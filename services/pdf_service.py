"""PDF and image processing utilities for receipts."""

import io
from pathlib import Path

from PIL import Image

SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
SUPPORTED_PDF_EXT = {".pdf"}


def get_mime_type(filename: str) -> str:
    """Return MIME type for common receipt file formats."""
    ext = Path(filename).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".pdf": "application/pdf",
    }
    return mime_map.get(ext, "application/octet-stream")


def is_supported_receipt_file(filename: str) -> bool:
    """Check if the file type is supported for receipt uploads."""
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_IMAGE_FORMATS or ext in SUPPORTED_PDF_EXT


def image_to_jpeg_bytes(image: Image.Image) -> bytes:
    """Convert PIL Image to JPEG bytes for consistent storage."""
    buffer = io.BytesIO()
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def load_image_from_bytes(data: bytes) -> Image.Image:
    """Load a PIL Image from bytes."""
    return Image.open(io.BytesIO(data)).copy()


def pdf_first_page_to_image(pdf_bytes: bytes) -> Image.Image | None:
    """
    Render the first page of a PDF as an image.
    Returns None if PDF processing fails.
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        if len(reader.pages) == 0:
            return None

        # pypdf doesn't render to image; we'd need pdf2image (poppler) for that.
        # For now, return None - caller can handle PDFs as raw upload or add pdf2image.
        return None
    except Exception:
        return None


def prepare_receipt_for_upload(
    file_data: bytes, filename: str
) -> tuple[bytes, str]:
    """
    Prepare receipt file for upload. Converts images to JPEG for consistency.
    Returns (bytes, mime_type).
    """
    ext = Path(filename).suffix.lower()

    if ext in SUPPORTED_IMAGE_FORMATS:
        img = load_image_from_bytes(file_data)
        jpeg_bytes = image_to_jpeg_bytes(img)
        return jpeg_bytes, "image/jpeg"

    if ext == ".pdf":
        img = pdf_first_page_to_image(file_data)
        if img:
            jpeg_bytes = image_to_jpeg_bytes(img)
            return jpeg_bytes, "image/jpeg"
        # Keep as PDF if we can't render
        return file_data, "application/pdf"

    return file_data, get_mime_type(filename)
