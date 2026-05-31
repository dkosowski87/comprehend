"""Render Manim scenes to static PNG frames."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class ManimRenderError(Exception):
    """Raised when Manim rendering fails."""


def manim_available() -> bool:
    """Return whether the ``manim`` CLI is on PATH."""
    return shutil.which("manim") is not None


def render_manim_scene(
    scene_path: Path,
    *,
    scene_name: str,
    output_path: Path,
    quality: str = "m",
) -> Path:
    """Render the last frame of a Manim scene to PNG.

    Uses ``manim render -s`` to save a static image instead of video.

    Args:
        scene_path: Python file containing the Manim scene class.
        scene_name: Scene class name to render.
        output_path: Destination PNG path.
        quality: Manim quality flag (``l``, ``m``, ``h``, etc.).

    Returns:
        Path to the rendered PNG.

    Raises:
        ManimRenderError: If Manim is missing or rendering fails.
    """
    if not manim_available():
        raise ManimRenderError(
            "manim not found. Install with: uv sync --extra manim",
        )

    if not scene_path.is_file():
        raise ManimRenderError(f"Scene file not found: {scene_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    media_dir = output_path.parent / "_manim_media"
    media_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "manim",
        "render",
        f"-q{quality}",
        "-s",
        "--media_dir",
        str(media_dir),
        str(scene_path),
        scene_name,
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown error"
        raise ManimRenderError(f"manim failed: {stderr}") from exc

    png_candidates = sorted(
        media_dir.rglob("*.png"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not png_candidates:
        raise ManimRenderError("manim produced no PNG output")

    latest_png = png_candidates[0]
    if latest_png.resolve() != output_path.resolve():
        output_path.write_bytes(latest_png.read_bytes())

    return output_path
