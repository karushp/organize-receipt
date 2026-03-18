"""Shared helpers for transaction/receipt exports."""

from __future__ import annotations


def sort_transactions_chronological(transactions: list[dict]) -> list[dict]:
    """Return a new list sorted by date ascending, then id (stable for statement/receipts)."""
    return sorted(transactions, key=lambda x: (x.get("date") or "", x.get("id") or ""))


def receipt_filename_from_url(url: str) -> str:
    """Return last path segment from receipt_url (query stripped) or empty string."""
    if not url or not url.strip():
        return ""
    path = url.rstrip("/").split("?", 1)[0]
    return path.rstrip("/").split("/")[-1] or ""

