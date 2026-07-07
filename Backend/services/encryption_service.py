import os

import cv2

from exceptions.encrypt_exceptions import NoSensitiveRegionsException, DecryptionException
from services.detection_service import detect_faces, detect_text
from services.preprocessing_service import preprocess_image
from services.redact_service import redact_and_embed, recover_from_image, delete_containers


def encrypt_image(image_path):
    # load and resize
    resized = preprocess_image(image_path)

    # detect sensitive regions
    mask_faces = detect_faces(resized)
    mask_text = detect_text(resized)
    combined_mask = cv2.bitwise_or(mask_faces, mask_text)

    if combined_mask.max() == 0:
        raise NoSensitiveRegionsException("No sensitive regions found")

    # stego
    encrypted_img, key, summary = redact_and_embed(resized, combined_mask)

    return encrypted_img, key

def decrypt_image(image_path, key):
    if not os.path.exists(image_path):
        raise FileNotFoundError()

    encrypted_img = cv2.imread(image_path)
    if encrypted_img is None:
        raise DecryptionException("Could not read image")

    encrypted_img = cv2.cvtColor(
        encrypted_img,
        cv2.COLOR_BGR2RGB
    )

    recovered_img = recover_from_image(encrypted_img, key)

    _, buffer = cv2.imencode(".png",
        cv2.cvtColor(recovered_img, cv2.COLOR_RGB2BGR)
    )

    return buffer

def delete_image_containers(image_path, key):
    if not os.path.exists(image_path):
        raise FileNotFoundError()

    encrypted_img = cv2.imread(image_path)
    if encrypted_img is None:
        raise DecryptionException("Could not read image")

    encrypted_img = cv2.cvtColor(
        encrypted_img,
        cv2.COLOR_BGR2RGB
    )

    return delete_containers(encrypted_img, key)
