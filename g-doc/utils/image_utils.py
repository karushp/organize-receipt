"""Image processing and validation utilities."""

import io
from pathlib import Path

from PIL import Image

MAX_FILE_SIZE_MB = 10
MAX_DIMENSION_PX = 4096
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


def validate_image_file(file_data: bytes, filename: str) -> tuple[bool, str]:
    """
    Validate an uploaded image file.
    Returns (is_valid, error_message).
    """
    if len(file_data) > MAX_FILE_SIZE_MB * 1024 * 1024:
        return False, f"File size exceeds {MAX_FILE_SIZE_MB}MB limit."

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    try:
        img = Image.open(io.BytesIO(file_data))
        img.verify()
    except Exception as e:
        return False, f"Invalid or corrupted image: {e}"

    # Re-open for dimension check (verify() closes the file)
    try:
        img = Image.open(io.BytesIO(file_data))
        w, h = img.size
        if w > MAX_DIMENSION_PX or h > MAX_DIMENSION_PX:
            return False, f"Image dimensions exceed {MAX_DIMENSION_PX}px limit."
    except Exception:
        return False, "Could not read image dimensions."

    return True, ""


def resize_if_needed(image: Image.Image, max_dimension: int = 2048) -> Image.Image:
    """Resize image if it exceeds max_dimension on either axis."""
    w, h = image.size
    if w <= max_dimension and h <= max_dimension:
        return image

    ratio = min(max_dimension / w, max_dimension / h)
    new_size = (int(w * ratio), int(h * ratio))
    return image.resize(new_size, Image.Resampling.LANCZOS)
