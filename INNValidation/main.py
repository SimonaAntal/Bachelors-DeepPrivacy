import os
import random
import kornia.augmentation as K
import cv2
from torch.utils.data import Dataset, DataLoader

from evaluate import evaluate_model
from pris import PRIS, train
import torch

torch.backends.cudnn.benchmark = True
torch.backends.cuda.matmul.allow_tf32 = True
torch.set_float32_matmul_precision('high')
torch.backends.cudnn.allow_tf32 = True

def crop_image(img, patch_size=224):
    h, w, _ = img.shape

    if h < patch_size or w < patch_size:
        img = cv2.resize(img, (patch_size, patch_size))
        patch = img
    else:
        y = random.randint(0, h - patch_size)
        x = random.randint(0, w - patch_size)
        patch = img[y:y + patch_size, x:x + patch_size]

    return patch

def resize_image(img, patch_size=224):
    return cv2.resize(img, (patch_size, patch_size), interpolation=cv2.INTER_AREA)

def load_image_tensor_cv(path):
    img = cv2.imread(path)  # BGR
    if img is None:
        print(f"[WARNING] skipping corrupt image: {path}")
        return None

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # tensor
    img = img / 255.0
    tensor = torch.tensor(img, dtype=torch.float32)
    tensor = tensor.permute(2, 0, 1)  # HWC → CHW

    return tensor


def save_image_cv(tensor, path):
    img = tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
    img = (img * 255).clip(0, 255).astype("uint8")
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(path, img)


class PRISDataset(Dataset):
    def __init__(self, host_files, secret_files, host_folder, secret_folder):
        self.host_files = host_files
        self.secret_files = secret_files

        self.host_folder = host_folder
        self.secret_folder = secret_folder

        self.host_tensors = []
        self.secret_tensors = []

        print(f"Loading {len(host_files)} host images into RAM...")
        for f in host_files:
            img = load_image_tensor_cv(os.path.join(host_folder, f))
            if img is not None: self.host_tensors.append(img)

        print(f"Loading {len(secret_files)} secret images into RAM...")
        for f in secret_files:
            img = load_image_tensor_cv(os.path.join(secret_folder, f))
            if img is not None: self.secret_tensors.append(img)

    def __len__(self):
        return len(self.secret_tensors)

    def __getitem__(self, idx):
        secret = self.secret_tensors[idx]
        secret_name = self.secret_files[idx]

        random_idx = random.randint(0, len(self.host_tensors) - 1)
        host = self.host_tensors[random_idx]
        host_name = self.host_files[random_idx]

        return host, secret, secret_name, host_name

import torchvision.transforms.functional as TF
from PIL import Image
import io
def jpeg_attack(img, quality):
    pil = TF.to_pil_image(img.cpu().clamp(0, 1))

    buf = io.BytesIO()
    pil.save(buf, format='JPEG', quality=quality)
    buf.seek(0)

    pil_compressed = Image.open(buf)
    return TF.to_tensor(pil_compressed)

def attacks(container_folder):
    attack_dirs = [
        "attacks/gauss1",
        "attacks/gauss10",
        "attacks/jpeg80",
        "attacks/jpeg90",
        "attacks/round"
    ]

    for d in attack_dirs:
        os.makedirs(d, exist_ok=True)

    for f in os.listdir(container_folder):
        path = os.path.join(container_folder, f)
        img = load_image_tensor_cv(path)

        #gaussian
        sigma = 1 / 255.0
        noise = torch.randn_like(img) * sigma
        gauss1 = (img + noise).clamp(0, 1)
        save_image_cv(gauss1, f"attacks/gauss1/{f}")

        sigma = 10 / 255.0
        noise = torch.randn_like(img) * sigma
        gauss1 = (img + noise).clamp(0, 1)
        save_image_cv(gauss1, f"attacks/gauss10/{f}")

        #jpeg
        #jpeg80 = jpeg_attack(img, 80)
        jpeg80 = K.RandomJPEG(jpeg_quality=(80, 80))
        jpeg80 = jpeg80(img.unsqueeze(0)).squeeze(0)
        save_image_cv(jpeg80, f"attacks/jpeg80/{f}")

        #jpeg90 = jpeg_attack(img, 90)
        jpeg90 = K.RandomJPEG(jpeg_quality=(90, 90))
        jpeg90 = jpeg90(img.unsqueeze(0)).squeeze(0)
        save_image_cv(jpeg90, f"attacks/jpeg90/{f}")

        #round
        round = (img * 255).round() / 255.0
        save_image_cv(round, f"attacks/round/{f}")

        print(f"Processed {f}")


