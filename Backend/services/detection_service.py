from ultralytics import YOLO
import easyocr
import numpy as np
from services.classifier_service import classify_texts

yolo_model = YOLO('yolov11n-face.pt')  # face model
ocr_reader = easyocr.Reader(['en', 'ro'])  # text model

def detect_faces(img, model = yolo_model):
    results = model(img)
    result = results[0] # only one img
    boxes = result.boxes.xyxy.cpu().numpy()  # all the faces

    mask = np.zeros(img.shape[:2], dtype=np.uint8)

    for box in boxes:
        x1, y1, x2, y2 = map(int, box)
        mask[y1:y2, x1:x2] = 255

    return mask

def detect_text(img, reader= ocr_reader):
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
