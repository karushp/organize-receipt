"""
Receipt print grid: A4, heading + line, then 3 sections.
Each section = name row (5 cells) + line + image row (5 cells).
GAP (with lines above/below) between sections.
"""

from __future__ import annotations

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
except ImportError:
    A4 = (595.28, 841.89)
    inch = 72.0

# Page
MARGIN_PT = 0.5 * inch
COLS = 5
SECTIONS = 3

# Top: heading then line below it
HEADING_HEIGHT_PT = 24
LINE_PT = 1

# Per section: name row, line, image row
NAME_ROW_HEIGHT_PT = 14
GAP_HEIGHT_PT = 12  # space for "GAP" band (lines above/below are LINE_PT each)

CELLS_PER_PAGE = COLS * SECTIONS * 2  # 30: 3 sections × (1 name row + 1 image row) × 5 cols


def get_page_size():
    """Return (width_pt, height_pt) for A4."""
    return A4


def get_receipt_grid_layout(page_size: tuple[float, float] | None = None) -> dict:
    """
    Layout for receipt print: heading, line, then 3 sections with GAPs between.
    Returns dict with: margin, cols, sections, cell_w, name_row_height, image_row_height,
    heading_height, line_pt, gap_height, page_w, page_h, content_top_y,
    and lists for drawing: section_rects, gap_rects, separator_lines.
    """
    w, h = page_size or get_page_size()
    m = MARGIN_PT
    content_top = h - m - HEADING_HEIGHT_PT - LINE_PT  # y of top of first section (below heading line)
    content_height = content_top - m  # from top of section 1 down to bottom margin

    # content_height = 3 * (name_row + line + image_row) + 2 * (gap + 2*line)
    # image_row_height = (content_height - 3*NAME_ROW_HEIGHT_PT - 3*LINE_PT - 2*GAP_HEIGHT_PT - 4*LINE_PT) / 3
    image_row_height = (
        content_height
        - 3 * NAME_ROW_HEIGHT_PT
        - 7 * LINE_PT
        - 2 * GAP_HEIGHT_PT
    ) / 3

    usable_w = w - 2 * m
    cell_w = usable_w / COLS

    section_height = NAME_ROW_HEIGHT_PT + LINE_PT + image_row_height
    gap_band_height = GAP_HEIGHT_PT + 2 * LINE_PT

    return {
        "margin": m,
        "cols": COLS,
        "sections": SECTIONS,
        "cell_w": cell_w,
        "name_row_height": NAME_ROW_HEIGHT_PT,
        "image_row_height": image_row_height,
        "heading_height": HEADING_HEIGHT_PT,
        "line_pt": LINE_PT,
        "gap_height": GAP_HEIGHT_PT,
        "page_w": w,
        "page_h": h,
        "content_top_y": content_top,
        "section_height": section_height,
        "gap_band_height": gap_band_height,
    }


def _section_top_y(layout: dict, section: int) -> float:
    """Y (bottom-left coords) of the top of this section (below name row + line, so top of image row)."""
    ct = layout["content_top_y"]
    sh = layout["section_height"]
    gb = layout["gap_band_height"]
    # Section 0 top = ct - 0 - 0 = ct (top of name row). Bottom of section 0 = ct - sh.
    # Section 1 starts after GAP: top = ct - sh - gb. Section 2: ct - 2*sh - 2*gb.
    return ct - section * (sh + gb)


def get_receipt_cell_rect(
    section: int,
    col: int,
    cell_type: str,
    page_size: tuple[float, float] | None = None,
) -> tuple[float, float, float, float]:
    """
    Return (left_pt, bottom_pt, width_pt, height_pt) for a cell.
    cell_type is 'name' or 'image'. section 0,1,2.
    """
    layout = get_receipt_grid_layout(page_size)
    m = layout["margin"]
    cw = layout["cell_w"]
    ph = layout["page_h"]
    section_top = _section_top_y(layout, section)
    name_h = layout["name_row_height"]
    image_h = layout["image_row_height"]
    line_pt = layout["line_pt"]

    left = m + col * cw
    if cell_type == "name":
        # Name row is at top of section
        bottom = section_top - name_h
        return (left, bottom, cw, name_h)
    else:  # image
        # Image row is below the line
        bottom = section_top - name_h - line_pt - image_h
        return (left, bottom, cw, image_h)


def iter_receipt_cells(page_size: tuple[float, float] | None = None):
    """Yield (section, col, cell_type, left, bottom, width, height) for each cell. Order: section 0..2, name then image, col 0..4."""
    layout = get_receipt_grid_layout(page_size)
    for section in range(layout["sections"]):
        for col in range(layout["cols"]):
            for cell_type in ("name", "image"):
                left, bottom, w, h = get_receipt_cell_rect(section, col, cell_type, page_size)
                yield section, col, cell_type, left, bottom, w, h


def get_heading_line_y(page_size: tuple[float, float] | None = None) -> float:
    """Y position of the horizontal line below the heading."""
    layout = get_receipt_grid_layout(page_size)
    return layout["page_h"] - layout["margin"] - layout["heading_height"]


def get_section_separator_lines(page_size: tuple[float, float] | None = None) -> list[tuple[float, float, float, float]]:
    """List of (x1, y, x2, y) for horizontal lines: below heading, below each name row, above/below each GAP."""
    layout = get_receipt_grid_layout(page_size)
    m, w = layout["margin"], layout["page_w"]
    lines = []
    # Line below heading
    y = get_heading_line_y(page_size)
    lines.append((m, y, w - m, y))

    ct = layout["content_top_y"]
    sh = layout["section_height"]
    gb = layout["gap_band_height"]
    name_h = layout["name_row_height"]
    line_pt = layout["line_pt"]

    for s in range(layout["sections"]):
        section_top = ct - s * (sh + gb)
        # Line below name row (above image row)
        y = section_top - name_h
        lines.append((m, y, w - m, y))
        # Line below image row (top of section bottom or top of GAP)
        y = section_top - name_h - line_pt - layout["image_row_height"]
        lines.append((m, y, w - m, y))

    # GAP band boundaries: after section 0 and 1, we have a GAP. Top of GAP = bottom of section (already have line). Bottom of GAP = top of next section - so we need line at top of next section (which is section_top for s+1). So line at section_top for s=1 and s=2.
    for s in range(1, layout["sections"]):
        section_top_next = ct - s * (sh + gb)
        lines.append((m, section_top_next, w - m, section_top_next))

    return lines


def get_gap_rects(page_size: tuple[float, float] | None = None) -> list[tuple[float, float, float, float]]:
    """List of (left, bottom, width, height) for each GAP band (for drawing 'GAP' text or background)."""
    layout = get_receipt_grid_layout(page_size)
    m, w = layout["margin"], layout["page_w"]
    ct = layout["content_top_y"]
    sh = layout["section_height"]
    gb = layout["gap_band_height"]
    usable_w = w - 2 * m

    rects = []
    for s in range(layout["sections"] - 1):
        bottom = ct - (s + 1) * (sh + gb)
        rects.append((m, bottom, usable_w, gb))
    return rects
