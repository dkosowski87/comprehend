"""Engineering queue loading and status tracking."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

from comprehend.engineering.prepare import infer_engineering_slug, prepare_engineering
from comprehend.engineering.tags import validate_engineering_topic
from comprehend.publish.github_wiki import WikiConfig, wiki_page_exists
from comprehend.util import default_cache_dir


class EngineeringQueueStatus(str, Enum):
    """Status of a queued engineering resource."""

    PENDING = "pending"
    PUBLISHED = "published"


@dataclass(frozen=True)
class EngineeringQueueEntry:
    """One engineering entry from ``engineering.yaml``."""

    url: str
    slug: str | None = None
    title: str | None = None
    topic: str | None = None
    secondary_urls: tuple[str, ...] = ()

    def resolve_slug(self) -> str:
        """Return the wiki slug for this entry."""
        normalized_topic = validate_engineering_topic(self.topic) if self.topic else None

        if self.slug is not None:
            return infer_engineering_slug(self.url, explicit_slug=self.slug, topic=normalized_topic)

        return infer_engineering_slug(
            self.url,
            title=self.title,
            topic=normalized_topic,
        )

    def resolve_topic(self) -> str:
        """Return the validated topic for this entry.

        Raises:
            ValueError: When ``topic`` is missing or invalid.
        """
        if self.topic is None:
            raise ValueError(f"Engineering queue entry is missing topic: {self.url}")

        return validate_engineering_topic(self.topic)


@dataclass(frozen=True)
class EngineeringQueueItem:
    """Queue entry enriched with slug, topic, and status."""

    url: str
    slug: str
    title: str | None
    topic: str
    status: EngineeringQueueStatus


def load_engineering_queue(path: Path) -> list[EngineeringQueueEntry]:
    """Load engineering queue entries from YAML.

    Args:
        path: Path to ``engineering.yaml``.

    Returns:
        Parsed queue entries.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    engineering = raw.get("engineering", []) if isinstance(raw, dict) else []
    entries: list[EngineeringQueueEntry] = []

    for item in engineering:
        if not isinstance(item, dict) or "url" not in item:
            continue

        slug_value = item.get("slug")
        slug = str(slug_value) if slug_value is not None else None

        title_value = item.get("title")
        title = str(title_value) if title_value is not None else None

        topic_value = item.get("topic")
        topic = str(topic_value) if topic_value is not None else None

        secondary_raw = item.get("secondary_urls")
        secondary_urls: tuple[str, ...] = ()
        if isinstance(secondary_raw, list):
            secondary_urls = tuple(str(url) for url in secondary_raw)

        entry = EngineeringQueueEntry(
            url=str(item["url"]),
            slug=slug,
            title=title,
            topic=topic,
            secondary_urls=secondary_urls,
        )
        entries.append(entry)

    return entries


def engineering_queue_items(
    entries: list[EngineeringQueueEntry],
    *,
    wiki_config: WikiConfig,
) -> list[EngineeringQueueItem]:
    """Attach slug, topic, and wiki status to queue entries.

    Args:
        entries: Parsed queue entries.
        wiki_config: Wiki configuration for deduplication checks.

    Returns:
        Enriched queue items.
    """
    items: list[EngineeringQueueItem] = []

    for entry in entries:
        slug = entry.resolve_slug()
        topic = entry.resolve_topic()
        if wiki_config.wiki_dir.is_dir():
            published = wiki_page_exists(slug, wiki_dir=wiki_config.wiki_dir)
        else:
            published = False

        status = EngineeringQueueStatus.PUBLISHED if published else EngineeringQueueStatus.PENDING
        item = EngineeringQueueItem(
            url=entry.url,
            slug=slug,
            title=entry.title,
            topic=topic,
            status=status,
        )
        items.append(item)

    return items


def next_pending_engineering(
    items: list[EngineeringQueueItem],
) -> EngineeringQueueItem | None:
    """Return the first pending engineering queue item.

    Args:
        items: Enriched queue items.

    Returns:
        First pending item, or ``None``.
    """
    for item in items:
        if item.status == EngineeringQueueStatus.PENDING:
            return item

    return None


def prepare_engineering_queue_entry(
    entry: EngineeringQueueEntry,
    *,
    cache_root: Path | None = None,
) -> Path:
    """Fetch and extract a queued engineering resource.

    Args:
        entry: Queue entry to prepare.
        cache_root: Optional cache root override.

    Returns:
        Engineering cache directory path.
    """
    cache = cache_root or default_cache_dir()
    prepared = prepare_engineering(
        entry.url,
        cache_root=cache,
        slug=entry.slug,
        title=entry.title,
        topic=entry.topic,
    )

    return prepared.cache_dir


def add_engineering_to_queue(
    path: Path,
    *,
    url: str,
    topic: str,
    slug: str | None = None,
    title: str | None = None,
) -> EngineeringQueueEntry:
    """Append an engineering resource to ``engineering.yaml``.

    Args:
        path: Path to ``engineering.yaml``.
        url: Documentation or tutorial URL.
        topic: Primary topic slug such as ``cuda``.
        slug: Optional wiki slug override.
        title: Optional display title.

    Returns:
        The new or existing queue entry.

    Raises:
        ValueError: When the URL is already present under a different slug.
    """
    if not path.is_file():
        path.write_text("engineering: []\n", encoding="utf-8")

    normalized_topic = validate_engineering_topic(topic)
    entries = load_engineering_queue(path)
    resolved_slug = infer_engineering_slug(
        url,
        title=title,
        topic=normalized_topic,
        explicit_slug=slug,
    )

    for entry in entries:
        if entry.url.rstrip("/") == url.rstrip("/"):
            return entry

        if entry.resolve_slug() == resolved_slug:
            raise ValueError(
                f"Slug '{resolved_slug}' already used for {entry.url}",
            )

    new_entry = EngineeringQueueEntry(
        url=url,
        slug=resolved_slug,
        title=title,
        topic=normalized_topic,
    )

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    engineering = raw.get("engineering", []) if isinstance(raw, dict) else []
    engineering.append(
        {
            "url": url,
            "slug": resolved_slug,
            "title": title or resolved_slug,
            "topic": normalized_topic,
        },
    )
    raw["engineering"] = engineering
    path.write_text(
        yaml.dump(raw, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )

    return new_entry
