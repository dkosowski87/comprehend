"""Paper queue loading and status tracking."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

from comprehend.concept.refs import ConceptRef, parse_concept_ref
from comprehend.prepare import infer_slug, prepare_paper
from comprehend.publish.github_wiki import WikiConfig, wiki_page_exists
from comprehend.util import default_cache_dir


class QueueStatus(str, Enum):
    """Status of a queued paper."""

    PENDING = "pending"
    PUBLISHED = "published"


@dataclass(frozen=True)
class PaperQueueEntry:
    """One paper entry from ``papers.yaml``."""

    url: str
    tags: list[str]
    concepts: list[ConceptRef]


@dataclass(frozen=True)
class PaperQueueItem:
    """Queue entry enriched with slug and status."""

    url: str
    tags: list[str]
    slug: str
    status: QueueStatus


def load_paper_queue(path: Path) -> list[PaperQueueEntry]:
    """Load paper queue entries from YAML.

    Args:
        path: Path to ``papers.yaml``.

    Returns:
        Parsed queue entries.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    papers = raw.get("papers", []) if isinstance(raw, dict) else []
    entries: list[PaperQueueEntry] = []

    for item in papers:
        if not isinstance(item, dict) or "url" not in item:
            continue

        tags = item.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        raw_concepts = item.get("concepts", [])
        concepts: list[ConceptRef] = []
        if isinstance(raw_concepts, list):
            for raw_concept in raw_concepts:
                concept_ref = parse_concept_ref(raw_concept)
                if concept_ref is not None:
                    concepts.append(concept_ref)

        entry = PaperQueueEntry(
            url=str(item["url"]),
            tags=[str(tag) for tag in tags],
            concepts=concepts,
        )
        entries.append(entry)

    return entries


def queue_items(
    entries: list[PaperQueueEntry],
    *,
    wiki_config: WikiConfig,
) -> list[PaperQueueItem]:
    """Attach slug and wiki status to queue entries.

    Args:
        entries: Parsed queue entries.
        wiki_config: Wiki configuration for deduplication checks.

    Returns:
        Enriched queue items.
    """
    items: list[PaperQueueItem] = []

    for entry in entries:
        slug = infer_slug(entry.url)
        if wiki_config.wiki_dir.is_dir():
            published = wiki_page_exists(slug, wiki_dir=wiki_config.wiki_dir)
        else:
            published = False

        status = QueueStatus.PUBLISHED if published else QueueStatus.PENDING
        item = PaperQueueItem(
            url=entry.url,
            tags=entry.tags,
            slug=slug,
            status=status,
        )
        items.append(item)

    return items


def next_pending_item(items: list[PaperQueueItem]) -> PaperQueueItem | None:
    """Return the first pending queue item.

    Args:
        items: Enriched queue items.

    Returns:
        First pending item, or ``None``.
    """
    for item in items:
        if item.status == QueueStatus.PENDING:
            return item

    return None


def prepare_queue_entry(
    entry: PaperQueueEntry,
    *,
    cache_root: Path | None = None,
) -> Path:
    """Download and extract a queued paper.

    Args:
        entry: Queue entry to prepare.
        cache_root: Optional cache root override.

    Returns:
        Paper cache directory path.
    """
    cache = cache_root or default_cache_dir()
    prepared = prepare_paper(entry.url, cache_root=cache)

    return prepared.cache_dir


def find_paper_entry(
    entries: list[PaperQueueEntry],
    *,
    paper_slug: str,
) -> PaperQueueEntry | None:
    """Find a queue entry by its wiki slug.

    Args:
        entries: Parsed queue entries.
        paper_slug: Paper wiki slug such as ``arxiv-2103-14030``.

    Returns:
        Matching entry, or ``None``.
    """
    for entry in entries:
        if infer_slug(entry.url) == paper_slug:
            return entry

    return None


def find_concept_ref(
    entry: PaperQueueEntry,
    *,
    concept_id: str,
) -> ConceptRef | None:
    """Find a declared concept on a paper entry.

    Args:
        entry: Paper queue entry.
        concept_id: Concept id such as ``cyclic_shift``.

    Returns:
        Matching concept reference, or ``None``.
    """
    for concept_ref in entry.concepts:
        if concept_ref.concept_id == concept_id:
            return concept_ref

    return None
