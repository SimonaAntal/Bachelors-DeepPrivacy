import json
import os
import random
import struct
import base64
import numpy as np
import cv2
import torch
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


# -------------------------------------- Encryption --------------------------------------

def encrypt(plaintext, key):
    num_once = get_random_bytes(12)

    cipher = AES.new(key, AES.MODE_GCM, nonce=num_once)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))

    # nonce(12) + tag (16) + ciphertext
    return num_once + tag + ciphertext


def decrypt(payload, key):
    # nonce(12) + tag (16) + ciphertext
    nonce = payload[:12]
    tag = payload[12:28]
    ciphertext = payload[28:]

    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")


# -------------------------------------- Steganography --------------------------------------

def image_capacity_bytes(img):
    # 1 bit per pixel on blue channel
    h, w = img.shape[:2]
    return (h * w) // 8 #bytes


def lsb_embed(img, data):
    # big endian unsigned int (4 bytes)
    header = struct.pack(">I", len(data))
    payload = header + data

    capacity = image_capacity_bytes(img)
    if len(payload) > capacity:
        raise ValueError(f"Image too small! Capacity is {capacity}, bytes needed {len(payload)}")

    flat = img.reshape(-1, 3)   # list where each pixel is [R, G, B]
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8)) # bit transform

    # LSB of B channel = bits
    num_pixels = len(bits)
    flat[:num_pixels, 2] = (flat[:num_pixels, 2] & 0xFE) | bits

    return flat.reshape(img.shape)


def lsb_extract(img):
    # list where each pixel is [B, G, R]
    flat = img.reshape(-1, 3)

    # Read length header (first 32 bits → 4 bytes)
    header_bits = (flat[:32, 2] & 1).astype(np.uint8)
    length = struct.unpack(">I", np.packbits(header_bits).tobytes())[0]

    total_bits = (4 + length) * 8
    all_bits = (flat[:total_bits, 2] & 1).astype(np.uint8)
    all_bytes = np.packbits(all_bits).tobytes()

    return all_bytes[4: 4 + length]         # skip the 4 byte header


# -------------------------------------- Region extraction --------------------------------------

def extract_text_from_mask(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []

    for i, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        regions.append((i, x, y, w, h))

    return regions


# -------------------------------------- Loading img as tensor --------------------------------------

def load_tensor(path, patch_size=224):
    img = cv2.imread(path)  # BGR
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    h, w, _ = img.shape

    if h < patch_size or w < patch_size:
        img = cv2.resize(img, (patch_size, patch_size))
        patch = img
    else:
        y = random.randint(0, h - patch_size)
        x = random.randint(0, w - patch_size)
        patch = img[y:y + patch_size, x:x + patch_size]

    t = torch.from_numpy(patch).float().div(255).permute(2, 0, 1)
    return t.unsqueeze(0)

def crop_to_tensor(crop, patch_size=224):
    img = cv2.resize(crop, (patch_size, patch_size), interpolation=cv2.INTER_AREA)

    t = torch.from_numpy(img).float().div(255).permute(2, 0, 1)
    return t.unsqueeze(0)

def tensor_to_numpy(tensor):
    t = tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
    return (t * 255).clip(0, 255).astype(np.uint8)

def save_img(img, path):
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(path, img, [cv2.IMWRITE_TIFF_COMPRESSION, 1])

# -------------------------------------- Pipeline --------------------------------------
host_folder = "PRIS/host"
secret_folder = "PRIS/secret"
output_container = "PRIS/output/container"
output_recovered = "PRIS/output/recovered"

def redact_and_embed(img, mask, pris_model, device, aes_key = None):
    # Returns ( stego_img, key, summary)

    host_files = os.listdir(host_folder) # container images

    regions = extract_text_from_mask(mask)
    redacted = img.copy()

    if aes_key is None:
        aes_key = get_random_bytes(32)

    region_meta = []

    with torch.no_grad():
        for (i, x, y, w, h) in regions:
            crop = img[y:y+h, x:x+w]

            # pick random host img
            host_file = random.choice(host_files)
            host = load_tensor(os.path.join(host_folder, host_file)).to(device)
            secret = crop_to_tensor(crop).to(device)

            # embed secret into host
            container = pris_model.embed(host, secret)
            container_np = tensor_to_numpy(container)
            container_name = f'h{os.path.splitext(host_file)[0]}_r{i}_x{x}_y{y}_w{w}_h{h}.tiff'
            save_img(container_np, os.path.join(output_container, container_name))

            # cover sensitive region with blur
            region_blurred = cv2.GaussianBlur(crop, (51, 51), 0)
            redacted[y:y + h, x:x + w] = region_blurred

            region_meta.append({
                "region_idx": i,
                "x": x, "y": y, "w": w, "h": h,
                "host_file": host_file,
                "container_name": container_name
            })

            print(f'Embeded region {i} using host {host_file}')

    # build encryption text
    plaintext = json.dumps({
        "original_size": [img.shape[1], img.shape[0]],
        "regions": region_meta
    }, ensure_ascii=False)

    # encrypt metadata
    ciphertext = encrypt(plaintext, aes_key)
    print(f"Ciphertext length: {len(ciphertext)} bytes")

    # embed ciphertext
    try:
        stego = lsb_embed(redacted, ciphertext)
    except ValueError as e:
        print(f"WARNING: LSB embeding failed {e}")
        stego = redacted

    summary = (
        f"Redacted {len(regions)} regions.\n"
        f"Embedded {len(ciphertext)} bytes of encrypted data.\n"
        f"Key (base64): {base64.b64encode(aes_key).decode()}"
    )
    print(summary)
    return stego, aes_key, summary


def recover_from_image(img, key, pris_model, device):
    ciphertext = lsb_extract(img)
    plaintext = decrypt(ciphertext, key)
    metadata = json.loads(plaintext)

    W, H = metadata["original_size"]
    regions = metadata["regions"]

    recovered = img.copy()

    with torch.no_grad():
        for r in regions:
            x, y, w, h = r["x"], r["y"], r["w"], r["h"]

            container_path = os.path.join(output_container, r["container_name"])
            container_img = cv2.imread(container_path)
            container_rgb = cv2.cvtColor(container_img, cv2.COLOR_BGR2RGB)
            container = crop_to_tensor(container_rgb).to(device)

            secret = pris_model.extract(container)
            secret_np = tensor_to_numpy(secret)

            secret_name = f'rec_r{r['region_idx']}_x{x}_y{y}_w{w}_h{h}.tiff'
            save_img(secret_np, os.path.join(output_recovered, secret_name))

            secret_resized = cv2.resize(secret_np, (w, h), interpolation=cv2.INTER_LANCZOS4)
            recovered[y:y+h, x:x+w] = secret_resized


    return recovered