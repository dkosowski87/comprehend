"""Visual rendering orchestration."""

from __future__ import annotations

from pathlib import Path

from comprehend.render.extract_figure import FigureRenderError, render_extracted_figure
from comprehend.render.manim_render import ManimRenderError, render_manim_scene
from comprehend.render.mermaid_render import MermaidRenderError, render_mermaid
from comprehend.summary.schema import (
    PaperSummary,
    VisualSpec,
    VisualType,
    default_asset_filename,
)


class VisualRenderError(Exception):
    """Raised when any visual cannot be rendered."""


def render_visual(
    visual: VisualSpec,
    *,
    slug: str,
    output_dir: Path,
    pdf_path: Path | None = None,
) -> Path:
    """Render a single visual specification to PNG.

    Args:
        visual: Visual specification.
        slug: Wiki slug for asset naming.
        output_dir: Output directory for PNG files.
        pdf_path: Required for ``extract`` visuals.

    Returns:
        Path to rendered PNG.

    Raises:
        VisualRenderError: If rendering fails or required inputs are missing.
    """
    asset_name = visual.asset_filename or default_asset_filename(slug, visual.id)
    output_path = output_dir / asset_name

    try:
        if visual.type == VisualType.EXTRACT:
            if pdf_path is None:
                raise VisualRenderError(
                    f"Visual {visual.id} requires pdf_path for extract rendering",
                )

            rendered_path = render_extracted_figure(
                pdf_path,
                visual,
                slug=slug,
                output_dir=output_dir,
            )

            return rendered_path

        if visual.type == VisualType.MERMAID:
            if not visual.mermaid_source:
                raise VisualRenderError(
                    f"Visual {visual.id} requires mermaid_source",
                )

            rendered_path = render_mermaid(
                visual.mermaid_source,
                output_path=output_path,
            )

            return rendered_path

        if visual.type == VisualType.MANIM:
            if not visual.manim_scene_path:
                raise VisualRenderError(
                    f"Visual {visual.id} requires manim_scene_path",
                )
            if not visual.manim_scene_class:
                raise VisualRenderError(
                    f"Visual {visual.id} requires manim_scene_class",
                )

            scene_path = Path(visual.manim_scene_path)
            rendered_path = render_manim_scene(
                scene_path,
                scene_name=visual.manim_scene_class,
                output_path=output_path,
            )

            return rendered_path

    except (FigureRenderError, MermaidRenderError, ManimRenderError) as exc:
        raise VisualRenderError(str(exc)) from exc

    raise VisualRenderError(f"Unsupported visual type: {visual.type}")


def render_summary_visuals(
    summary: PaperSummary,
    *,
    output_dir: Path,
    pdf_path: Path | None = None,
) -> dict[str, Path]:
    """Render all visuals for a summary.

    Args:
        summary: Summary with visual specifications.
        output_dir: Directory for PNG assets.
        pdf_path: Source PDF for extract visuals.

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
            pdf_path=pdf_path,
        )
        visual.asset_filename = rendered_path.name
        rendered[visual.id] = rendered_path

    return rendered
