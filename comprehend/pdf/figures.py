"""Detect composite figure regions on PDF pages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

FIGURE_CAPTION_PATTERN = re.compile(r"^(?:Figure|Fig\.?)\s+(\d+)\s*[:.]")
PAGE_TOP_MARGIN = 20.0
REGION_PADDING = 5.0
CAPTION_MAX_LINES = 6
CAPTION_MAX_HEIGHT = 100.0
LINE_GAP_THRESHOLD = 8.0
MIN_CONTENT_SIZE = 8.0
MIN_CLIPPED_AREA = 64.0


@dataclass(frozen=True)
class FigureCaption:
    """A figure caption block on a PDF page."""

    number: int
    rect: fitz.Rect
    page: int
    text: str


@dataclass(frozen=True)
class FigureRegion:
    """Bounding box for a numbered figure on a page."""

    page: int
    number: int
    clip: tuple[float, float, float, float]
    caption: str



def _line_text(line: dict) -> str:
    return "".join(span["text"] for span in line["spans"])


def _rect_from_lines(lines: list[dict]) -> fitz.Rect:
    rect = fitz.Rect(lines[0]["bbox"])
    for line in lines[1:]:
        rect |= fitz.Rect(line["bbox"])
    return rect


def _clip_rect_to_band(rect: fitz.Rect, top_y: float, bottom_y: float) -> fitz.Rect | None:
    """Return ``rect`` intersected with a vertical band, or ``None`` if too small."""
    clipped = fitz.Rect(
        rect.x0,
        max(top_y, rect.y0),
        rect.x1,
        min(bottom_y, rect.y1),
    )
    if clipped.is_empty or clipped.is_infinite:
        return None

    if clipped.width < MIN_CONTENT_SIZE or clipped.height < MIN_CONTENT_SIZE:
        return None

    if clipped.width * clipped.height < MIN_CLIPPED_AREA:
        return None

    return clipped


def _caption_from_block(block: dict, *, page_number: int) -> FigureCaption | None:
    """Extract a figure caption from a text block using line-level bounds.

    PDF text blocks often merge the caption with unrelated body text in the
    same column. We keep only the opening caption lines (small vertical gaps,
    bounded line count and height) instead of the full block bbox.
    """
    caption_lines: list[dict] = []
    figure_number: int | None = None

    for line in block["lines"]:
        text = _line_text(line).strip()
        if figure_number is None:
            match = FIGURE_CAPTION_PATTERN.match(text)
            if match is None:
                continue

            figure_number = int(match.group(1))
            caption_lines.append(line)
            continue

        previous_line = caption_lines[-1]
        gap = line["bbox"][1] - previous_line["bbox"][3]
        caption_height = line["bbox"][3] - caption_lines[0]["bbox"][1]
        if (
            gap > LINE_GAP_THRESHOLD
            or len(caption_lines) >= CAPTION_MAX_LINES
            or caption_height > CAPTION_MAX_HEIGHT
        ):
            break

        caption_lines.append(line)

    if figure_number is None or not caption_lines:
        return None

    return FigureCaption(
        number=figure_number,
        rect=_rect_from_lines(caption_lines),
        page=page_number,
        text="".join(_line_text(line) for line in caption_lines).strip(),
    )


def find_figure_captions(page: fitz.Page, *, page_number: int) -> list[FigureCaption]:
    """Return figure captions on a page sorted by vertical position.

    Args:
        page: PyMuPDF page object.
        page_number: 1-based page index for metadata.

    Returns:
        Captions whose text starts with ``Figure N:`` or ``Figure N.``.
    """
    captions: list[FigureCaption] = []
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        if block.get("type") != 0:
            continue

        caption = _caption_from_block(block, page_number=page_number)
        if caption is not None:
            captions.append(caption)

    captions.sort(key=lambda caption: caption.rect.y0)

    return captions


def _content_rects_in_band(page: fitz.Page, top_y: float, bottom_y: float) -> list[fitz.Rect]:
    """Return image and vector rects clipped to a vertical band."""
    rects: list[fitz.Rect] = []

    for image in page.get_images(full=True):
        xref = image[0]
        for rect in page.get_image_rects(xref):
            clipped = _clip_rect_to_band(rect, top_y, bottom_y)
            if clipped is not None:
                rects.append(clipped)

    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue

        clipped = _clip_rect_to_band(fitz.Rect(rect), top_y, bottom_y)
        if clipped is not None:
            rects.append(clipped)

    return rects


def _clip_from_rects(
    rects: list[fitz.Rect],
    *,
    page_rect: fitz.Rect,
    padding: float = REGION_PADDING,
) -> tuple[float, float, float, float]:
    x0 = min(rect.x0 for rect in rects) - padding
    y0 = min(rect.y0 for rect in rects) - padding
    x1 = max(rect.x1 for rect in rects) + padding
    y1 = max(rect.y1 for rect in rects) + padding

    clip = (
        max(page_rect.x0, x0),
        max(page_rect.y0, y0),
        min(page_rect.x1, x1),
        min(page_rect.y1, y1),
    )

    return clip


def figure_clip_on_page(
    page: fitz.Page,
    figure_number: int,
    *,
    include_caption: bool = True,
) -> tuple[float, float, float, float] | None:
    """Compute a clip rectangle for one numbered figure on a page.

    Composite paper figures are often split across many embedded images and
    vector paths. This unions all page content between the previous caption
    and the target caption so the rendered crop matches the full figure.

    Args:
        page: PyMuPDF page object.
        figure_number: Caption number such as ``4`` for ``Figure 4``.
        include_caption: When True, extend the clip through the caption block.

    Returns:
        ``(x0, y0, x1, y1)`` clip in PDF coordinates, or ``None`` if not found.
    """
    captions = find_figure_captions(page, page_number=0)
    previous_bottom = page.rect.y0 + PAGE_TOP_MARGIN
    target_caption: FigureCaption | None = None

    for caption in captions:
        if caption.number == figure_number:
            target_caption = caption
            top_y = previous_bottom
            content_bottom = caption.rect.y0
            break

        previous_bottom = caption.rect.y1

    if target_caption is None:
        return None

    content_rects = _content_rects_in_band(page, top_y, content_bottom)
    union_rects = list(content_rects)

    if include_caption:
        union_rects.append(target_caption.rect)

    if not union_rects:
        return None

    clip = _clip_from_rects(union_rects, page_rect=page.rect)

    return clip


def find_xref_page_and_rect(document: fitz.Document, xref: int) -> tuple[int, fitz.Rect] | None:
    """Locate the first on-page placement rectangle for an embedded image.

    Args:
        document: Open PDF document.
        xref: Embedded image xref.

    Returns:
        1-based page number and placement rectangle, or ``None``.
    """
    for page_index in range(document.page_count):
        page = document[page_index]
        for rect in page.get_image_rects(xref):
            return page_index + 1, rect

    return None


def _figure_band_for_anchor(
    page: fitz.Page,
    anchor_rect: fitz.Rect,
    *,
    include_caption: bool = True,
) -> tuple[FigureCaption | None, float, float]:
    """Return the caption and vertical band that contain an anchor rectangle."""
    captions = find_figure_captions(page, page_number=0)
    previous_bottom = page.rect.y0 + PAGE_TOP_MARGIN

    for caption in captions:
        content_top = previous_bottom
        content_bottom = caption.rect.y0
        anchor_center_y = (anchor_rect.y0 + anchor_rect.y1) / 2
        if content_top <= anchor_center_y <= content_bottom:
            return caption, content_top, content_bottom

        previous_bottom = caption.rect.y1

    if captions:
        last_caption = captions[-1]
        if anchor_rect.y0 >= last_caption.rect.y1 - 1:
            return None, last_caption.rect.y1, page.rect.y1

        first_caption = captions[0]
        return None, page.rect.y0 + PAGE_TOP_MARGIN, first_caption.rect.y0

    return None, page.rect.y0 + PAGE_TOP_MARGIN, page.rect.y1


def figure_clip_for_xref(
    pdf_path: Path,
    xref: int,
    *,
    include_caption: bool = True,
) -> tuple[int, tuple[float, float, float, float]] | None:
    """Resolve an embedded image xref to its full composite figure clip.

    Args:
        pdf_path: Path to the PDF file.
        xref: Embedded image xref from :func:`list_figures`.
        include_caption: When True, include the figure caption in the clip.

    Returns:
        ``(page, clip)`` tuple, or ``None`` when the xref is not on any page.
    """
    document = fitz.open(pdf_path)
    location = find_xref_page_and_rect(document, xref)

    if location is None:
        document.close()
        return None

    page_number, anchor_rect = location
    page = document[page_number - 1]
    caption, top_y, content_bottom = _figure_band_for_anchor(
        page,
        anchor_rect,
        include_caption=include_caption,
    )

    content_rects = _content_rects_in_band(page, top_y, content_bottom)
    union_rects = list(content_rects)

    if caption is not None and include_caption:
        union_rects.append(caption.rect)

    if not union_rects:
        document.close()
        return None

    clip = _clip_from_rects(union_rects, page_rect=page.rect)
    result = (page_number, clip)
    document.close()

    return result


def resolve_figure_region(
    pdf_path: Path,
    *,
    page: int | None,
    figure_number: int | None = None,
    xref: int | None = None,
    clip: tuple[float, float, float, float] | None = None,
    include_caption: bool = True,
) -> tuple[int, tuple[float, float, float, float]]:
    """Resolve page number and clip rectangle for figure rendering.

    Args:
        pdf_path: Path to the PDF file.
        page: Optional 1-based page hint from the summary spec.
        figure_number: Optional caption number such as ``4``.
        xref: Optional embedded image xref.
        clip: Optional explicit clip rectangle.
        include_caption: When True, include the caption in auto-detected clips.

    Returns:
        ``(page, clip)`` tuple for :func:`render_page_region`.

    Raises:
        ValueError: If no clip can be determined.
    """
    if clip is not None:
        if page is None:
            raise ValueError("page is required when clip is provided")

        return page, clip

    if figure_number is not None:
        if page is None:
            raise ValueError("page is required when figure_number is provided")

        resolved_clip = figure_clip(
            pdf_path,
            page=page,
            figure_number=figure_number,
            include_caption=include_caption,
        )

        return page, resolved_clip

    if xref is not None:
        resolved = figure_clip_for_xref(
            pdf_path,
            xref,
            include_caption=include_caption,
        )
        if resolved is None:
            raise ValueError(f"Could not resolve figure region for xref {xref}")

        resolved_page, resolved_clip = resolved

        return resolved_page, resolved_clip

    raise ValueError("figure_number, xref, or clip is required to detect a figure clip")


def figure_clip(
    pdf_path: Path,
    *,
    page: int,
    figure_number: int | None = None,
    xref: int | None = None,
    include_caption: bool = True,
) -> tuple[float, float, float, float]:
    """Resolve a figure clip from a page and figure number or xref.

    Args:
        pdf_path: Path to the PDF file.
        page: 1-based page number from the summary spec.
        figure_number: Optional caption number such as ``4``.
        xref: Optional embedded image xref.
        include_caption: When True, include the caption in the clip.

    Returns:
        ``(x0, y0, x1, y1)`` clip rectangle.

    Raises:
        ValueError: If no clip can be determined.
    """
    if figure_number is not None:
        document = fitz.open(pdf_path)
        page_index = page - 1
        if page_index < 0 or page_index >= document.page_count:
            document.close()
            raise ValueError(f"Page {page} out of range (1-{document.page_count})")

        pdf_page = document[page_index]
        clip = figure_clip_on_page(
            pdf_page,
            figure_number,
            include_caption=include_caption,
        )
        document.close()

        if clip is None:
            raise ValueError(
                f"Figure {figure_number} not found on page {page} of {pdf_path.name}",
            )

        return clip

    if xref is not None:
        resolved = figure_clip_for_xref(
            pdf_path,
            xref,
            include_caption=include_caption,
        )
        if resolved is None:
            raise ValueError(f"Could not resolve figure region for xref {xref}")

        _resolved_page, clip = resolved

        return clip

    raise ValueError("figure_number or xref is required to detect a figure clip")


def list_figure_regions(pdf_path: Path) -> list[FigureRegion]:
    """List numbered figure regions detected from captions in a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Detected figure regions with page, number, and clip rectangle.
    """
    document = fitz.open(pdf_path)
    regions: list[FigureRegion] = []

    for page_index in range(document.page_count):
        page = document[page_index]
        page_number = page_index + 1
        captions = find_figure_captions(page, page_number=page_number)

        for caption in captions:
            clip = figure_clip_on_page(
                page,
                caption.number,
                include_caption=True,
            )
            if clip is None:
                continue

            region = FigureRegion(
                page=page_number,
                number=caption.number,
                clip=clip,
                caption=caption.text,
            )
            regions.append(region)

    document.close()

    return regions
