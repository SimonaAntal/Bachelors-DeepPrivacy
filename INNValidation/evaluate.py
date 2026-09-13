import os

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim


def find_image(folder, name):
    for ext in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]:
        path = os.path.join(folder, name + ext)
        if os.path.exists(path):
            return path
    return None

def load_image(path):
    img = cv2.imread(path)
    if img is None:
        return None

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img.astype('float32') / 255.0

def compute_psnr(img1, img2):
    mse = np.mean((img1 - img2) ** 2)
    return 10 * np.log10(1.0 / mse)

def compute_ssim(img1, img2):
    return ssim(img1, img2, channel_axis=2, data_range=1.0)

def evaluate_model(host_dir, container_dir, secret_dir, recovered_dir):
    psnr_container = 0
    psnr_secret = 0
    ssim_container = 0
    ssim_secret = 0
    count = 0

    for f in os.listdir(recovered_dir):
        if not f.endswith(".tif"):
            continue

        name = os.path.splitext(f)[0]
        parts = name.split("_")

        s_name = parts[0][1:] # remove 's'
        c_name = parts[1][1:] # remove 'c'

        host_path = find_image(host_dir, c_name)
        secret_path = find_image(secret_dir, s_name)
        container_path = os.path.join(container_dir, f)
        recovered_path = os.path.join(recovered_dir, f)

        # load images
        host = load_image(host_path)
        secret = load_image(secret_path)
        container = load_image(container_path)
        recovered = load_image(recovered_path)

        psnr_c = compute_psnr(host, container)
        psnr_s = compute_psnr(secret, recovered)

        ssim_c = compute_ssim(host, container)
        ssim_s = compute_ssim(secret, recovered)

        count += 1
        psnr_container += psnr_c
        psnr_secret += psnr_s
        ssim_container += ssim_c
        ssim_secret += ssim_s

    print('=================== FINAL RESULTS ==================')
    print(f'Average PSNRc: {psnr_container / count:.2f}')
    print(f'Average PSNRs: {psnr_secret / count:.2f}')
    print(f'Average SSIMc: {ssim_container / count:.2f}')
    print(f'Average SSIMs: {ssim_secret / count:.2f}')