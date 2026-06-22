"""Engineering summary schema and markdown assembly."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from comprehend.engineering.tags import validate_engineering_tags, validate_engineering_topic
from comprehend.summary.schema import (
    VisualSpec,
    VisualType,
    _anchor,
    _format_summary_bullet,
    default_asset_filename,
)


class CodeExample(BaseModel):
    """A short code snippet illustrating tool usage."""

    id: str
    title: str
    language: str
    code: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value:
            raise ValueError("Code example id must not be empty")

        return value


class EngineeringSummary(BaseModel):
    """Structured engineering documentation summary."""

    title: str
    source_url: str
    topic: str
    tags: list[str] = Field(default_factory=list)
    slug: str
    keywords: list[str] = Field(default_factory=list)
    problem: list[str]
    solution: list[str]
    key_concepts: list[str]
    code_examples: list[CodeExample] = Field(default_factory=list)
    visuals: list[VisualSpec] = Field(default_factory=list)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        validated = validate_engineering_topic(value)

        return validated

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        validated = validate_engineering_tags(value)

        return validated

    @field_validator("code_examples")
    @classmethod
    def validate_code_examples(cls, value: list[CodeExample]) -> list[CodeExample]:
        if len(value) > 2:
            raise ValueError("At most 2 code examples are allowed")

        return value

    @field_validator("visuals")
    @classmethod
    def validate_visuals(cls, value: list[VisualSpec]) -> list[VisualSpec]:
        if len(value) > 2:
            raise ValueError("At most 2 visuals are allowed")

        for visual in value:
            if visual.type == VisualType.EXTRACT:
                raise ValueError(
                    f"Visual {visual.id}: extract visuals are not supported for engineering summaries",
                )

        return value


def collect_engineering_ref_ids(summary: EngineeringSummary) -> set[str]:
    """Collect cross-reference ids from code examples and visuals.

    Args:
        summary: Engineering summary model.

    Returns:
        Set of ids such as ``3a`` or ``4a`` that can be link targets.
    """
    ref_ids = {example.id for example in summary.code_examples}
    ref_ids.update(visual.id for visual in summary.visuals)

    return ref_ids


def render_markdown(summary: EngineeringSummary) -> str:
    """Assemble wiki markdown from an engineering summary model.

    Args:
        summary: Completed summary including rendered asset filenames.

    Returns:
        GitHub wiki markdown string.
    """
    ref_ids = collect_engineering_ref_ids(summary)
    tag_line = ", ".join(f"`{tag}`" for tag in summary.tags)
    lines: list[str] = [
        f"# {summary.title}",
        "",
        f"**Source:** [{summary.source_url}]({summary.source_url})  ",
        f"**Topic:** `{summary.topic}`  ",
        f"**Tags:** {tag_line}" if tag_line else "**Tags:**",
        "",
        "## 1. Problem",
        "",
    ]

    for item in summary.problem:
        lines.append(
            f"- {_format_summary_bullet(item, ref_ids=ref_ids, keywords=summary.keywords)}",
        )

    lines.extend(["", "## 2. Solution", ""])
    for item in summary.solution:
        lines.append(
            f"- {_format_summary_bullet(item, ref_ids=ref_ids, keywords=summary.keywords)}",
        )

    lines.extend(["", "## 3. Key concepts", ""])
    for item in summary.key_concepts:
        lines.append(
            f"- {_format_summary_bullet(item, ref_ids=ref_ids, keywords=summary.keywords)}",
        )

    if summary.code_examples:
        lines.extend(["", "## 4. Code examples", ""])
        for example in summary.code_examples:
            lines.extend(
                [
                    _anchor(example.id),
                    "",
                    f"**{example.id}** {example.title}:",
                    "",
                    f"```{example.language}",
                    example.code.rstrip(),
                    "```",
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
                    _anchor(visual.id),
                    "",
                    f"### {visual.id} — {visual.caption}",
                    "",
                    f"![{visual.id}](assets/{asset_name})",
                    "",
                ],
            )

    markdown = "\n".join(lines).rstrip() + "\n"

    return markdown


def load_engineering_summary(path: Path) -> EngineeringSummary:
    """Load an engineering summary JSON file.

    Args:
        path: Path to JSON file.

    Returns:
        Parsed engineering summary model.
    """
    summary = EngineeringSummary.model_validate_json(path.read_text(encoding="utf-8"))

    return summary


def save_engineering_summary(summary: EngineeringSummary, path: Path) -> Path:
    """Write an engineering summary model to JSON.

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
