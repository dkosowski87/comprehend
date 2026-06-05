"""Tests for PDF extraction utilities."""

from pathlib import Path

import fitz

from comprehend.pdf.extract import extract_figure_by_xref, list_figures


def test_extract_figure_by_xref_writes_png(tmp_path: Path) -> None:
    source_pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120, 120), False)
    source_pixmap.clear_with(255)
    jpeg_bytes = source_pixmap.tobytes("jpg")

    pdf_path = tmp_path / "paper.pdf"
    document = fitz.open()
    page = document.new_page(width=120, height=120)
    page.insert_image(fitz.Rect(0, 0, 120, 120), stream=jpeg_bytes)
    document.save(pdf_path)
    document.close()

    figure = list_figures(pdf_path)[0]
    output_path = tmp_path / "figure.png"

    rendered_path = extract_figure_by_xref(
        pdf_path,
        figure.xref,
        output_path=output_path,
    )

    assert rendered_path == output_path
    assert output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
