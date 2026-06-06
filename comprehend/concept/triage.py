"""Classify concepts as simple vs paper-originated and check the paper queue."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from comprehend.concept.prepare import ConceptPrepareError, prepare_concept
from comprehend.concept.references import (
    ConceptReferenceMatch,
    extract_references_section,
    find_concept_reference_matches,
    split_reference_entries,
)
from comprehend.pdf.download import paper_cache_dir
from comprehend.prepare import infer_slug
from comprehend.publish.github_wiki import WikiConfig, wiki_page_exists
from comprehend.queue import QueueStatus, find_paper_entry, load_paper_queue, queue_items

if TYPE_CHECKING:
    from comprehend.queue import PaperQueueEntry


class ConceptKind(str, Enum):
    """How much background a concept explanation likely needs."""

    SIMPLE = "simple"
    PAPER_ORIGINATED = "paper_originated"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class QueueMatch:
    """A bibliography hit that is already listed in ``papers.yaml``."""

    slug: str
    title: str | None
    url: str
    status: str


@dataclass(frozen=True)
class SuggestedQueueEntry:
    """Proposed ``papers.yaml`` row for an origin paper not yet queued."""

    url: str
    slug: str
    title: str | None
    arxiv_id: str | None


@dataclass(frozen=True)
class ConceptTriageResult:
    """Outcome of concept origin triage before writing ``concept.json``."""

    concept_id: str
    paper_slug: str
    kind: ConceptKind
    terms: list[str]
    best_reference_match: ConceptReferenceMatch | None
    queue_match: QueueMatch | None
    suggested_queue_entry: SuggestedQueueEntry | None
    references_available: bool
    message: str


def triage_concept(
    *,
    paper_slug: str,
    concept_id: str,
    papers_file: Path,
    wiki_config: WikiConfig,
    cache_root: Path,
    terms: list[str] | None = None,
) -> ConceptTriageResult:
    """Check whether a concept is defined in a cited origin paper.

    Args:
        paper_slug: Wiki slug of the paper being summarized.
        concept_id: Concept identifier such as ``cyclic_shift``.
        papers_file: Path to ``papers.yaml``.
        wiki_config: Wiki configuration.
        cache_root: Local cache root (``.comprehend``).
        terms: Optional link-search terms for bibliography matching.

    Returns:
        Triage result with queue status and a user-facing message.

    Raises:
        ConceptPrepareError: If prepare prerequisites fail.
    """
    prepared = prepare_concept(
        paper_slug=paper_slug,
        concept_id=concept_id,
        papers_file=papers_file,
        wiki_config=wiki_config,
        cache_root=cache_root,
        terms=terms,
    )

    entries = load_paper_queue(papers_file)
    paper_entry = find_paper_entry(entries, paper_slug=paper_slug)
    if paper_entry is None:
        raise ConceptPrepareError(f"Paper slug '{paper_slug}' not found in {papers_file}")

    text_path = paper_cache_dir(
        paper_entry.url,
        cache_root=cache_root,
        slug=paper_slug,
    ) / "paper.txt"

    references_available = False
    best_match: ConceptReferenceMatch | None = None

    if text_path.is_file():
        full_text = text_path.read_text(encoding="utf-8")
        section = extract_references_section(full_text)
        if section is not None:
            references_available = True
            ref_entries = split_reference_entries(section)
            matches = find_concept_reference_matches(
                ref_entries,
                terms=prepared.terms,
                concept_id=concept_id,
            )
            if matches:
                best_match = matches[0]

    if best_match is None:
        kind = ConceptKind.UNCERTAIN if not references_available else ConceptKind.SIMPLE
        message = _simple_message(kind=kind, references_available=references_available)

        return ConceptTriageResult(
            concept_id=concept_id,
            paper_slug=paper_slug,
            kind=kind,
            terms=list(prepared.terms),
            best_reference_match=None,
            queue_match=None,
            suggested_queue_entry=None,
            references_available=references_available,
            message=message,
        )

    queue_match, suggested = _resolve_queue(
        entries=entries,
        wiki_config=wiki_config,
        match=best_match,
    )

    kind = ConceptKind.PAPER_ORIGINATED
    message = _paper_originated_message(
        match=best_match,
        queue_match=queue_match,
        suggested=suggested,
    )

    return ConceptTriageResult(
        concept_id=concept_id,
        paper_slug=paper_slug,
        kind=kind,
        terms=list(prepared.terms),
        best_reference_match=best_match,
        queue_match=queue_match,
        suggested_queue_entry=suggested,
        references_available=references_available,
        message=message,
    )


def _resolve_queue(
    *,
    entries: list[PaperQueueEntry],
    wiki_config: WikiConfig,
    match: ConceptReferenceMatch,
) -> tuple[QueueMatch | None, SuggestedQueueEntry | None]:
    entry = match.entry
    url = entry.arxiv_url
    slug: str | None = None

    if url is not None:
        slug = infer_slug(url)
    else:
        slug = infer_slug(entry.text[:120])

    if url is None:
        suggested = SuggestedQueueEntry(
            url=f"placeholder://reference/{slug}",
            slug=slug,
            title=_title_hint(entry.text),
            arxiv_id=entry.arxiv_id,
        )

        return None, suggested

    queue_entry = find_paper_entry(entries, paper_slug=slug)
    if queue_entry is None:
        for candidate in entries:
            if candidate.url.rstrip("/") == url.rstrip("/"):
                queue_entry = candidate
                slug = candidate.resolve_slug()
                break

    if queue_entry is not None:
        resolved_slug = queue_entry.resolve_slug()
        status = _queue_status(slug=resolved_slug, wiki_config=wiki_config)
        queue_match = QueueMatch(
            slug=resolved_slug,
            title=queue_entry.title,
            url=queue_entry.url,
            status=status,
        )

        return queue_match, None

    suggested = SuggestedQueueEntry(
        url=url,
        slug=slug,
        title=_title_hint(entry.text),
        arxiv_id=entry.arxiv_id,
    )

    return None, suggested


def _queue_status(*, slug: str, wiki_config: WikiConfig) -> str:
    if wiki_config.wiki_dir.is_dir() and wiki_page_exists(
        slug,
        wiki_dir=wiki_config.wiki_dir,
    ):
        return QueueStatus.PUBLISHED.value

    return QueueStatus.PENDING.value


def _title_hint(reference_text: str) -> str | None:
    line = reference_text.splitlines()[0]
    cleaned = re.sub(r"^\[\d+\]\s*", "", line).strip()

    if len(cleaned) < 12:
        return None

    return cleaned[:200]


def _simple_message(*, kind: ConceptKind, references_available: bool) -> str:
    if kind is ConceptKind.SIMPLE:
        return (
            "No bibliography entry clearly introduces this concept. "
            "Treat it as a simple concept (web research + standard concept page)."
        )

    return (
        "Could not parse a References section from the cached PDF. "
        "Treat as a simple concept unless you know it comes from another paper."
    )


def _paper_originated_message(
    *,
    match: ConceptReferenceMatch,
    queue_match: QueueMatch | None,
    suggested: SuggestedQueueEntry | None,
) -> str:
    excerpt = " ".join(match.entry.text.split())[:220]
    header = (
        f"Bibliography likely introduces this concept (matched '{match.matched_term}'): "
        f"{excerpt}..."
    )

    if queue_match is not None:
        title = queue_match.title or queue_match.slug
        status_note = (
            "published on the wiki"
            if queue_match.status == QueueStatus.PUBLISHED.value
            else "in papers.yaml but not yet summarized"
        )

        return (
            f"{header} Origin paper is already queued as '{queue_match.slug}' "
            f"({title}, {status_note}). You can summarize that paper first, then "
            "write the concept page, or proceed with a shorter concept page now."
        )

    if suggested is not None:
        if suggested.arxiv_id is not None:
            return (
                f"{header} Origin paper is not in papers.yaml ({suggested.url}). "
                "Ask the user whether to add it to the queue before continuing."
            )

        return (
            f"{header} A likely origin paper was found but no arXiv URL was detected. "
            "Ask the user for the paper URL if they want it added to papers.yaml."
        )

    return header


def triage_result_to_dict(result: ConceptTriageResult) -> dict[str, object]:
    """Serialize a triage result for JSON CLI output.

    Args:
        result: Triage outcome.

    Returns:
        JSON-serializable mapping.
    """
    payload: dict[str, object] = {
        "concept_id": result.concept_id,
        "paper_slug": result.paper_slug,
        "kind": result.kind.value,
        "terms": result.terms,
        "references_available": result.references_available,
        "message": result.message,
        "proceed_with_concept_page": True,
        "ask_user_add_to_queue": False,
    }

    if result.best_reference_match is not None:
        entry = result.best_reference_match.entry
        payload["origin_reference"] = {
            "matched_term": result.best_reference_match.matched_term,
            "score": result.best_reference_match.score,
            "index": entry.index,
            "excerpt": " ".join(entry.text.split())[:280],
            "arxiv_id": entry.arxiv_id,
            "arxiv_url": entry.arxiv_url,
        }

    if result.queue_match is not None:
        payload["queue"] = {
            "in_queue": True,
            "slug": result.queue_match.slug,
            "title": result.queue_match.title,
            "url": result.queue_match.url,
            "status": result.queue_match.status,
        }

    if result.suggested_queue_entry is not None:
        suggested = result.suggested_queue_entry
        has_real_url = not suggested.url.startswith("placeholder://")
        payload["queue"] = {"in_queue": False}
        payload["suggested_queue_entry"] = {
            "url": suggested.url if has_real_url else None,
            "slug": suggested.slug,
            "title": suggested.title,
            "arxiv_id": suggested.arxiv_id,
        }
        payload["ask_user_add_to_queue"] = has_real_url

    return payload
