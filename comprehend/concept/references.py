"""Extract and search bibliography sections from paper text."""

from __future__ import annotations

import re
from dataclasses import dataclass

from comprehend.util import parse_arxiv_id


REFERENCES_HEADING = re.compile(
    r"\n\s*(?:references|bibliography)\s*\n",
    re.IGNORECASE,
)
SECTION_STOP = re.compile(
    r"\n\s*(?:appendix|supplementary|acknowledg)",
    re.IGNORECASE,
)
BRACKET_REF_START = re.compile(r"^\[\d+\]", re.MULTILINE)
ARXIV_URL_PATTERN = re.compile(
    r"arxiv\.org/(?:abs|pdf)/([\d.]+(?:v\d+)?)",
    re.IGNORECASE,
)
ARXIV_ID_PATTERN = re.compile(
    r"arxiv[:\s]+([\d]{4}\.[\d]{4,5}(?:v\d+)?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReferenceEntry:
    """One bibliography entry parsed from the paper PDF text."""

    index: int | None
    text: str
    arxiv_id: str | None
    arxiv_url: str | None


@dataclass(frozen=True)
class ConceptReferenceMatch:
    """A bibliography entry that likely introduces the concept."""

    entry: ReferenceEntry
    matched_term: str
    score: float


def extract_references_section(full_text: str) -> str | None:
    """Return the references section body, if present.

    Args:
        full_text: Full PDF text extraction.

    Returns:
        References section text, or ``None`` when no heading is found.
    """
    match = REFERENCES_HEADING.search(full_text)
    if match is None:
        return None

    section = full_text[match.end() :]
    stop = SECTION_STOP.search(section)
    if stop is not None:
        section = section[: stop.start()]

    trimmed = section.strip()
    if not trimmed:
        return None

    return trimmed


def split_reference_entries(section: str) -> list[ReferenceEntry]:
    """Split a references section into individual entries.

    Args:
        section: References section text.

    Returns:
        Parsed reference entries.
    """
    if BRACKET_REF_START.search(section):
        chunks = re.split(r"(?=\[\d+\])", section)
    else:
        chunks = re.split(r"\n(?=\d+\.\s)", section)

    entries: list[ReferenceEntry] = []
    for chunk in chunks:
        text = chunk.strip()
        if len(text) < 20:
            continue

        index_match = re.match(r"\[(\d+)\]", text)
        index = int(index_match.group(1)) if index_match else None

        arxiv_id = _arxiv_id_from_text(text)
        arxiv_url = (
            f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id is not None else None
        )

        entries.append(
            ReferenceEntry(
                index=index,
                text=text,
                arxiv_id=arxiv_id,
                arxiv_url=arxiv_url,
            ),
        )

    return entries


def find_concept_reference_matches(
    entries: list[ReferenceEntry],
    *,
    terms: list[str],
    concept_id: str,
) -> list[ConceptReferenceMatch]:
    """Rank bibliography entries that likely introduce the concept.

    Args:
        entries: Parsed bibliography entries.
        terms: Link/search terms from ``papers.yaml``.
        concept_id: Concept id such as ``ccff``.

    Returns:
        Matches sorted by descending relevance score.
    """
    search_terms = _search_terms(terms=terms, concept_id=concept_id)
    matches: list[ConceptReferenceMatch] = []

    for entry in entries:
        entry_lower = entry.text.lower()
        best_score = 0.0
        best_term = ""

        for term in search_terms:
            term_lower = term.lower()
            if term_lower not in entry_lower:
                continue

            score = float(len(term_lower))
            if entry.arxiv_id is not None:
                score += 5.0

            if score > best_score:
                best_score = score
                best_term = term

        if best_score > 0:
            matches.append(
                ConceptReferenceMatch(
                    entry=entry,
                    matched_term=best_term,
                    score=best_score,
                ),
            )

    matches.sort(key=lambda match: match.score, reverse=True)

    return matches


def _search_terms(*, terms: list[str], concept_id: str) -> list[str]:
    normalized_id = concept_id.replace("_", " ")
    extra = [normalized_id, concept_id.replace("_", "-")]
    if normalized_id.upper() != normalized_id:
        extra.append(normalized_id.upper())

    seen: set[str] = set()
    ordered: list[str] = []

    for candidate in [*terms, *extra]:
        key = candidate.strip().lower()
        if not key or key in seen:
            continue

        seen.add(key)
        ordered.append(candidate.strip())

    return ordered


def _arxiv_id_from_text(text: str) -> str | None:
    match = ARXIV_URL_PATTERN.search(text)
    if match is not None:
        return match.group(1).split("v", maxsplit=1)[0]

    label_match = ARXIV_ID_PATTERN.search(text)
    if label_match is not None:
        return label_match.group(1).split("v", maxsplit=1)[0]

    for token in text.split():
        cleaned = token.strip(".,;)")
        if parse_arxiv_id(f"https://arxiv.org/abs/{cleaned}") is not None:
            return cleaned.split("v", maxsplit=1)[0]

    return None
