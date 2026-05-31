"""Concept summary schema and markdown assembly."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from comprehend.summary.schema import VisualSpec, default_asset_filename


class RelatedPaper(BaseModel):
    """Link from a concept page back to a paper summary."""

    slug: str
    title: str


class ConceptSummary(BaseModel):
    """Structured concept explanation before and after visual rendering."""

    name: str
    concept_id: str
    slug: str
    related_papers: list[RelatedPaper]
    what_it_is: list[str]
    how_it_works: list[str]
    tags: list[str] = Field(default_factory=list)
    visuals: list[VisualSpec] = Field(default_factory=list)

    @field_validator("visuals")
    @classmethod
    def validate_visual_count(cls, value: list[VisualSpec]) -> list[VisualSpec]:
        if len(value) > 1:
            raise ValueError("At most 1 visual is allowed per concept")

        return value


def render_concept_markdown(summary: ConceptSummary) -> str:
    """Assemble wiki markdown for a concept page.

    Args:
        summary: Completed concept summary including rendered asset filenames.

    Returns:
        GitHub wiki markdown string.
    """
    related_links = ", ".join(
        f"[{paper.title}]({paper.slug})" for paper in summary.related_papers
    )
    tag_line = ", ".join(f"`{tag}`" for tag in summary.tags)

    lines: list[str] = [
        f"# {summary.name}",
        "",
        f"**Related papers:** {related_links}  ",
    ]

    if tag_line:
        lines.append(f"**Tags:** {tag_line}  ")

    lines.extend(["", "## What it is", ""])
    for item in summary.what_it_is:
        lines.append(f"- {item}")

    lines.extend(["", "## How it works", ""])
    for item in summary.how_it_works:
        lines.append(f"- {item}")

    if summary.visuals:
        lines.extend(["", "## Visualisation", ""])
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


def load_concept_summary(path: Path) -> ConceptSummary:
    """Load a concept JSON file.

    Args:
        path: Path to JSON file.

    Returns:
        Parsed concept model.
    """
    summary = ConceptSummary.model_validate_json(path.read_text(encoding="utf-8"))

    return summary


def save_concept_summary(summary: ConceptSummary, path: Path) -> Path:
    """Write a concept model to JSON.

    Args:
        summary: Concept to serialize.
        path: Destination JSON path.

    Returns:
        Written path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    json_text = summary.model_dump_json(indent=2)
    path.write_text(json_text + "\n", encoding="utf-8")

    return path
