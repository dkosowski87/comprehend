"""Render extracted PDF figures to PNG."""

from __future__ import annotations

from pathlib import Path

from comprehend.pdf.extract import extract_figure_by_xref, render_page_region
from comprehend.summary.schema import VisualSpec, default_asset_filename


class FigureRenderError(Exception):
    """Raised when a PDF figure cannot be rendered."""


def render_extracted_figure(
    pdf_path: Path,
    visual: VisualSpec,
    *,
    slug: str,
    output_dir: Path,
) -> Path:
    """Render an extract-type visual from a PDF.

    Args:
        pdf_path: Source PDF path.
        visual: Visual specification with ``page``, optional ``xref`` or ``clip``.
        slug: Wiki slug for asset naming.
        output_dir: Directory for output PNG files.

    Returns:
        Path to the rendered PNG.

    Raises:
        FigureRenderError: If required fields are missing or rendering fails.
    """
    if visual.page is None:
        raise FigureRenderError(
            f"Visual {visual.id} requires 'page' for extract rendering",
        )

    asset_name = visual.asset_filename or default_asset_filename(slug, visual.id)
    output_path = output_dir / asset_name

    if visual.xref is not None:
        rendered_path = extract_figure_by_xref(
            pdf_path,
            visual.xref,
            output_path=output_path,
        )

        return rendered_path

    try:
        rendered_path = render_page_region(
            pdf_path,
            page=visual.page,
            output_path=output_path,
            clip=visual.clip,
        )
    except ValueError as exc:
        raise FigureRenderError(str(exc)) from exc

    return rendered_path
