"""Tests for concept explanations."""

from comprehend.concept.linkify import patch_first_concept_mention
from comprehend.concept.refs import parse_concept_ref
from comprehend.concept.schema import ConceptSummary, RelatedPaper, render_concept_markdown
from comprehend.util import concept_display_name, concept_wiki_slug


def test_parse_concept_ref_string() -> None:
    ref = parse_concept_ref("cyclic_shift")

    assert ref is not None
    assert ref.concept_id == "cyclic_shift"
    assert ref.terms == ["cyclic shift"]


def test_parse_concept_ref_with_terms() -> None:
    ref = parse_concept_ref(
        {
            "slug": "cyclic_shift",
            "terms": ["cyclic shift", "shifted window"],
        },
    )

    assert ref is not None
    assert ref.terms == ["cyclic shift", "shifted window"]


def test_concept_wiki_slug() -> None:
    slug = concept_wiki_slug("cyclic_shift")

    assert slug == "concept-cyclic-shift"


def test_concept_display_name() -> None:
    name = concept_display_name("cyclic_shift")

    assert name == "Cyclic shift"


def test_patch_first_concept_mention() -> None:
    markdown = "Swin uses cyclic shift across windows. Later cyclic shift again."

    patched, linked = patch_first_concept_mention(
        markdown,
        term="cyclic shift",
        concept_slug="concept-cyclic-shift",
    )

    assert linked is True
    assert patched.startswith("Swin uses [cyclic shift](concept-cyclic-shift)")
    assert "Later cyclic shift again." in patched


def test_render_concept_markdown_structure() -> None:
    summary = ConceptSummary(
        name="Cyclic shift",
        concept_id="cyclic_shift",
        slug="concept-cyclic-shift",
        related_papers=[
            RelatedPaper(slug="arxiv-2103-14030", title="Swin Transformer"),
        ],
        what_it_is=["Defines window movement on a grid."],
        how_it_works=["Shifts patch layout cyclically."],
        tags=["vision"],
    )

    markdown = render_concept_markdown(summary)

    assert "# Cyclic shift" in markdown
    assert "## What it is" in markdown
    assert "## How it works" in markdown
    assert "Swin Transformer" in markdown
    assert "Why it appears" not in markdown


def test_concept_visual_uses_caption_heading_not_paper_ids() -> None:
    from comprehend.summary.schema import VisualSpec, VisualType

    summary = ConceptSummary(
        name="Cyclic shift",
        concept_id="cyclic_shift",
        slug="concept-cyclic-shift",
        related_papers=[
            RelatedPaper(slug="arxiv-2103-14030", title="Swin Transformer"),
        ],
        what_it_is=["Defines window movement on a grid."],
        how_it_works=["Shifts patch layout cyclically."],
        visuals=[
            VisualSpec(
                id="5a",
                caption="Grid roll illustration",
                type=VisualType.MANIM,
                description="diagram",
                asset_filename="concept-cyclic-shift-visual.png",
            ),
        ],
    )

    markdown = render_concept_markdown(summary)

    assert "### Grid roll illustration" in markdown
    assert "### 5a" not in markdown
    assert summary.visuals[0].id == "visual"
