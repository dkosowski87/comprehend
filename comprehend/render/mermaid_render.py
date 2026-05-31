"""Render Mermaid diagrams to PNG."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class MermaidRenderError(Exception):
    """Raised when Mermaid rendering fails."""


def mermaid_cli_available() -> bool:
    """Return whether the ``mmdc`` CLI is on PATH."""
    return shutil.which("mmdc") is not None


def render_mermaid(
    source: str,
    *,
    output_path: Path,
    theme: str = "dark",
) -> Path:
    """Render Mermaid source to PNG via ``@mermaid-js/mermaid-cli``.

    Args:
        source: Mermaid diagram source.
        output_path: Destination PNG path.
        theme: Mermaid theme passed to ``mmdc``.

    Returns:
        Path to the rendered PNG.

    Raises:
        MermaidRenderError: If ``mmdc`` is missing or rendering fails.
    """
    if not mermaid_cli_available():
        raise MermaidRenderError(
            "mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "diagram.mmd"
        input_path.write_text(source, encoding="utf-8")

        command = [
            "mmdc",
            "-i",
            str(input_path),
            "-o",
            str(output_path),
            "-b",
            "transparent",
            "-t",
            theme,
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
            raise MermaidRenderError(f"mmdc failed: {stderr}") from exc

    if not output_path.exists():
        raise MermaidRenderError(f"Mermaid output not created: {output_path}")

    return output_path
