"""Export receipts for print: multiple receipts per page."""
from datetime import date
from pathlib import Path
import sys

# Allow running from project root with utils on path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from PIL import Image
    from io import BytesIO
    import urllib.request
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def _fetch_image_as_reader(url: str) -> ImageReader | None:
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


def generate_receipts_pdf(
    transactions: list[dict],
    output_path: str | Path | None = None,
    output_buffer: "BytesIO | None" = None,
    receipts_per_page: int = 4,
    page_size=letter,
) -> bytes | None:
    """
    Generate a PDF with receipt thumbnails and details, multiple per page.
    Each transaction should have: date, user, category, amount, description, receipt_url.
    Pass either output_path (file path) or output_buffer (BytesIO). If buffer, returns PDF bytes.
    """
    if not HAS_REPORTLAB:
        raise RuntimeError("Install reportlab and Pillow for PDF export: pip install reportlab pillow")

    dest = output_buffer if output_buffer is not None else str(output_path)
    c = canvas.Canvas(dest, pagesize=page_size)
    w, h = page_size
    margin = 0.5 * inch
    cols = 2
    rows = 2
    cell_w = (w - 2 * margin) / cols
    cell_h = (h - 2 * margin) / rows
    img_h = 1.8 * inch
    line_h = 0.2 * inch

    for idx, t in enumerate(transactions):
        row = idx % rows
        col = (idx // rows) % cols
        if idx > 0 and (idx % receipts_per_page) == 0:
            c.showPage()

        x = margin + col * cell_w
        y = h - margin - (row + 1) * cell_h

        # Receipt image
        url = t.get("receipt_url") or ""
        ir = _fetch_image_as_reader(url) if url else None
        if ir:
            try:
                iw, ih = ir.getSize()
                scale = min(cell_w / iw, img_h / ih, 1.0)
                c.drawImage(ir, x, y + cell_h - img_h, width=iw * scale, height=ih * scale)
            except Exception:
                pass

        # Text block
        text_y = y + cell_h - img_h - line_h
        c.setFont("Helvetica", 8)
        c.drawString(x, text_y, str(t.get("date", "")))
        text_y -= line_h
        c.drawString(x, text_y, f"{t.get('category', '')}  ${float(t.get('amount') or 0):.2f}")
        text_y -= line_h
        desc = (t.get("description") or "")[:40]
        if desc:
            c.drawString(x, text_y, desc)

    c.save()
    if output_buffer is not None:
        return output_buffer.getvalue()
    return None


def transactions_for_month_user(transactions: list[dict], month: date, user: str | None) -> list[dict]:
    """Filter transactions by month and optional user (for PDF export)."""
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
