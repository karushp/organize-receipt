#!/usr/bin/env python3
"""
Draw the receipt grid: heading, line, 3 sections (name row + line + image row each),
GAP between sections. Placeholder text in cells (receipt-1..15, image-1..15).

Run from project root:
  uv run python scripts/test_receipt_grid.py

Output: receipt_grid_test.pdf
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reportlab.pdfgen import canvas

from utils.receipt_grid import (
    get_page_size,
    get_receipt_grid_layout,
    get_heading_line_y,
    get_section_separator_lines,
    get_gap_rects,
    get_receipt_cell_rect,
)


def main():
    out_path = ROOT / "receipt_grid_test.pdf"
    page_size = get_page_size()
    w, h = page_size
    layout = get_receipt_grid_layout(page_size)
    m = layout["margin"]

    c = canvas.Canvas(str(out_path), pagesize=page_size)

    # Page border (light gray)
    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    c.rect(m, m, w - 2 * m, h - 2 * m, stroke=1, fill=0)

    # Heading
    c.setFont("Helvetica-Bold", 12)
    c.drawString(m, h - m - 14, "Receipts")

    # Line below heading
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    y_heading_line = get_heading_line_y(page_size)
    c.line(m, y_heading_line, w - m, y_heading_line)

    # All separator lines (below each name row, below each image row, GAP boundaries)
    for x1, y, x2, _ in get_section_separator_lines(page_size):
        c.line(x1, y, x2, y)

    c.setLineWidth(0.5)
    # Cell borders and labels: name row then image row per section
    for section in range(layout["sections"]):
        for col in range(layout["cols"]):
            idx = section * layout["cols"] + col + 1
            for cell_type in ("name", "image"):
                left, bottom, cw, ch = get_receipt_cell_rect(section, col, cell_type, page_size)
                c.rect(left, bottom, cw, ch, stroke=1, fill=0)
                label = f"receipt-{idx}" if cell_type == "name" else f"image-{idx}"
                c.setFont("Helvetica", 7)
                c.drawString(left + 2, bottom + ch - 9, label[:14] + ("…" if len(label) > 14 else ""))

    # Gap bands between sections (no label; separator lines already drawn)
    for (left, bottom, gw, gh) in get_gap_rects(page_size):
        c.rect(left, bottom, gw, gh, stroke=1, fill=0)

    c.save()
    print(f"Wrote {out_path}")
    print("Layout: heading, line, then 3 sections (name row + line + image row), gap between sections.")


if __name__ == "__main__":
    main()
