"""PDF text and figure extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True)
class FigureInfo:
    """Metadata for an embedded PDF image."""

    page: int
    index: int
    width: int
    height: int
    xref: int


@dataclass(frozen=True)
class ExtractedPaper:
    """Structured extraction output for a paper PDF."""

    text: str
    text_path: Path
    figures: list[FigureInfo]
    page_count: int


def extract_text(pdf_path: Path) -> str:
    """Extract full text from a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Concatenated page text separated by blank lines.
    """
    document = fitz.open(pdf_path)
    pages: list[str] = []
    for page in document:
        pages.append(page.get_text())

    document.close()
    full_text = "\n\n".join(pages)

    return full_text


def list_figures(pdf_path: Path) -> list[FigureInfo]:
    """List embedded images in a PDF above a minimum size.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of figure metadata sorted by page and index.
    """
    document = fitz.open(pdf_path)
    figures: list[FigureInfo] = []
    min_size = 100

    for page_number in range(document.page_count):
        page = document[page_number]
        for image_index, image in enumerate(page.get_images(full=True)):
            xref = image[0]
            width = image[2]
            height = image[3]
            if width < min_size or height < min_size:
                continue

            figure = FigureInfo(
                page=page_number + 1,
                index=image_index,
                width=width,
                height=height,
                xref=xref,
            )
            figures.append(figure)

    document.close()

    return figures


def extract_figure_by_xref(
    pdf_path: Path,
    xref: int,
    *,
    output_path: Path,
) -> Path:
    """Extract a single embedded image by xref.

    Args:
        pdf_path: Path to the PDF file.
        xref: Image xref from :func:`list_figures`.
        output_path: Destination PNG path.

    Returns:
        Path to the written image file.
    """
    document = fitz.open(pdf_path)
    try:
        pixmap = fitz.Pixmap(document, xref)
        if pixmap.n - pixmap.alpha > 3:
            pixmap = fitz.Pixmap(fitz.csRGB, pixmap)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(output_path)
    finally:
        document.close()

    return output_path


def render_page_region(
    pdf_path: Path,
    *,
    page: int,
    output_path: Path,
    clip: tuple[float, float, float, float] | None = None,
    zoom: float = 2.0,
) -> Path:
    """Render a PDF page or clipped region to PNG.

    Args:
        pdf_path: Path to the PDF file.
        page: 1-based page number.
        output_path: Destination PNG path.
        clip: Optional ``(x0, y0, x1, y1)`` clip rectangle in PDF coordinates.
        zoom: Render zoom factor for resolution.

    Returns:
        Path to the rendered PNG file.
    """
    document = fitz.open(pdf_path)
    page_index = page - 1
    if page_index < 0 or page_index >= document.page_count:
        document.close()
        raise ValueError(f"Page {page} out of range (1-{document.page_count})")

    pdf_page = document[page_index]
    matrix = fitz.Matrix(zoom, zoom)
    if clip is not None:
        clip_rect = fitz.Rect(clip)
        pixmap = pdf_page.get_pixmap(matrix=matrix, clip=clip_rect)
    else:
        pixmap = pdf_page.get_pixmap(matrix=matrix)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(output_path)
    document.close()

    return output_path


def extract_paper(
    pdf_path: Path,
    *,
    output_dir: Path,
) -> ExtractedPaper:
    """Extract text and figure catalog from a PDF into ``output_dir``.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory for ``text.txt`` and future assets.

    Returns:
        Structured extraction result.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    text = extract_text(pdf_path)
    text_path = output_dir / "text.txt"
    text_path.write_text(text, encoding="utf-8")

    document = fitz.open(pdf_path)
    page_count = document.page_count
    document.close()

    figures = list_figures(pdf_path)
    extracted = ExtractedPaper(
        text=text,
        text_path=text_path,
        figures=figures,
        page_count=page_count,
    )

    return extracted
