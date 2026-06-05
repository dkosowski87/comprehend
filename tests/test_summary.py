"""Tests for summary schema and utilities."""

from pathlib import Path

import pytest

from comprehend.summary.schema import (
    MathEntry,
    MathVariable,
    PaperSummary,
    VisualSpec,
    VisualType,
    emphasize_keywords,
    linkify_refs,
    normalize_wiki_latex,
    render_markdown,
)
from comprehend.util import arxiv_slug, parse_arxiv_id, slugify


def test_parse_arxiv_abs_url() -> None:
    arxiv_id = parse_arxiv_id("https://arxiv.org/abs/2012.12877")

    assert arxiv_id == "2012.12877"


def test_arxiv_slug() -> None:
    slug = arxiv_slug("2012.12877")

    assert slug == "arxiv-2012-12877"


def test_slugify_title() -> None:
    slug = slugify("DeiT: Training data-efficient image transformers")

    assert slug.startswith("deit-training")


def test_many_visuals_allowed() -> None:
    visuals = [
        VisualSpec(
            id=f"5{x}",
            caption="c",
            type=VisualType.EXTRACT,
            description="d",
            page=1,
            figure_number=1,
        )
        for x in "abc"
    ]

    summary = PaperSummary(
        title="T",
        pdf_url="https://example.com/paper.pdf",
        tags=[],
        slug="test",
        problem=["p"],
        solution=["s"],
        key_concepts=["k"],
        visuals=visuals,
    )

    assert len(summary.visuals) == 3


def test_render_markdown_includes_variable_legend() -> None:
    summary = PaperSummary(
        title="Test Paper",
        pdf_url="https://arxiv.org/pdf/2012.12877.pdf",
        tags=[],
        slug="test",
        problem=[],
        solution=[],
        key_concepts=[],
        math=[
            MathEntry(
                id="4a",
                label="volume rendering",
                latex=r"C(\mathbf{r}) = \int T(t)\,\sigma(\mathbf{r}(t))\,dt",
                variables=[
                    MathVariable(
                        symbol=r"\mathbf{r}",
                        meaning="3D spatial location",
                    ),
                    MathVariable(
                        symbol=r"\sigma",
                        meaning="volume density along the ray",
                    ),
                    MathVariable(symbol="T(t)", meaning="accumulated transmittance"),
                ],
            ),
        ],
        visuals=[],
    )

    markdown = render_markdown(summary)

    assert "Where:" in markdown
    assert r"$\mathbf{r}$ — 3D spatial location" in markdown
    assert r"$\sigma$ — volume density along the ray" in markdown
    assert "$T(t)$ — accumulated transmittance" in markdown


def test_render_markdown_includes_sections(tmp_path: Path) -> None:
    summary = PaperSummary(
        title="Test Paper",
        pdf_url="https://arxiv.org/pdf/2012.12877.pdf",
        tags=["vision"],
        slug="arxiv-2012-12877",
        problem=["Problem one"],
        solution=["Solution one"],
        key_concepts=["Concept one"],
        math=[MathEntry(id="4a", label="loss", latex="L = 0")],
        visuals=[
            VisualSpec(
                id="5a",
                caption="Overview",
                type=VisualType.MERMAID,
                description="diagram",
                asset_filename="arxiv-2012-12877-5a.png",
            ),
        ],
    )

    markdown = render_markdown(summary)

    assert "# Test Paper" in markdown
    assert "## 3. Key concepts" in markdown
    assert "$$L = 0$$" in markdown
    assert "assets/arxiv-2012-12877-5a.png" in markdown
    assert '<a id="4a"></a>' in markdown
    assert '<a id="5a"></a>' in markdown


def test_emphasize_keywords_bolds_terms() -> None:
    text = "RT-DETR replaces NMS with an efficient hybrid encoder."

    emphasized = emphasize_keywords(text, ["RT-DETR", "hybrid encoder"])

    assert emphasized == "**RT-DETR** replaces NMS with an efficient **hybrid encoder**."


