"""Concept reference parsing from papers.yaml."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptRef:
    """A concept declared for a paper in ``papers.yaml``."""

    concept_id: str
    terms: list[str]


def parse_concept_ref(raw: object) -> ConceptRef | None:
    """Parse one concept entry from YAML.

    Args:
        raw: YAML value — a string id or a mapping with ``slug`` and optional ``terms``.

    Returns:
        Parsed concept reference, or ``None`` when invalid.
    """
    if isinstance(raw, str):
        concept_id = raw.strip()
        if not concept_id:
            return None

        terms = [_default_term(concept_id)]

        return ConceptRef(concept_id=concept_id, terms=terms)

    if isinstance(raw, dict):
        slug_value = raw.get("slug")
        if not slug_value:
            return None

        concept_id = str(slug_value).strip()
        raw_terms = raw.get("terms", [])
        if isinstance(raw_terms, list) and raw_terms:
            terms = [str(term) for term in raw_terms]
        else:
            terms = [_default_term(concept_id)]

        return ConceptRef(concept_id=concept_id, terms=terms)

    return None


def _default_term(concept_id: str) -> str:
    return concept_id.replace("_", " ")
