"""Concept reference helpers for link patching and term resolution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptRef:
    """Legacy concept reference shape (no longer stored in ``papers.yaml``)."""

    concept_id: str
    terms: list[str]


def default_concept_terms(concept_id: str) -> list[str]:
    """Build default link-search terms from a concept id."""
    return [concept_id.replace("_", " ")]


def resolve_link_terms(
    concept_id: str,
    *,
    terms: list[str] | None = None,
    keywords: list[str] | None = None,
) -> list[str]:
    """Resolve terms used to patch first mentions in a paper wiki page.

    Priority: explicit ``terms`` (CLI) → ``keywords`` from ``concept.json`` →
    default phrase from ``concept_id``.
    """
    if terms:
        return [term.strip() for term in terms if term.strip()]

    if keywords:
        return [keyword.strip() for keyword in keywords if keyword.strip()]

    return default_concept_terms(concept_id)


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
