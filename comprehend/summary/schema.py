"""Summary schema and markdown assembly."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from comprehend.summary.tags import validate_paper_tags


class VisualType(str, Enum):
    """Supported visual generation strategies."""

    EXTRACT = "extract"
    MERMAID = "mermaid"
    MANIM = "manim"


class MathVariable(BaseModel):
    """Definition of one symbol used in a math entry."""

    symbol: str
    meaning: str


class MathEntry(BaseModel):
    """A labeled LaTeX equation block."""

    id: str
    label: str
    latex: str
    variables: list[MathVariable] = Field(default_factory=list)


class VisualSpec(BaseModel):
    """Specification for one summary visual."""

    id: str
    caption: str
    type: VisualType
    description: str
    refs: list[str] = Field(default_factory=list)
    page: int | None = None
    figure_number: int | None = None
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
    keywords: list[str] = Field(default_factory=list)
    problem: list[str]
    solution: list[str]
    key_concepts: list[str]
    math: list[MathEntry] = Field(default_factory=list)
    visuals: list[VisualSpec] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        validated = validate_paper_tags(value)

        return validated


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


def collect_ref_ids(summary: PaperSummary) -> set[str]:
    """Collect cross-reference ids from math and visual sections.

    Args:
        summary: Paper summary model.

    Returns:
        Set of ids such as ``4a`` or ``5a`` that can be link targets.
    """
    ref_ids = {entry.id for entry in summary.math}
    ref_ids.update(visual.id for visual in summary.visuals)

    return ref_ids


def linkify_refs(text: str, ref_ids: set[str]) -> str:
    """Turn cross-reference markers in text into markdown jump links.

    Supports ``**4a**`` and ``(4a)`` forms when ``4a`` is a known target id.

    Args:
        text: Bullet or paragraph text from a summary section.
        ref_ids: Known anchor ids from :func:`collect_ref_ids`.

    Returns:
        Text with markdown links to in-page anchors.
    """
    if not ref_ids:
        return text

    linked = text
    for ref_id in sorted(ref_ids, key=len, reverse=True):
        escaped_id = re.escape(ref_id)
        bold_pattern = re.compile(rf"(?<!\[)\*\*{escaped_id}\*\*")
        linked = bold_pattern.sub(rf"[**{ref_id}**](#{ref_id})", linked)

        paren_pattern = re.compile(rf"(?<!\[)\({escaped_id}\)")
        linked = paren_pattern.sub(rf"[({ref_id})](#{ref_id})", linked)

    return linked


def emphasize_keywords(text: str, keywords: list[str]) -> str:
    """Wrap occurrences of paper-specific keywords in bold markdown.

    Skips text that is already bold. Longer keywords are emphasized first so
    phrases like ``cross-scale feature fusion`` win over shorter substrings.

    Args:
        text: Bullet text from a summary section.
        keywords: Terms to emphasize, such as method or module names.

    Returns:
        Text with newly bolded keyword occurrences.
    """
    unique_keywords = [keyword.strip() for keyword in keywords if keyword.strip()]
    if not unique_keywords:
        return text

    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    emphasized_parts: list[str] = []

    for index, part in enumerate(parts):
        if index % 2 == 1:
            emphasized_parts.append(part)
            continue

        emphasized = part
        for keyword in sorted(set(unique_keywords), key=len, reverse=True):
            escaped_keyword = re.escape(keyword)
            pattern = re.compile(rf"\b({escaped_keyword})\b", re.IGNORECASE)
            emphasized = pattern.sub(r"**\1**", emphasized)

        emphasized_parts.append(emphasized)

    emphasized_text = "".join(emphasized_parts)

    return emphasized_text


def _format_summary_bullet(
    text: str,
    *,
    ref_ids: set[str],
    keywords: list[str],
) -> str:
    linked = linkify_refs(emphasize_keywords(text, keywords), ref_ids)

    return linked


def _anchor(ref_id: str) -> str:
    return f'<a id="{ref_id}"></a>'


def _replace_braced_macro(latex: str, *, source: str, target: str) -> str:
    """Replace ``\\source{...}`` with ``\\target{...}``, including nested braces.

    Args:
        latex: Equation string that may contain the macro.
        source: Macro name to replace (without a leading backslash).
        target: Replacement macro name (without a leading backslash).

    Returns:
        Equation string with matching braced macro calls rewritten.
    """
    needle = f"\\{source}"
    result: list[str] = []
    index = 0

    while index < len(latex):
        start = latex.find(needle, index)
        if start == -1:
            result.append(latex[index:])
            break

        brace_start = start + len(needle)
        while brace_start < len(latex) and latex[brace_start].isspace():
            brace_start += 1

        if brace_start >= len(latex) or latex[brace_start] != "{":
            result.append(latex[index : start + len(needle)])
            index = start + len(needle)
            continue

        depth = 0
        position = brace_start
        while position < len(latex):
            character = latex[position]
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    break
            position += 1

        if depth != 0:
            result.append(latex[index:])
            break

        inner = latex[brace_start + 1 : position]
        result.append(latex[index:start])
        result.append(f"\\{target}{{{inner}}}")
        index = position + 1

    normalized = "".join(result)

    return normalized


def _brace_inner_superscripts(inner: str) -> str:
    """Brace ``^`` operators inside an existing superscript group.

    GitHub wiki math rejects forms like ``^{\\mathcal{S}^*}`` where the inner
    ``^*`` is not wrapped in braces.

    Args:
        inner: Superscript content (text inside the outer ``^{...}``).

    Returns:
        Superscript content with nested superscripts braced.
    """
    normalized = re.sub(r"\^\*", r"^{\\ast}", inner)
    normalized = re.sub(r"\^([^{])", r"^{\1}", normalized)

    return normalized


def _fix_nested_superscripts(latex: str) -> str:
    """Brace nested superscripts inside ``^{...}`` groups for wiki math parsers.

    Args:
        latex: Equation string that may contain nested superscripts.

    Returns:
        Equation string with nested superscripts braced.
    """
    result: list[str] = []
    index = 0

    while index < len(latex):
        caret = latex.find("^{", index)
        if caret == -1:
            result.append(latex[index:])
            break

        result.append(latex[index:caret])
        brace_start = caret + 1
        depth = 0
        position = brace_start
        while position < len(latex):
            character = latex[position]
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    break
            position += 1

        if depth != 0:
            result.append(latex[caret:])
            break

        inner = latex[brace_start + 1 : position]
        fixed_inner = _brace_inner_superscripts(inner)
        result.append(f"^{{{fixed_inner}}}")
        index = position + 1

    normalized = "".join(result)

    return normalized


def normalize_wiki_latex(latex: str) -> str:
    """Normalize LaTeX for GitHub wiki math rendering.

    GitHub wiki math can reject some macros (for example ``\\operatorname``,
    ``\\bm``) and nested superscripts (for example ``^{\\mathcal{S}^*}``).
    This rewrites ``\\bm`` to ``\\boldsymbol`` and other unsupported forms to
    compatible ones before emitting ``$$...$$`` blocks.

    Args:
        latex: Raw equation string from summary JSON.

    Returns:
        Equation string with wiki-compatible macros.
    """
    normalized = _replace_braced_macro(latex, source="operatorname", target="mathrm")
    normalized = _replace_braced_macro(normalized, source="bm", target="boldsymbol")
    normalized = _fix_nested_superscripts(normalized)

    return normalized


def render_math_entry_lines(entry: MathEntry) -> list[str]:
    """Build markdown lines for one math entry including an optional variable legend.

    Args:
        entry: Math entry with LaTeX and optional variable definitions.

    Returns:
        Markdown lines for the entry anchor, equation, and legend.
    """
    normalized_latex = normalize_wiki_latex(entry.latex)
    lines = [
        _anchor(entry.id),
        "",
        f"**{entry.id}** {entry.label}:",
        "",
        f"$${normalized_latex}$$",
    ]

    if entry.variables:
        lines.append("")
        lines.append("Where:")
        for variable in entry.variables:
            normalized_symbol = normalize_wiki_latex(variable.symbol)
            lines.append(f"- ${normalized_symbol}$ — {variable.meaning}")

    lines.append("")

    return lines


def render_markdown(summary: PaperSummary) -> str:
    """Assemble wiki markdown from a summary model.

    Cross-references such as ``**4a**`` or ``(5a)`` in section bullets become
    jump links when matching math or visual ids exist. Targets use HTML
    anchors compatible with GitHub wiki.

    Args:
        summary: Completed summary including rendered asset filenames.

    Returns:
        GitHub wiki markdown string.
    """
    ref_ids = collect_ref_ids(summary)
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
        lines.append(f"- {_format_summary_bullet(item, ref_ids=ref_ids, keywords=summary.keywords)}")

    lines.extend(["", "## 2. Solution", ""])
    for item in summary.solution:
        lines.append(f"- {_format_summary_bullet(item, ref_ids=ref_ids, keywords=summary.keywords)}")

    lines.extend(["", "## 3. Key concepts", ""])
    for item in summary.key_concepts:
        lines.append(f"- {_format_summary_bullet(item, ref_ids=ref_ids, keywords=summary.keywords)}")

    if summary.math:
        lines.extend(["", "## 4. Math", ""])
        for entry in summary.math:
            lines.extend(render_math_entry_lines(entry))

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
