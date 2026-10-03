import pytesseract
from PIL import Image


def ocr_image(path: str) -> str:
    with Image.open(path) as image:
        return pytesseract.image_to_string(image)
