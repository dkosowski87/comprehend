"""Tests for concept explanations."""

from comprehend.concept.linkify import patch_first_concept_mention
from comprehend.concept.refs import parse_concept_ref
from comprehend.concept.schema import ConceptSummary, RelatedPaper, render_concept_markdown
from comprehend.summary.schema import MathEntry
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


def test_resolve_link_terms_prefers_explicit_terms() -> None:
    from comprehend.concept.refs import resolve_link_terms

    terms = resolve_link_terms(
        "cyclic_shift",
        terms=["shifted window"],
        keywords=["cyclic shift"],
    )

    assert terms == ["shifted window"]


def test_resolve_link_terms_falls_back_to_keywords() -> None:
    from comprehend.concept.refs import resolve_link_terms

    terms = resolve_link_terms("ccff", keywords=["cross-scale feature fusion", "CCFF"])

    assert terms == ["cross-scale feature fusion", "CCFF"]


def test_render_concept_markdown_structure() -> None:
    summary = ConceptSummary(
        name="Cyclic shift",
        concept_id="cyclic_shift",
        slug="concept-cyclic-shift",
        related_papers=[
            RelatedPaper(slug="arxiv-2103-14030", title="Swin Transformer"),
        ],
        what_it_is=["Rolls the feature grid before windowing."],
        how_it_works=["Uses cyclic shift to connect adjacent windows."],
        tags=["transformers", "representation-learning"],
        keywords=["cyclic shift", "shifted window"],
    )

    markdown = render_concept_markdown(summary)

    assert "# Cyclic shift" in markdown
    assert "## What it is" in markdown
    assert "## How it works" in markdown
    assert "Swin Transformer" in markdown
    assert "**cyclic shift**" in markdown
    assert "Why it appears" not in markdown


def test_render_concept_markdown_math_section_and_links() -> None:
    summary = ConceptSummary(
        name="Euler integration",
        concept_id="euler-integration",
        slug="concept-euler-integration",
        related_papers=[
            RelatedPaper(slug="arxiv-2410-24164", title="π₀"),
        ],
        what_it_is=["One step is **m1**."],
        how_it_works=["Initialize with **m2**."],
        math=[
            MathEntry(id="m1", label="update", latex="x \\leftarrow x + \\delta v"),
            MathEntry(id="m2", label="init", latex="x_0 \\sim \\mathcal{N}(0,I)"),
        ],
        tags=["robotics"],
    )

    markdown = render_concept_markdown(summary)

    assert "## Math" in markdown
    assert '<a id="m1"></a>' in markdown
    assert "$$x \\leftarrow x + \\delta v$$" in markdown
    assert "[**m1**](#m1)" in markdown
    assert "[**m2**](#m2)" in markdown
    assert "\\(" not in markdown


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


def test_render_concept_markdown_normalizes_operatorname_in_math() -> None:
    summary = ConceptSummary(
        name="IoU thresholding",
        concept_id="iou-thresholding",
        slug="concept-iou-thresholding",
        related_papers=[
            RelatedPaper(slug="arxiv-0000-00000", title="Test Paper"),
        ],
        what_it_is=[],
        how_it_works=[],
        math=[
            MathEntry(
                id="m1",
                label="threshold",
                latex=r"\operatorname{IoU}\left(\mathbf{1}[\ell>-1],\mathbf{1}[\ell>1]\right)\ge 0.95",
            ),
        ],
        visuals=[],
    )

    markdown = render_concept_markdown(summary)

    assert r"\operatorname{" not in markdown
    assert r"$$\mathrm{IoU}\left(\mathbf{1}[\ell>-1],\mathbf{1}[\ell>1]\right)\ge 0.95$$" in markdown
