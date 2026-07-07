import cv2
import pytesseract

def convert_rgb_img(path):
    img = cv2.imread(path)  # BGR
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img

def fix_orientation(img):
    try:
        osd = pytesseract.image_to_osd(img, output_type=pytesseract.Output.DICT)
        angle = osd.get("rotate", 0)
        confidence = osd.get("orientation_conf", 0)
    except Exception:
        return img  # tesseract failed (too little text)

    # only rotate if confidence is high enough
    if confidence < 2.0 or angle == 0:
        return img

    rotation_map = {
        90: cv2.ROTATE_90_CLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_COUNTERCLOCKWISE,
    }

    if angle not in rotation_map:
        return img

    return cv2.rotate(img, rotation_map[angle])

def resize_img(img, size=(1024, 1024)):
    h, w = img.shape[:2]
    scale = min (size[0]/w, size[1]/h)
    new_w, new_h = int(scale * w), int(scale * h)
    img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    return img_resized

def preprocess_image(path, size=(1024, 1024)):
    img = convert_rgb_img(path)
    img = fix_orientation(img)
    img = resize_img(img, size)

    return img