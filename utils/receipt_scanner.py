"""
Lightweight receipt pipeline: center crop → grayscale only (no resize).

User aligns receipt in frame; app crops a tall center strip (≈1:5 ratio)
and keeps aspect ratio. No edge detection.
"""

from __future__ import annotations

from io import BytesIO

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Crop: tall center strip, height:width ≈ 5:1, inside frame
WIDTH_FRACTION = 0.18
HEIGHT_FRACTION = 0.9

JPEG_QUALITY = 90


def _center_crop_box(width: int, height: int) -> tuple[int, int, int, int]:
    """Return PIL crop box (left, upper, right, lower) for centered strip."""
    cw = int(width * WIDTH_FRACTION)
    ch = int(height * HEIGHT_FRACTION)
    x = (width - cw) // 2
    y = (height - ch) // 2
    return (x, y, x + cw, y + ch)


def process_receipt(image_bytes: bytes) -> bytes:
    """
    Crop center rectangle and convert to grayscale. Aspect ratio unchanged.

    Returns JPEG bytes. On missing PIL or any error, returns original bytes.
    """
    if not HAS_PIL:
        return image_bytes

    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        box = _center_crop_box(img.width, img.height)
        cropped = img.crop(box).convert("L")

        buf = BytesIO()
        cropped.save(buf, format="JPEG", quality=JPEG_QUALITY)
        return buf.getvalue()
    except Exception:
        return image_bytes


def scan_receipt_image_bytes(
    image_bytes: bytes,
    target_size: tuple[int, int] | None = None,
) -> bytes:
    """Alias for process_receipt. target_size is ignored (no resize). Kept for compatibility."""
    return process_receipt(image_bytes)
