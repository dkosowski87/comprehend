"""Tests for concept bibliography matching."""

from comprehend.concept.references import (
    extract_references_section,
    find_concept_reference_matches,
    split_reference_entries,
)


def test_extract_and_match_concept_in_references() -> None:
    text = """
Introduction
We use PANet-style fusion [12].

References
[12] S Liu et al. Path Aggregation Network for Instance Segmentation. arXiv:1803.00897.
[13] Other paper about trees.
"""
    section = extract_references_section(text)

    assert section is not None
    entries = split_reference_entries(section)
    matches = find_concept_reference_matches(
        entries,
        terms=["PANet", "path aggregation"],
        concept_id="panet",
    )

    assert len(matches) >= 1
    assert matches[0].entry.arxiv_id == "1803.00897"
    assert "path aggregation" in matches[0].matched_term.lower()


def test_simple_concept_has_no_reference_match() -> None:
    text = """
We apply cyclic shift on the grid.

References
[1] Some unrelated survey on databases.
"""
    section = extract_references_section(text)
    assert section is not None
    entries = split_reference_entries(section)
    matches = find_concept_reference_matches(
        entries,
        terms=["cyclic shift"],
        concept_id="cyclic_shift",
    )

    assert matches == []
