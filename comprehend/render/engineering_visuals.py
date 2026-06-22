"""Visual rendering for engineering summaries."""

from __future__ import annotations

from pathlib import Path

from comprehend.engineering.schema import EngineeringSummary
from comprehend.render.visuals import VisualRenderError, render_visual


def render_engineering_visuals(
    summary: EngineeringSummary,
    *,
    output_dir: Path,
) -> dict[str, Path]:
    """Render all visuals for an engineering summary.

    Args:
        summary: Summary with visual specifications.
        output_dir: Directory for PNG assets.

    Returns:
        Mapping of visual id to rendered PNG path.

    Raises:
        VisualRenderError: If any visual fails to render.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered: dict[str, Path] = {}

    for visual in summary.visuals:
        rendered_path = render_visual(
            visual,
            slug=summary.slug,
            output_dir=output_dir,
            pdf_path=None,
        )
        visual.asset_filename = rendered_path.name
        rendered[visual.id] = rendered_path

    return rendered
