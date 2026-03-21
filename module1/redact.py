import json
import struct
import base64
import numpy as np
import cv2
import easyocr
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

def extract_text_from_mask(img, mask, reader):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        x1 = x
        y1 = y
        x2 = x + w
        y2 = y + h

        crop = img[y1:y2, x1:x2]
        ocr_results = reader.readtext(crop)
        text = " ".join(t for box, t, prob in ocr_results).strip()

        if text:
            regions.append({"box": (x1, y1, x2 - x1, y2 - y1), "text": text})

    return regions


# -------------------------------------- Blurring --------------------------------------

def blur_mask_regions(img, mask, strength = 51):
    if strength % 2 == 0:
        strength += 1

    blurred = cv2.GaussianBlur(img, (strength, strength), 0)

    # blur only the mask
    result = img.copy()
    result[mask == 255] = blurred[mask == 255]
    return result


# -------------------------------------- Pipeline --------------------------------------

def redact_and_embed(img, mask, reader, key = None, blur_strength = 51):
    # Returns ( stego_img, key, summary)

    if key is None:
        key = get_random_bytes(32)

    regions = extract_text_from_mask(img, mask, reader)

    if not regions:
        print("Nothing to embed - no text found")
        blurred = blur_mask_regions(img, mask, blur_strength)
        return blurred, key, "No sensitive text found."


    extracted = {
        "regions": [
            {"box": r["box"], "text": r["text"]}
            for r in regions
        ]
    }
    plaintext = json.dumps(extracted, ensure_ascii=False)
    print(f"Extracted text: {plaintext}")

    # Encrypt
    ciphertext = encrypt(plaintext, key)
    print(f"Ciphertext length: {len(ciphertext)} bytes")

    # Blur
    blurred = blur_mask_regions(img, mask, blur_strength)

    # Embed
    try:
        stego = lsb_embed(blurred, ciphertext)
    except ValueError as e:
        print(f"WARNING: {e}")
        return blurred, key, f"Blur applied but stego failed: {e}"

    summary = (
        f"Redacted {len(regions)} regions.\n"
        f"Embedded {len(ciphertext)} bytes of encrypted data.\n"
        f"Key (base64): {base64.b64encode(key).decode()}"
    )
    print(summary)
    return stego, key, summary


def recover_from_image(img, key):
    ciphertext = lsb_extract(img)
    plaintext = decrypt(ciphertext, key)
    return json.loads(plaintext)