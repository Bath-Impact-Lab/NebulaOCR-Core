# backend/ocr_utils.py

import os
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance
import pytesseract
import cv2
import numpy as np
import re
from textblob import TextBlob

# Configure Tesseract path if necessary
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Update as needed

def convert_pdf_to_images(pdf_path, dpi=1200):
    """
    Convert PDF to a list of PIL Image objects.
    """
    images = convert_from_path(pdf_path, dpi=dpi)
    print(images)
    return images

def preprocess_image(pil_image, options):
    """
    Preprocess the image based on selected options.
    """
    open_cv_image = np.array(pil_image)
    open_cv_image = open_cv_image[:, :, ::-1].copy()  # Convert RGB to BGR

    # 1. Grayscale
    if options.get("grayscale", True):
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = open_cv_image

    # 2. Noise Reduction
    if options.get("denoise", True):
        if len(gray.shape) == 2:
            denoised = cv2.medianBlur(gray, 3)
        else:
            denoised = cv2.cvtColor(cv2.medianBlur(cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY), 3), cv2.COLOR_GRAY2BGR)
    else:
        denoised = gray

    # 3. Thresholding
    if options.get("threshold", True):
        if len(denoised.shape) == 3 and denoised.shape[2] == 3:
            gray_thresh = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
        else:
            gray_thresh = denoised
        thresh = cv2.adaptiveThreshold(gray_thresh, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 31, 2)
    else:
        thresh = denoised if options.get("grayscale", True) else denoised

    # 4. Deskewing
    if options.get("deskew", True):
        deskewed = deskew(thresh)
    else:
        deskewed = thresh

    # 5. Contrast Enhancement
    if options.get("contrast", True):
        if len(deskewed.shape) == 2:
            enhanced = cv2.convertScaleAbs(deskewed, alpha=1.5, beta=0)
        else:
            enhancer = ImageEnhance.Contrast(Image.fromarray(cv2.cvtColor(deskewed, cv2.COLOR_BGR2RGB)))
            enhanced_pil = enhancer.enhance(1.5)
            enhanced = cv2.cvtColor(np.array(enhanced_pil), cv2.COLOR_RGB2BGR)
    else:
        enhanced = deskewed

    # Convert back to PIL Image
    if len(enhanced.shape) == 2:
        processed_pil = Image.fromarray(enhanced)
    else:
        processed_pil = Image.fromarray(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB))

    return processed_pil

def deskew(image):
    """
    Deskew the image based on its moments.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    coords = np.column_stack(np.where(gray > 0))
    if coords.size == 0:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(image, M, (w, h),
                              flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return deskewed

def perform_ocr(image, config='--oem 3 --psm 1', lang='eng'):
    """
    Perform OCR on the provided PIL Image.
    """
    raw_text = pytesseract.image_to_string(image, config='--oem 3 --psm 6', lang=lang)
    print(raw_text)
    image.save('ocrd.png', 'PNG')
    formatted_text = format_text(raw_text)
    # corrected_text = correct_spelling(formatted_text)
    return formatted_text

def format_text(text):
    """
    Basic text formatting:
    - Capitalize first letter of sentences.
    - Remove extra spaces.
    - Remove hyphens at line breaks.
    """
    print(text)
    text = re.sub(r'-\s*[\r\n]+\s*', '', text)
    sentences = re.split('(?<=[.!?]) +', text)
    #sentences = [s.capitalize() for s in sentences]
    formatted_text = ' '.join(sentences)
    print(formatted_text)
    formatted_text = re.sub(r'\s+', ' ', formatted_text)
    print(formatted_text)
    return formatted_text

def correct_spelling(text):
    """
    Correct spelling using TextBlob.
    """
    try:
        blob = TextBlob(text)
        corrected = blob.correct()
        return str(corrected)
    except Exception:
        return text  # Return raw text if correction fails
