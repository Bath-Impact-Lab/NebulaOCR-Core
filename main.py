# backend/main.py

import os
import shutil
import uuid
import logging
import uvicorn
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

from ocr_utils import (
    convert_pdf_to_images,
    preprocess_image,
    perform_ocr
)

app = FastAPI(title="OCR API")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# CORS settings (adjust origins as needed)
origins = [
    #"http://localhost:5174",  # React frontend
    # Add other origins if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to store uploads and images
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory storage for PDF metadata (in production, use a database or persistent storage)
pdf_store = {}


class PreprocessOptions(BaseModel):
    grayscale: bool = True
    denoise: bool = True
    threshold: bool = True
    deskew: bool = True
    contrast: bool = True


class OCRRequest(BaseModel):
    pdf_id: str
    page_number: int
    bbox: List[float]  # [x1, y1, x2, y2]
    preprocess: PreprocessOptions


class OCRResponse(BaseModel):
    text: str


class PDFUploadResponse(BaseModel):
    pdf_id: str
    pages: int


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

@app.post("/upload_pdf", response_model=PDFUploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    logger.info(f"Received file upload with content type: {file.content_type}")

    if file.content_type != "application/pdf":
        logger.error("Unsupported file type uploaded.")
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_id = str(uuid.uuid4())
    pdf_filename = f"{pdf_id}.pdf"
    pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)

    # Create directory for images
    images_dir = os.path.join(UPLOAD_DIR, pdf_id)
    os.makedirs(images_dir, exist_ok=True)
    logger.info(f"Created directory for PDF images at: {images_dir}")

    # Save the uploaded PDF to disk
    try:
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Saved PDF to {pdf_path}")
    except Exception as e:
        logger.error(f"Failed to save uploaded PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save PDF: {e}")
    finally:
        file.file.close()

    # Convert PDF to images and save them to disk
    try:
        images = convert_pdf_to_images(pdf_path)

        options = {
            "grayscale": True,
            "denoise": True,
            "threshold": False,
            "deskew": False,
            "contrast": True,
        }

        total_pages = len(images)
        logger.info(f"Converted PDF to {total_pages} image(s).")

        for idx, img in enumerate(images, start=1):
            image_filename = f"page_{idx}.png"
            image_path = os.path.join(images_dir, image_filename)
            img = preprocess_image(img, options)
            img.save(image_path, "PNG")
            logger.info(f"Saved image for page {idx} at {image_path}")

        # Update the in-memory PDF store
        pdf_store[pdf_id] = {
            "pdf_path": pdf_path,
            "pages": total_pages
        }
        logger.info(f"Stored metadata for PDF ID {pdf_id}")
        return PDFUploadResponse(pdf_id=pdf_id, pages=total_pages)

    except Exception as e:
        logger.error(f"Failed to process PDF {pdf_id}: {e}")
        # Cleanup: Remove the saved PDF and images directory
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            logger.info(f"Removed corrupted PDF at {pdf_path}")
        if os.path.exists(images_dir):
            shutil.rmtree(images_dir)
            logger.info(f"Removed images directory at {images_dir}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {e}")


@app.get("/get_page/{pdf_id}/{page_number}")
def get_page(pdf_id: str, page_number: int):
    logger.info(f"Request to get page {page_number} of PDF ID {pdf_id}")

    if pdf_id not in pdf_store:
        logger.error(f"PDF ID {pdf_id} not found.")
        raise HTTPException(status_code=404, detail="PDF not found.")

    total_pages = pdf_store[pdf_id]["pages"]
    if page_number < 1 or page_number > total_pages:
        logger.error(f"Invalid page number {page_number} for PDF ID {pdf_id}.")
        raise HTTPException(status_code=400, detail="Invalid page number.")

    image_path = os.path.join(UPLOAD_DIR, pdf_id, f"page_{page_number}.png")
    if not os.path.exists(image_path):
        logger.error(f"Image file {image_path} does not exist.")
        raise HTTPException(status_code=404, detail="Image not found.")

    logger.info(f"Serving image from {image_path}")
    return FileResponse(image_path, media_type="image/png")


@app.post("/perform_ocr", response_model=OCRResponse)
def perform_ocr_endpoint(request: OCRRequest):
    logger.info(f"Received OCR request for PDF ID {request.pdf_id}, page {request.page_number}")

    pdf_id = request.pdf_id
    if pdf_id not in pdf_store:
        logger.error(f"PDF ID {pdf_id} not found for OCR.")
        raise HTTPException(status_code=404, detail="PDF not found.")

    total_pages = pdf_store[pdf_id]["pages"]
    page_number = request.page_number
    if page_number < 1 or page_number > total_pages:
        logger.error(f"Invalid page number {page_number} for PDF ID {pdf_id}.")
        raise HTTPException(status_code=400, detail="Invalid page number.")

    image_path = os.path.join(UPLOAD_DIR, pdf_id, f"page_{page_number}.png")
    if not os.path.exists(image_path):
        logger.error(f"Image file {image_path} does not exist for OCR.")
        raise HTTPException(status_code=404, detail="Image not found.")

    try:
        pil_image = Image.open(image_path)
        logger.info(f"Opened image {image_path} for OCR.")
    except Exception as e:
        logger.error(f"Failed to open image {image_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to open image for OCR.")

    # Crop the selected region
    try:
        width, height = pil_image.size
        x1 = int(request.bbox[0] / 100 * width)
        y1 = int(request.bbox[1] / 100 * height)
        x2 = int(request.bbox[2] / 100 * width)
        y2 = int(request.bbox[3] / 100 * height)

        cropped = pil_image.crop((x1, y1, x2, y2))
        cropped.save('current_region.png', "PNG")
        logger.info(f"Cropped image to bounding box {request.bbox}")
    except Exception as e:
        logger.error(f"Failed to crop image: {e}")
        raise HTTPException(status_code=400, detail="Invalid bounding box.")

    # Preprocess the image
    try:
        # processed_image = preprocess_image(cropped, request.preprocess.dict())
        # processed_image.save(fp='current_region.png', format="PNG")
        logger.info("Image preprocessing completed.")
    except Exception as e:
        logger.error(f"Failed to preprocess image: {e}")
        raise HTTPException(status_code=500, detail="Image preprocessing failed.")

    # Perform OCR
    try:
        text = perform_ocr(cropped)
        logger.info("OCR processing completed.")
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail="OCR processing failed.")

    return OCRResponse(text=text)


@app.on_event("shutdown")
def cleanup():
    logger.info("Shutting down. Cleaning up upload directory.")
    # Remove all uploaded files on shutdown
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    logger.info("Upload directory cleaned up.")


@app.post('/ping')
def ping():
    logger.info("Received ping request.")
    return 'Pong!'
