"""
Lightweight receipt pipeline: center crop to print-template ratio → grayscale (no resize).

User aligns receipt in frame; app crops to 171:365 (width:height) so the image
fits the receipt grid cells when printing. No edge detection.
"""

from __future__ import annotations

from io import BytesIO

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Match print template receipt cell ratio (width : height)
RECEIPT_TEMPLATE_RATIO_W = 171
RECEIPT_TEMPLATE_RATIO_H = 365

JPEG_QUALITY = 90


def _center_crop_to_ratio(
    width: int,
    height: int,
    ratio_w: int,
    ratio_h: int,
) -> tuple[int, int, int, int]:
    """Return PIL crop box (left, upper, right, lower) for largest centered crop with ratio_w:ratio_h."""
    # Largest rectangle with ratio_w:ratio_h that fits in (width, height)
    # Option A: use full height -> cw = H * ratio_w/ratio_h
    cw_by_h = int(height * ratio_w / ratio_h)
    if cw_by_h <= width:
        cw, ch = cw_by_h, height
    else:
        ch = int(width * ratio_h / ratio_w)
        cw = width
    x = (width - cw) // 2
    y = (height - ch) // 2
    return (x, y, x + cw, y + ch)


def process_receipt(image_bytes: bytes) -> bytes:
    """
    Crop to print-template ratio (171:365) and convert to grayscale.

    Returns JPEG bytes. On missing PIL or any error, returns original bytes.
    """
    if not HAS_PIL:
        return image_bytes

    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        box = _center_crop_to_ratio(
            img.width, img.height,
            RECEIPT_TEMPLATE_RATIO_W, RECEIPT_TEMPLATE_RATIO_H,
        )
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
