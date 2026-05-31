"""Tests for summary schema and utilities."""

from pathlib import Path

import pytest

from comprehend.summary.schema import MathEntry, PaperSummary, VisualSpec, VisualType, render_markdown
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


def test_visual_count_limit() -> None:
    visuals = [
        VisualSpec(
            id=f"5{x}",
            caption="c",
            type=VisualType.EXTRACT,
            description="d",
            page=1,
        )
        for x in "abc"
    ]

    with pytest.raises(ValueError, match="At most 2 visuals"):
        PaperSummary(
            title="T",
            pdf_url="https://example.com/paper.pdf",
            tags=[],
            slug="test",
            problem=["p"],
            solution=["s"],
            key_concepts=["k"],
            visuals=visuals,
        )


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
