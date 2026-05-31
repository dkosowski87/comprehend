"""Summary schema and markdown assembly."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class VisualType(str, Enum):
    """Supported visual generation strategies."""

    EXTRACT = "extract"
    MERMAID = "mermaid"
    MANIM = "manim"


class MathEntry(BaseModel):
    """A labeled LaTeX equation block."""

    id: str
    label: str
    latex: str


class VisualSpec(BaseModel):
    """Specification for one summary visual."""

    id: str
    caption: str
    type: VisualType
    description: str
    refs: list[str] = Field(default_factory=list)
    page: int | None = None
    xref: int | None = None
    clip: tuple[float, float, float, float] | None = None
    mermaid_source: str | None = None
    manim_scene_path: str | None = None
    manim_scene_class: str | None = None
    asset_filename: str | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value:
            raise ValueError("Visual id must not be empty")

        return value


class PaperSummary(BaseModel):
    """Structured paper summary before and after visual rendering."""

    title: str
    pdf_url: str
    tags: list[str] = Field(default_factory=list)
    slug: str
    problem: list[str]
    solution: list[str]
    key_concepts: list[str]
    math: list[MathEntry] = Field(default_factory=list)
    visuals: list[VisualSpec] = Field(default_factory=list)

    @field_validator("visuals")
    @classmethod
    def validate_visual_count(cls, value: list[VisualSpec]) -> list[VisualSpec]:
        if len(value) > 2:
            raise ValueError("At most 2 visuals are allowed per summary")

        return value


def default_asset_filename(slug: str, visual_id: str) -> str:
    """Build a wiki asset filename for a visual id.

    Args:
        slug: Wiki page slug.
        visual_id: Visual identifier such as ``5a``.

    Returns:
        Asset filename relative to the wiki ``assets/`` directory.
    """
    safe_visual_id = visual_id.replace("/", "-")

    return f"{slug}-{safe_visual_id}.png"


def render_markdown(summary: PaperSummary) -> str:
    """Assemble wiki markdown from a summary model.

    Args:
        summary: Completed summary including rendered asset filenames.

    Returns:
        GitHub wiki markdown string.
    """
    tag_line = ", ".join(f"`{tag}`" for tag in summary.tags)
    lines: list[str] = [
        f"# {summary.title}",
        "",
        f"**PDF:** [{summary.pdf_url}]({summary.pdf_url})  ",
        f"**Tags:** {tag_line}" if tag_line else "**Tags:**",
        "",
        "## 1. Problem",
        "",
    ]

    for item in summary.problem:
        lines.append(f"- {item}")

    lines.extend(["", "## 2. Solution", ""])
    for item in summary.solution:
        lines.append(f"- {item}")

    lines.extend(["", "## 3. Key concepts", ""])
    for item in summary.key_concepts:
        lines.append(f"- {item}")

    if summary.math:
        lines.extend(["", "## 4. Math", ""])
        for entry in summary.math:
            lines.extend(
                [
                    f"**{entry.id}** {entry.label}:",
                    "",
                    f"$${entry.latex}$$",
                    "",
                ],
            )

    if summary.visuals:
        lines.extend(["", "## 5. Visualisation", ""])
        for visual in summary.visuals:
            asset_name = visual.asset_filename or default_asset_filename(
                summary.slug,
                visual.id,
            )
            lines.extend(
                [
                    f"### {visual.id} — {visual.caption}",
                    "",
                    f"![{visual.id}](assets/{asset_name})",
                    "",
                ],
            )

    markdown = "\n".join(lines).rstrip() + "\n"

    return markdown


def load_summary(path: Path) -> PaperSummary:
    """Load a summary JSON file.

    Args:
        path: Path to JSON file.

    Returns:
        Parsed summary model.
    """
    summary = PaperSummary.model_validate_json(path.read_text(encoding="utf-8"))

    return summary


def save_summary(summary: PaperSummary, path: Path) -> Path:
    """Write a summary model to JSON.

    Args:
        summary: Summary to serialize.
        path: Destination JSON path.

    Returns:
        Written path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    json_text = summary.model_dump_json(indent=2)
    path.write_text(json_text + "\n", encoding="utf-8")

    return path
