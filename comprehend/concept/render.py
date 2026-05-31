"""Concept visual rendering."""

from __future__ import annotations

from pathlib import Path

from comprehend.concept.schema import ConceptSummary
from comprehend.render.visuals import VisualRenderError, render_visual


def render_concept_visuals(
    summary: ConceptSummary,
    *,
    output_dir: Path,
    pdf_path: Path | None = None,
) -> dict[str, Path]:
    """Render all visuals for a concept summary.

    Args:
        summary: Concept with visual specifications.
        output_dir: Directory for PNG assets.
        pdf_path: Optional source PDF for extract visuals.

    Returns:
        Mapping of visual id to rendered PNG path.

    Raises:
        VisualRenderError: If rendering fails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered: dict[str, Path] = {}

    for visual in summary.visuals:
        rendered_path = render_visual(
            visual,
            slug=summary.slug,
            output_dir=output_dir,
            pdf_path=pdf_path,
        )
        visual.asset_filename = rendered_path.name
        rendered[visual.id] = rendered_path

    return rendered
