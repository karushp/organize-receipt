"""
Receipt-only PDF export: uses receipt_grid layout (heading, line, 3 sections of name row + image row).
Draws receipt name in each name cell and receipt image in each image cell. Sorted by date. No statement.

Public API:
- generate_receipts_pdf(): build receipts-only PDF to buffer or path.
- draw_receipt_pages(): draw receipt pages onto an existing canvas (for statement+receipts).
"""

from __future__ import annotations

from datetime import date as date_type
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reportlab.pdfgen.canvas import Canvas

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from PIL import Image
    import urllib.request

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from utils.receipt_grid import (
    get_page_size,
    get_receipt_grid_layout,
    get_receipt_cell_rect,
    COLS,
    SECTIONS,
)
from utils.transaction_utils import receipt_filename_from_url, sort_transactions_chronological

RECEIPTS_PER_PAGE = COLS * SECTIONS  # 15
_NAME_FONT_SIZE = 6


def _receipt_name(t: dict) -> str:
    """Display name: saved file name {user}-{MMDDYY}-{seq}.ext from receipt_url, else {user}-{date}."""
    url = (t.get("receipt_url") or "").strip()
    segment = receipt_filename_from_url(url)
    if segment:
        return segment
    user = (t.get("user") or "").strip()
    d = t.get("date")
    if d and user:
        if hasattr(d, "strftime"):
            date_str = d.strftime("%m%d%y")
        elif isinstance(d, str):
            try:
                date_str = date_type.fromisoformat(d).strftime("%m%d%y")
            except (ValueError, TypeError):
                date_str = ""
        else:
            date_str = ""
        if date_str:
            return f"{user}-{date_str}"
    return user or "—"


def _fetch_image_as_reader(url: str) -> ImageReader | None:
    """Fetch image from URL and return a ReportLab ImageReader, or None on failure."""
    if not HAS_REPORTLAB or not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = r.read()
        img = Image.open(BytesIO(data))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return ImageReader(buf)
    except Exception:
        return None


def _sort_by_date(transactions: list[dict]) -> list[dict]:
    """Return a new list sorted by date first (ascending), then id."""
    return sort_transactions_chronological(transactions)


def _truncate_to_width(c: "Canvas", text: str, max_width: float, font: str = "Helvetica", size: int = _NAME_FONT_SIZE) -> str:
    """Return text truncated with … to fit max_width."""
    if not text:
        return text
    if c.stringWidth(text, font, size) <= max_width:
        return text
    suffix = "…"
    while len(text) > 1:
        text = text[:-1]
        if c.stringWidth(text + suffix, font, size) <= max_width:
            return text + suffix
    return suffix


def _draw_receipt_name_in_cell(c: "Canvas", name: str, left: float, bottom: float, width: float, height: float) -> None:
    """Draw receipt name in a name cell; truncate to fit width."""
    c.setFont("Helvetica", _NAME_FONT_SIZE)
    label = _truncate_to_width(c, name, width - 4)
    # Baseline near top of cell, with small padding
    baseline = bottom + height - 4
    c.drawString(left + 2, baseline, label)


def _draw_receipt_image_in_cell(
    c: "Canvas",
    url: str,
    left: float,
    bottom: float,
    width: float,
    height: float,
) -> None:
    """Draw receipt image in cell; fill the box (cover) and clip to cell."""
    ir = _fetch_image_as_reader(url) if url else None
    if not ir:
        return
    try:
        iw, ih = ir.getSize()
        if not iw or not ih:
            return

        # Cover-fit into an inset rect so we leave a tiny white border.
        inset = 1  # points
        draw_left = left + inset
        draw_bottom = bottom + inset
        draw_width = max(0, width - 2 * inset)
        draw_height = max(0, height - 2 * inset)
        if draw_width <= 0 or draw_height <= 0:
            return

        # Scale so the inset rect is fully filled, then clip overflow.
        scale = max(draw_width / iw, draw_height / ih)
        draw_w, draw_h = iw * scale, ih * scale
        img_x = draw_left + (draw_width - draw_w) / 2
        img_y = draw_bottom + (draw_height - draw_h) / 2

        c.saveState()
        p = c.beginPath()
        p.rect(draw_left, draw_bottom, draw_width, draw_height)
        c.clipPath(p, stroke=0, fill=0)
        c.drawImage(ir, img_x, img_y, width=draw_w, height=draw_h)
        c.restoreState()
    except Exception:
        pass


