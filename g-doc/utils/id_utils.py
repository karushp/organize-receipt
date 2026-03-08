"""Generate unique IDs for receipts."""

import uuid
from datetime import datetime


def generate_receipt_id() -> str:
    """Generate a unique ID for a receipt/transaction."""
    return f"rec_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:12]}"


def generate_image_filename(receipt_id: str, original_filename: str) -> str:
    """Generate a consistent filename for storing receipt image in Drive."""
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "jpg"
    if ext not in ("jpg", "jpeg", "png", "gif", "webp", "pdf"):
        ext = "jpg"
    return f"{receipt_id}.{ext}"
