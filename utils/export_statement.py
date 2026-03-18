"""
Statement PDF export: table (Date, Description, Category, Amount, Receipt).
Receipt pages are handled by utils.export_receipt when include_receipts=True.

Public API:
- generate_receipts_pdf(): build PDF (statement only, or statement + receipt pages via export_receipt).
- transactions_for_month_user(): filter transactions by month and optional user.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reportlab.pdfgen.canvas import Canvas

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    from utils import export_receipt
    from reportlab.pdfgen import canvas

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from utils.transaction_utils import receipt_filename_from_url, sort_transactions_chronological

# -----------------------------------------------------------------------------
# Statement table layout
# -----------------------------------------------------------------------------
_TABLE_MARGIN = 0.5 * inch
_TABLE_ROW_HEIGHT = 0.25 * inch
# Date, Description, Category, Amount, Receipt (Receipt wider for KP-030126-001.jpg)
_TABLE_COL_WIDTHS = (0.9 * inch, 1.7 * inch, 2.7 * inch, 1.0 * inch, 1.1 * inch)
_TABLE_FONT_SIZE = 8
_TABLE_HEADER_FONT_SIZE = 9
_TABLE_HEADERS = ("Date", "Description", "Category", "Amount", "Receipt")

_HEADING_TITLE_SIZE = 14
_HEADING_SUB_SIZE = 10
_HEADING_TOP_OFFSET = 10  # pt from top margin to title baseline
_HEADING_TITLE_TO_USER = 16  # pt from title baseline to "User:" baseline
_HEADING_USER_TO_TABLE = 28  # pt from "User:" to table top when user present; 16 when not
_HEADING_TO_TABLE_GAP = 0.2 * inch  # extra gap between heading block and table

_CELL_PAD = 5  # pt from cell edge to text
_TOTAL_GAP = 22  # pt below table before total line

def _draw_table_cell(
    c: "Canvas",
    row_y: float,
    x: float,
    width: float,
    text: str,
    *,
    bold: bool = False,
    align_right: bool = False,
) -> None:
    """Draw one table cell; row_y is the logical top of the row (text drawn below)."""
    font_name = "Helvetica-Bold" if bold else "Helvetica"
    font_size = _TABLE_HEADER_FONT_SIZE if bold else _TABLE_FONT_SIZE
    c.setFont(font_name, font_size)
    max_ch = max(6, int((width - 2 * _CELL_PAD) / (font_size * 0.5)))
    if len(text) > max_ch:
        text = text[: max_ch - 1] + "…"
    text = text or "—"
    if align_right:
        tw = c.stringWidth(text, font_name, font_size)
        cell_x = x + width - _CELL_PAD - tw
    else:
        cell_x = x + _CELL_PAD
    c.drawString(cell_x, row_y - font_size - 2, text)


def _filename_from_receipt_url(url: str) -> str:
    """Derive display filename from receipt_url (last path segment)."""
    segment = receipt_filename_from_url(url)
    return segment if segment else "—"


def _transaction_to_cells(t: dict, currency: str) -> list[str]:
    """Convert a transaction dict to a row of cell strings (Date, Description, Category, Amount, Receipt)."""
    date_val = str(t.get("date", ""))
    desc = (t.get("description") or "").strip() or "—"
    category = str(t.get("category", ""))
    amount = t.get("amount")
    amount_str = f"{currency}{float(amount):,.2f}" if amount not in (None, "") else "—"
    url = t.get("receipt_url") or ""
    receipt = _filename_from_receipt_url(url) if url else "—"
    return [date_val, desc, category, amount_str, receipt]


def _statement_table_top_y(page_height: float, user_name: str) -> float:
    """Return the y-coordinate for the top of the statement table (no drawing)."""
    margin = _TABLE_MARGIN
    baseline = page_height - 2 * margin - _HEADING_TOP_OFFSET
    return baseline - (_HEADING_USER_TO_TABLE if user_name else 16) - _HEADING_TO_TABLE_GAP


def _draw_statement_heading(
    c: "Canvas",
    page_height: float,
    month_label: str,
    user_name: str,
) -> float:
    """Draw title and user line; return y of table top (below the heading block)."""
    margin = _TABLE_MARGIN
    baseline = page_height - 2 * margin - _HEADING_TOP_OFFSET
    c.setFont("Helvetica-Bold", _HEADING_TITLE_SIZE)
    title = f"Statement for {month_label}" if month_label else "Statement"
    c.drawString(margin, baseline, title)
    if user_name:
        c.setFont("Helvetica", _HEADING_SUB_SIZE)
        c.drawString(margin, baseline - _HEADING_TITLE_TO_USER, f"User: {user_name}")
    return _statement_table_top_y(page_height, user_name)


def _draw_statement_table_grid(
    c: "Canvas",
    x_start: float,
    table_top_y: float,
    y_bottom: float,
    n_rows: int,
) -> None:
    """Draw horizontal and vertical lines for one table page."""
    total_w = sum(_TABLE_COL_WIDTHS)
    for i in range(2 + n_rows):
        yy = table_top_y - i * _TABLE_ROW_HEIGHT
        c.line(x_start, yy, x_start + total_w, yy)
    for col_i in range(len(_TABLE_COL_WIDTHS) + 1):
        x = x_start + sum(_TABLE_COL_WIDTHS[:col_i])
        c.line(x, y_bottom, x, table_top_y)


def _draw_statement_header_row(c: "Canvas", x_start: float, table_top_y: float) -> None:
    """Draw the header row (Date, Description, Category, Amount, Receipt)."""
    header_baseline_y = table_top_y - _TABLE_ROW_HEIGHT + 10
    header_row_y = header_baseline_y + _TABLE_HEADER_FONT_SIZE + 2
    xx = x_start
    for i, (header, w) in enumerate(zip(_TABLE_HEADERS, _TABLE_COL_WIDTHS)):
        _draw_table_cell(c, header_row_y, xx, w, header, bold=True, align_right=(i == 3))
        xx += w


def _draw_statement_data_rows(
    c: "Canvas",
    x_start: float,
    table_top_y: float,
    transactions: list[dict],
    currency: str,
) -> None:
    """Draw data rows for the given transactions."""
    for row_idx, t in enumerate(transactions):
        row_y = table_top_y - (1 + row_idx) * _TABLE_ROW_HEIGHT
        cells = _transaction_to_cells(t, currency)
        xx = x_start
        for i, (cell, w) in enumerate(zip(cells, _TABLE_COL_WIDTHS)):
            _draw_table_cell(c, row_y, xx, w, cell, align_right=(i == 3))
            xx += w


def _draw_statement_total(
    c: "Canvas",
    x_start: float,
    y_bottom: float,
    transactions: list[dict],
    currency: str,
) -> None:
    """Draw the total line below the table."""
    total = sum(float(t.get("amount") or 0) for t in transactions)
    c.setFont("Helvetica-Bold", _TABLE_FONT_SIZE)
    total_text = f"Total: {currency}{total:,.2f}"
    tw = c.stringWidth(total_text, "Helvetica-Bold", _TABLE_FONT_SIZE)
    amount_col_right = x_start + sum(_TABLE_COL_WIDTHS[:4])
    c.drawString(amount_col_right - tw - _CELL_PAD, y_bottom - _TOTAL_GAP, total_text)


def _draw_statement_pages(
    c: "Canvas",
    transactions: list[dict],
    page_size: tuple[float, float],
    currency: str,
    month_label: str = "",
    user_name: str = "",
) -> None:
    """Draw statement table across one or more pages."""
    page_width, page_height = page_size
    margin = _TABLE_MARGIN
    x_start = margin
    total_table_w = sum(_TABLE_COL_WIDTHS)

    table_top_y = _draw_statement_heading(c, page_height, month_label, user_name)
    available_height = table_top_y - margin - 2 * _TABLE_ROW_HEIGHT
    rows_per_page = max(1, int(available_height / _TABLE_ROW_HEIGHT))

    offset = 0
    while offset < len(transactions):
        chunk = transactions[offset : offset + rows_per_page]
        n_rows = len(chunk)
        y_bottom = table_top_y - (1 + n_rows) * _TABLE_ROW_HEIGHT

        _draw_statement_table_grid(c, x_start, table_top_y, y_bottom, n_rows)
        _draw_statement_header_row(c, x_start, table_top_y)
        _draw_statement_data_rows(c, x_start, table_top_y, chunk, currency)
        _draw_statement_total(c, x_start, y_bottom, chunk, currency)

        offset += len(chunk)
        if offset < len(transactions):
            c.showPage()
            # Continuation page: no heading redraw, just position table
            table_top_y = _statement_table_top_y(page_height, user_name)
            available_height = table_top_y - margin - 2 * _TABLE_ROW_HEIGHT
            rows_per_page = max(1, int(available_height / _TABLE_ROW_HEIGHT))


def _sort_chronological(transactions: list[dict]) -> list[dict]:
    """Return a new list sorted by date ascending, then id (for statement and receipt order)."""
    return sort_transactions_chronological(transactions)


def generate_receipts_pdf(
    transactions: list[dict],
    output_path: str | Path | None = None,
    output_buffer: BytesIO | None = None,
    receipts_per_page: int = 15,
    page_size: tuple[float, float] | None = None,
    currency: str = "$",
    include_receipts: bool = True,
    include_statement: bool = True,
    statement_month_label: str = "",
    statement_user_name: str = "",
) -> bytes | None:
    """
    Generate a PDF with optional statement table and/or receipt pages (receipts via utils.export_receipt).

    Transactions are shown in chronological order (date, then id). Receipt pages use A4, 5×2 layout.

    Args:
        transactions: List of dicts with date, user, category, amount, description, receipt_url.
        output_path: Write PDF to this path (mutually exclusive with output_buffer).
        output_buffer: Write PDF bytes here (mutually exclusive with output_path).
        receipts_per_page: Receipt thumbnails per page (default 15 for grid 3 sections × 5 cols).
        page_size: Page size in points; default letter for statement-only, A4 when receipts included.
        currency: Symbol for amounts (e.g. "$", "¥").
        include_statement: If True, include statement table.
        include_receipts: If True, include receipt pages (from utils.export_receipt).
        statement_month_label: Heading text e.g. "March 2026".
        statement_user_name: Heading text e.g. "user-1" or "All users".

    Returns:
        PDF bytes if output_buffer was provided, else None.
    """
    if not HAS_REPORTLAB:
        raise RuntimeError("Install reportlab and Pillow for PDF export: pip install reportlab pillow")

    sorted_tx = _sort_chronological(transactions)
    effective_page_size = A4 if include_receipts else (page_size or letter)
    dest = output_buffer if output_buffer is not None else str(output_path)
    c = canvas.Canvas(dest, pagesize=effective_page_size)

    if include_statement:
        _draw_statement_pages(
            c, sorted_tx, effective_page_size, currency,
            month_label=statement_month_label,
            user_name=statement_user_name,
        )
        if not include_receipts:
            c.save()
            return output_buffer.getvalue() if output_buffer is not None else None
        c.showPage()

    if include_receipts:
        export_receipt.draw_receipt_pages(
            c,
            sorted_tx,
            effective_page_size,
            receipts_per_page,
            heading_suffix=statement_month_label,
        )

    c.save()
    return output_buffer.getvalue() if output_buffer is not None else None


def transactions_for_month_user(
    transactions: list[dict],
    month: date,
    user: str | None,
) -> list[dict]:
    """Filter transactions by month and optional user; return sorted by date then id."""
    out = []
    for t in transactions:
        d = t.get("date")
        if not d:
            continue
        if isinstance(d, str):
            d = date.fromisoformat(d)
        if d.year != month.year or d.month != month.month:
            continue
        if user and t.get("user") != user:
            continue
        out.append(t)
    return sorted(out, key=lambda x: (x.get("date"), x.get("id")))
