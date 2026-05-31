"""Render package exports."""

from comprehend.render.extract_figure import FigureRenderError, render_extracted_figure
from comprehend.render.manim_render import ManimRenderError, manim_available, render_manim_scene
from comprehend.render.mermaid_render import MermaidRenderError, mermaid_cli_available, render_mermaid
from comprehend.render.visuals import VisualRenderError, render_summary_visuals, render_visual

__all__ = [
    "FigureRenderError",
    "ManimRenderError",
    "MermaidRenderError",
    "VisualRenderError",
    "manim_available",
    "mermaid_cli_available",
    "render_extracted_figure",
    "render_manim_scene",
    "render_mermaid",
    "render_summary_visuals",
    "render_visual",
]