def test_attack(container_folder, output_folder, model, device, use_enhance=False):
    os.makedirs(output_folder, exist_ok=True)

    for f in os.listdir(container_folder):
        path = os.path.join(container_folder, f)
        container = load_image_tensor_cv(path).to(device).unsqueeze(0)

        with torch.no_grad():
            recovered = model.extract(container, use_enhance)

        save_image_cv(recovered, os.path.join(output_folder, f))


def main():
    torch.backends.cudnn.benchmark = True

    # -------------------------- PRIS MODEL --------------------------
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'Using device: {device}')

    model = PRIS(num_blocks=8).to(device)

    host_folder = "PRIS/host"
    secret_folder = "PRIS/secret"

    test_host_folder = "PRIS/test/host"
    test_secret_folder = "PRIS/test/secret"

    output_container = "PRIS/output/container"
    output_recovered = "PRIS/output/recovered"

    # ================= PROCESS IMAGES =================
    host_files = [
        f for f in os.listdir(host_folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))
    ]

    secret_files = [
        f for f in os.listdir(secret_folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))
    ]

    test_host_files = [
        f for f in os.listdir(test_host_folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))
    ]

    test_secret_files = [
        f for f in os.listdir(test_secret_folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))
    ]

    split = int(0.8 * len(secret_files))
    train_secrets = secret_files[:split]
    eval_secrets = secret_files[split:]

    #train_dataset = PRISDataset(host_files, train_secrets, host_folder, secret_folder)
    #eval_dataset = PRISDataset(host_files, eval_secrets, host_folder, secret_folder)
    test_dataset = PRISDataset(test_host_files, test_secret_files, test_host_folder, test_secret_folder)

    #train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True, num_workers=4, pin_memory=True, persistent_workers=True, prefetch_factor=4, drop_last=True)
    #eval_loader = DataLoader(eval_dataset, batch_size=8, shuffle=False, num_workers=4, pin_memory=True, persistent_workers=True, prefetch_factor=4, drop_last=True)
    test_loader = DataLoader(test_dataset, batch_size=8, shuffle=False, num_workers=4, pin_memory=True, persistent_workers=True, prefetch_factor=4, drop_last=True)

    '''
    print('Loading model...')
    checkpoint = torch.load('model_step2.pth', map_location=device)
    model.load_state_dict(checkpoint)
    model.eval()
    '''

    # ----------------- Training -----------------
    print('Training...')
    #train(model, train_loader, eval_loader, device,1000)


    # ----------------- Testing -----------------
    print('Loading model...')
    checkpoint = torch.load('model_step3.pth', map_location=device)
    model.load_state_dict(checkpoint)
    model.eval()

    print('Testing...')
    for host, secret, secret_file, host_file in test_loader:
        host = host.to(device)
        secret = secret.to(device)

        with torch.no_grad():
            container = model.embed(host, secret)
            recovered = model.extract(container, use_enhance=True)

        for i in range(len(secret_file)):
            s_name = os.path.splitext(secret_file[i])[0]
            c_name = os.path.splitext(host_file[i])[0]
            new_name = f's{s_name}_c{c_name}.tif'

            save_image_cv(container[i], os.path.join(output_container, new_name))
            save_image_cv(recovered[i], os.path.join(output_recovered, new_name))

            print(f"Processed: {secret_file[i]}")

    print("Done.")

    attacks(output_container)

    print("Gauss 1")
    test_attack("attacks/gauss1", "attacks/gauss1_rec", model, device, use_enhance=True)

    print("Gauss 10")
    test_attack("attacks/gauss10", "attacks/gauss10_rec", model, device, use_enhance=True)

    print("Jpeg 80")
    test_attack("attacks/jpeg80", "attacks/jpeg80_rec", model, device, use_enhance=True)

    print("Jpeg 90")
    test_attack("attacks/jpeg90", "attacks/jpeg90_rec", model, device, use_enhance=True)

    print("Round")
    test_attack("attacks/round", "attacks/round_rec", model, device, use_enhance=True)


    # ----------------- Model evaluation -----------------
    print("\nNormal")
    evaluate_model(test_host_folder, output_container, test_secret_folder, output_recovered)

    print("\nGauss 1")
    evaluate_model(test_host_folder, "attacks/gauss1", test_secret_folder, "attacks/gauss1_rec")

    print("\nGauss 10")
    evaluate_model(test_host_folder, "attacks/gauss10", test_secret_folder, "attacks/gauss10_rec")

    print("\nJpeg 80")
    evaluate_model(test_host_folder, "attacks/jpeg80", test_secret_folder, "attacks/jpeg80_rec")

    print("\nJpeg 90")
    evaluate_model(test_host_folder, "attacks/jpeg90", test_secret_folder, "attacks/jpeg90_rec")

    print("\nRound")
    evaluate_model(test_host_folder, "attacks/round", test_secret_folder, "attacks/round_rec")

    return 0


if __name__ == '__main__':
    main()