def _with_receipts_only(transactions: list[dict]) -> list[dict]:
    """Return transactions that have a receipt (non-empty receipt_url)."""
    return [t for t in transactions if (t.get("receipt_url") or "").strip()]


def _draw_one_receipt_page(
    c: "Canvas",
    transactions: list[dict],
    page_size: tuple[float, float],
    *,
    heading_suffix: str = "",
) -> None:
    """Draw one page: heading, then up to 15 receipts in grid cells (white background, no grid lines)."""
    layout = get_receipt_grid_layout(page_size)
    m = layout["margin"]

    # Heading (no lines; white grid)
    c.setFont("Helvetica-Bold", 12)
    heading = "Receipts"
    if heading_suffix:
        heading = f"{heading} — {heading_suffix}"
    c.drawString(m, layout["page_h"] - m - 14, heading)

    # Fill name and image cells for each receipt
    for idx, t in enumerate(transactions):
        if idx >= RECEIPTS_PER_PAGE:
            break
        section = idx // COLS
        col = idx % COLS
        left_n, bottom_n, w_n, h_n = get_receipt_cell_rect(section, col, "name", page_size)
        left_i, bottom_i, w_i, h_i = get_receipt_cell_rect(section, col, "image", page_size)
        _draw_receipt_name_in_cell(c, _receipt_name(t), left_n, bottom_n, w_n, h_n)
        _draw_receipt_image_in_cell(c, (t.get("receipt_url") or "").strip(), left_i, bottom_i, w_i, h_i)


def draw_receipt_pages(
    c: "Canvas",
    transactions: list[dict],
    page_size: tuple[float, float],
    receipts_per_page: int = RECEIPTS_PER_PAGE,
    *,
    heading_suffix: str = "",
) -> None:
    """
    Draw receipt pages onto an existing canvas using receipt_grid layout.
    Only transactions with receipt_url are printed, sorted by date first.
    """
    with_receipts = _with_receipts_only(transactions)
    if not with_receipts:
        return
    sorted_tx = sort_transactions_chronological(with_receipts)

    for offset in range(0, len(sorted_tx), receipts_per_page):
        if offset > 0:
            c.showPage()
        chunk = sorted_tx[offset : offset + receipts_per_page]
        _draw_one_receipt_page(c, chunk, page_size, heading_suffix=heading_suffix)


def generate_receipts_pdf(
    transactions: list[dict],
    output_path: str | Path | None = None,
    output_buffer: BytesIO | None = None,
    page_size: tuple[float, float] | None = None,
    *,
    heading_suffix: str = "",
) -> bytes | None:
    """
    Generate a receipts-only PDF using receipt_grid (heading, 3 sections of name+image rows per page).

    Args:
        transactions: List of dicts with date, receipt_url, user, etc.
        output_path: Write PDF here (mutually exclusive with output_buffer).
        output_buffer: Write PDF bytes here (mutually exclusive with output_path).
        page_size: A4 if not specified.

    Returns:
        PDF bytes if output_buffer was provided, else None.
    """
    if not HAS_REPORTLAB:
        raise RuntimeError("Install reportlab and Pillow for PDF export: pip install reportlab pillow")

    size = page_size or get_page_size()
    dest = output_buffer if output_buffer is not None else str(output_path)
    c = canvas.Canvas(dest, pagesize=size)
    draw_receipt_pages(c, transactions, size, RECEIPTS_PER_PAGE, heading_suffix=heading_suffix)
    c.save()
    return output_buffer.getvalue() if output_buffer is not None else None
