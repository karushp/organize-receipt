"""Simple image handling for receipts (resize/thumbnail for display)."""
from io import BytesIO

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def make_thumbnail(image_bytes: bytes, max_size: tuple[int, int] = (400, 400)) -> bytes:
    """Return JPEG bytes of a thumbnail. If PIL is missing, returns original bytes."""
    if not HAS_PIL:
        return image_bytes
    img = Image.open(BytesIO(image_bytes))
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    out = BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()


def get_image_size(image_bytes: bytes) -> tuple[int, int] | None:
    """Return (width, height) if PIL available, else None."""
    if not HAS_PIL:
        return None
    img = Image.open(BytesIO(image_bytes))
    return img.size
