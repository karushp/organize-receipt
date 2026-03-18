"""Upload receipt image to Supabase Storage and insert transaction."""
import os
from pathlib import Path
from uuid import uuid4
from datetime import date

from app.supabase_client import get_client, first_row


BUCKET = "receipts"


def content_type_for_filename(filename: str) -> str:
    """Return a suitable content-type for upload from filename extension."""
    lower = (filename or "").lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".heic"):
        return "image/heic"
    return "image/jpeg"


def _user_folder(user: str) -> str:
    """Storage path prefix for user (e.g. user-1, user-2)."""
    return f"{user.strip()}/"


def _next_receipt_number_for_user_date(user: str, transaction_date: date) -> int:
    """Return next incremental number (1-based) for receipts for this user on this date."""
    client = get_client()
    date_iso = transaction_date.isoformat()
    resp = client.table("transactions").select("id").eq("user", user.strip()).eq("date", date_iso).execute()
    count = len(resp.data or [])
    return count + 1


def upload_image(
    user: str,
    file_bytes: bytes,
    content_type: str,
    transaction_date: date | None = None,
) -> str:
    """
    Upload receipt image to Storage and return public URL.
    Path: receipts/{user}/{user}-{MMDDYY}-{seq:03d}.{ext} when transaction_date is set,
    else receipts/{user}/{uuid}.{ext} (legacy).
    """
    ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
    if "webp" in content_type:
        ext = "webp"
    if "heic" in content_type:
        ext = "heic"

    if transaction_date is not None:
        mmddyy = transaction_date.strftime("%m%d%y")
        seq = _next_receipt_number_for_user_date(user, transaction_date)
        name = f"{user.strip()}-{mmddyy}-{seq:03d}.{ext}"
    else:
        name = f"{uuid4().hex}.{ext}"

    path = f"{_user_folder(user)}{name}"

    client = get_client()
    client.storage.from_(BUCKET).upload(
        path,
        file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    return f"{base}/storage/v1/object/public/{BUCKET}/{path}"


def _amount_for_db(amount: float):
    """Send whole numbers as int so PostgreSQL numeric/bigint columns accept it."""
    amt = round(amount, 2)
    return int(amt) if amt == int(amt) else amt


def insert_transaction(
    *,
    date_val: date,
    user: str,
    category: str,
    amount: float,
    description: str = "",
    receipt_url: str | None = None,
) -> dict:
    """Insert a transaction row and return the created record."""
    client = get_client()
    today = date.today().isoformat()
    row = {
        "date": date_val.isoformat(),
        "user": user.strip(),
        "category": category.strip(),
        "amount": _amount_for_db(amount),
        "description": (description or "").strip(),
        "receipt_url": receipt_url or None,
        "created_date": today,
    }
    resp = client.table("transactions").insert(row).execute()
    return first_row(resp, or_raise=True)
