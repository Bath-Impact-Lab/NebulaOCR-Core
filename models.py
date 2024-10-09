# backend/models.py

from pydantic import BaseModel
from typing import List, Optional

class PreprocessOptions(BaseModel):
    grayscale: Optional[bool] = True
    denoise: Optional[bool] = True
    threshold: Optional[bool] = True
    deskew: Optional[bool] = True
    contrast: Optional[bool] = True

class OCRRequest(BaseModel):
    page_number: int
    bbox: List[float]  # [x1, y1, x2, y2]
    preprocess: PreprocessOptions

class OCRResponse(BaseModel):
    text: str

class PDFUploadResponse(BaseModel):
    pages: int
