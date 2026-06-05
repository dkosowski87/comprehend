"""Render extracted PDF figures to PNG."""

from __future__ import annotations

from pathlib import Path

from comprehend.pdf.extract import render_page_region
from comprehend.pdf.figures import resolve_figure_region
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
        visual: Visual specification with ``page`` and ``figure_number``,
            ``xref``, or ``clip``.
        slug: Wiki slug for asset naming.
        output_dir: Directory for output PNG files.

    Returns:
        Path to the rendered PNG.

    Raises:
        FigureRenderError: If required fields are missing or rendering fails.
    """
    if visual.page is None and visual.xref is None and visual.clip is None:
        raise FigureRenderError(
            f"Visual {visual.id} requires 'page' for extract rendering",
        )

    asset_name = visual.asset_filename or default_asset_filename(slug, visual.id)
    output_path = output_dir / asset_name

    try:
        page, clip = resolve_figure_region(
            pdf_path,
            page=visual.page,
            figure_number=visual.figure_number,
            xref=visual.xref,
            clip=visual.clip,
        )

        rendered_path = render_page_region(
            pdf_path,
            page=page,
            output_path=output_path,
            clip=clip,
        )
    except ValueError as exc:
        raise FigureRenderError(str(exc)) from exc

    return rendered_path
