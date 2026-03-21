import os
import json
import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
from classifiers import classify_texts
from redact import redact_and_embed, recover_from_image


def resize_and_convert(path, size=(1024, 1024)):
    img = cv2.imread(path) #BGR
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    #resize
    h, w = img.shape[:2]
    scale = min (size[0]/w, size[1]/h)
    new_w, new_h = int(scale * w), int(scale * h)
    img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    return img_resized

def detect_faces(img, model):
    results = model(img)
    result = results[0] # only one img
    boxes = result.boxes.xyxy.cpu().numpy()  # all the faces

    mask = np.zeros(img.shape[:2], dtype=np.uint8)

    for box in boxes:
        x1, y1, x2, y2 = map(int, box)
        mask[y1:y2, x1:x2] = 255

    return mask

def detect_text(img, reader):
    results = reader.readtext(img)
    texts = [text for (box, text, prob) in results]
    sensitive_list = classify_texts(texts)

    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for box, text, prob in results:
        if text in sensitive_list:
            xs = [p[0] for p in box] # all x's
            ys = [p[1] for p in box] # all y's

            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            mask[y_min:y_max, x_min:x_max] = 255

    return mask


def main():
    image_folder = 'res/'
    output_folder = 'out/'

    files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]

    yolo_model = YOLO('yolov11n-face.pt')  # face model
    reader = easyocr.Reader(['en', 'ro']) # text model

    for f in files:
        img_path = os.path.join(image_folder, f)

        resized = resize_and_convert(img_path)
        mask_faces = detect_faces(resized, yolo_model)
        mask_text = detect_text(resized, reader)

        face_overlay = resized.copy()
        color_mask = np.zeros_like(resized)
        color_mask[:, :, 0] = mask_faces  # mask is on one channel
        alpha = 0.3
        cv2.addWeighted(color_mask, alpha, face_overlay, 1 - alpha, 0, face_overlay)

        text_overlay = resized.copy()
        color_mask = np.zeros_like(resized)
        color_mask[:, :, 2] = mask_text
        alpha = 0.3
        cv2.addWeighted(color_mask, alpha, text_overlay, 1 - alpha, 0, text_overlay)


        # stego
        combined_mask = cv2.bitwise_or(mask_faces, mask_text)
        stego_img, key, summary = redact_and_embed(resized, combined_mask, reader)
        print(f'\n\n{summary}')

        base_name = os.path.splitext(f)[0]
        #save_key(key, base_name)

        out_path = os.path.join(output_folder, base_name + '_redacted.png')
        cv2.imwrite(out_path, cv2.cvtColor(stego_img, cv2.COLOR_RGB2BGR))
        print(f'Saved {out_path}')

        # Verify recovery works
        recovered = recover_from_image(stego_img, key)
        print('\n\nRecovered:', json.dumps(recovered, indent=2, ensure_ascii=False))

        cv2.imshow('resize', cv2.cvtColor(resized, cv2.COLOR_RGB2BGR))
        cv2.imshow('Faces', cv2.cvtColor(face_overlay, cv2.COLOR_RGB2BGR))
        cv2.imshow('Text', cv2.cvtColor(text_overlay, cv2.COLOR_RGB2BGR))
        cv2.imshow('Redacted', cv2.cvtColor(stego_img, cv2.COLOR_RGB2BGR))
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return 0


if __name__ == '__main__':
    main()