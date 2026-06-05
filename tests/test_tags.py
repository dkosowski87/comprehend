"""Tests for summary topic tags."""

import pytest

from comprehend.summary.schema import PaperSummary
from comprehend.summary.tags import MAX_PAPER_TAGS, validate_paper_tags


def test_validate_paper_tags_accepts_allowed_values() -> None:
    tags = validate_paper_tags(["transformers", "object-detection"])

    assert tags == ["transformers", "object-detection"]


def test_validate_paper_tags_rejects_unknown_tag() -> None:
    with pytest.raises(ValueError, match="Unknown tag"):
        validate_paper_tags(["not-a-real-tag"])


def test_validate_paper_tags_enforces_max_count() -> None:
    too_many = [
        "vision",
        "transformers",
        "object-detection",
        "contrastive-learning",
        "neural-rendering",
        "distillation",
    ]

    with pytest.raises(ValueError, match=str(MAX_PAPER_TAGS)):
        validate_paper_tags(too_many)


def test_paper_summary_validates_tags_on_load() -> None:
    with pytest.raises(ValueError, match="Unknown tag"):
        PaperSummary(
            title="T",
            pdf_url="https://example.com/paper.pdf",
            tags=["made-up-tag"],
            slug="test",
            problem=["p"],
            solution=["s"],
            key_concepts=["k"],
        )
