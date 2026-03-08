"""Date parsing and formatting utilities for receipts."""

from datetime import datetime
import re


DISPLAY_FORMAT = "%Y-%m-%d"
SHEETS_FORMAT = "%Y-%m-%d"


def parse_date(value: str) -> datetime | None:
    """
    Parse a date string in various formats.
    Supports: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, etc.
    """
    if not value or not value.strip():
        return None

    value = value.strip()
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%d.%m.%Y",
        "%B %d, %Y",  # January 15, 2024
        "%b %d, %Y",  # Jan 15, 2024
        "%d %B %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    # Try ISO format with time
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass

    return None


def format_date_for_display(dt: datetime) -> str:
    """Format datetime for display in the UI."""
    return dt.strftime(DISPLAY_FORMAT)


def format_date_for_sheets(dt: datetime) -> str:
    """Format datetime for storage in Google Sheets."""
    return dt.strftime(SHEETS_FORMAT)


def parse_and_format(value: str) -> str:
    """
    Parse a date string and return in standard YYYY-MM-DD format.
    Returns empty string if parsing fails.
    """
    dt = parse_date(value)
    if dt:
        return format_date_for_sheets(dt)
    return ""


def is_valid_date(value: str) -> bool:
    """Check if the value is a valid parseable date."""
    return parse_date(value) is not None