def test_emphasize_keywords_skips_existing_bold() -> None:
    text = "The **RT-DETR** decoder uses cross-attention."

    emphasized = emphasize_keywords(text, ["RT-DETR", "cross-attention"])

    assert emphasized == "The **RT-DETR** decoder uses **cross-attention**."


def test_render_markdown_emphasizes_keywords() -> None:
    summary = PaperSummary(
        title="Test Paper",
        pdf_url="https://arxiv.org/pdf/2012.12877.pdf",
        tags=[],
        slug="test",
        keywords=["distillation token"],
        problem=["DeiT introduces a distillation token for attention transfer."],
        solution=[],
        key_concepts=[],
        visuals=[],
    )

    markdown = render_markdown(summary)

    assert "**distillation token**" in markdown


def test_render_markdown_keywords_and_cross_refs() -> None:
    summary = PaperSummary(
        title="Test Paper",
        pdf_url="https://arxiv.org/pdf/2012.12877.pdf",
        tags=[],
        slug="test",
        keywords=["distillation token"],
        problem=[],
        solution=["The distillation token feeds loss **4a**."],
        key_concepts=[],
        math=[MathEntry(id="4a", label="loss", latex="L = 0")],
        visuals=[],
    )

    markdown = render_markdown(summary)

    assert "**distillation token**" in markdown
    assert "[**4a**](#4a)" in markdown


def test_linkify_refs_bold_and_parens() -> None:
    ref_ids = {"4a", "5a"}
    text = "See **5a** and soft distillation **4a**."

    linked = linkify_refs(text, ref_ids)

    assert linked == "See [**5a**](#5a) and soft distillation [**4a**](#4a)."

    paren_linked = linkify_refs("Details in (5a).", ref_ids)

    assert paren_linked == "Details in [(5a)](#5a)."


def test_render_markdown_linkifies_solution_refs() -> None:
    summary = PaperSummary(
        title="Test Paper",
        pdf_url="https://arxiv.org/pdf/2012.12877.pdf",
        tags=[],
        slug="test",
        problem=[],
        solution=["Use token (**5a**) with loss **4a**."],
        key_concepts=[],
        math=[MathEntry(id="4a", label="loss", latex="L = 0")],
        visuals=[
            VisualSpec(
                id="5a",
                caption="Overview",
                type=VisualType.EXTRACT,
                description="diagram",
                page=1,
            ),
        ],
    )

    markdown = render_markdown(summary)

    assert "[**4a**](#4a)" in markdown
    assert "[**5a**](#5a)" in markdown


def test_normalize_wiki_latex_rewrites_operatorname() -> None:
    latex = r"\operatorname{IoU}\left(\mathbf{1}[\ell>-1],\mathbf{1}[\ell>1]\right)\ge 0.95"

    normalized_latex = normalize_wiki_latex(latex)

    assert r"\operatorname{" not in normalized_latex
    assert r"\mathrm{IoU}" in normalized_latex


def test_render_markdown_normalizes_operatorname_in_math() -> None:
    summary = PaperSummary(
        title="Test Paper",
        pdf_url="https://arxiv.org/pdf/2012.12877.pdf",
        tags=[],
        slug="test",
        problem=[],
        solution=[],
        key_concepts=[],
        math=[
            MathEntry(
                id="4a",
                label="iou",
                latex=r"\operatorname{IoU}\left(\mathbf{1}[\ell>-1],\mathbf{1}[\ell>1]\right)\ge 0.95",
            ),
        ],
        visuals=[],
    )

    markdown = render_markdown(summary)

    assert r"\operatorname{" not in markdown
    assert r"$$\mathrm{IoU}\left(\mathbf{1}[\ell>-1],\mathbf{1}[\ell>1]\right)\ge 0.95$$" in markdown
