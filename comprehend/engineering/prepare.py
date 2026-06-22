"""Engineering documentation preparation workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from comprehend.engineering.extract import (
    EngineeringExtractError,
    extract_doc_text,
    write_text_file,
)
from comprehend.engineering.fetch import EngineeringFetchError, fetch_doc_html
from comprehend.engineering.tags import validate_engineering_topic
from comprehend.util import slugify


class EngineeringPrepareError(Exception):
    """Raised when engineering preparation fails."""


@dataclass(frozen=True)
class PreparedEngineering:
    """Local artifacts for a fetched and extracted documentation page."""

    url: str
    slug: str
    topic: str
    source_url: str
    title: str | None
    cache_dir: Path
    html_path: Path
    text_path: Path


def engineering_wiki_slug(slug: str) -> str:
    """Ensure a wiki slug uses the ``engineering-`` prefix.

    Args:
        slug: Raw or partial slug.

    Returns:
        Slug prefixed with ``engineering-`` when missing.
    """
    normalized = slugify(slug.removeprefix("engineering-"))

    return f"engineering-{normalized}"


def infer_engineering_slug(
    url: str,
    *,
    title: str | None = None,
    topic: str | None = None,
    explicit_slug: str | None = None,
) -> str:
    """Infer a wiki slug from a documentation URL or metadata.

    Args:
        url: Documentation page URL.
        title: Optional page title.
        topic: Optional topic slug such as ``cuda``.
        explicit_slug: Optional override slug.

    Returns:
        Wiki page slug with ``engineering-`` prefix.
    """
    if explicit_slug is not None:
        return engineering_wiki_slug(explicit_slug)

    if title is not None:
        base = f"{topic}-{title}" if topic else title
        return engineering_wiki_slug(base)

    path = urlparse(url).path.rstrip("/")
    segment = path.split("/")[-1] if path else url
    base = f"{topic}-{segment}" if topic else segment

    return engineering_wiki_slug(base)


def engineering_cache_dir(
    *,
    cache_root: Path,
    slug: str,
) -> Path:
    """Return the cache directory for an engineering wiki slug.

    Args:
        cache_root: Root cache directory.
        slug: Resolved wiki slug.

    Returns:
        Cache path under ``engineering/``.
    """
    directory_name = slug.removeprefix("engineering-")

    return cache_root / "engineering" / directory_name


def prepare_engineering(
    url: str,
    *,
    cache_root: Path,
    slug: str | None = None,
    title: str | None = None,
    topic: str | None = None,
    force_download: bool = False,
) -> PreparedEngineering:
    """Fetch and extract a documentation page into the local cache.

    Args:
        url: Documentation or tutorial URL.
        cache_root: Root cache directory.
        slug: Optional explicit wiki slug.
        title: Optional display title override.
        topic: Optional topic slug from ``engineering.yaml``.
        force_download: Re-fetch even when ``source.html`` exists.

    Returns:
        Prepared engineering artifacts.

    Raises:
        EngineeringPrepareError: If fetch or extraction fails.
    """
    normalized_topic = validate_engineering_topic(topic) if topic else None
    provisional_slug = infer_engineering_slug(
        url,
        title=title,
        topic=normalized_topic,
        explicit_slug=slug,
    )
    cache_dir = engineering_cache_dir(cache_root=cache_root, slug=provisional_slug)

    try:
        html_path, _metadata = fetch_doc_html(
            url,
            output_dir=cache_dir,
            force_download=force_download,
        )
    except EngineeringFetchError as exc:
        raise EngineeringPrepareError(str(exc)) from exc

    html = html_path.read_text(encoding="utf-8")

    try:
        text, extracted_title = extract_doc_text(html, url=url)
    except EngineeringExtractError as exc:
        raise EngineeringPrepareError(str(exc)) from exc

    resolved_slug = infer_engineering_slug(
        url,
        title=title or extracted_title,
        topic=normalized_topic,
        explicit_slug=slug,
    )
    if resolved_slug != provisional_slug:
        cache_dir = engineering_cache_dir(cache_root=cache_root, slug=resolved_slug)
        cache_dir.mkdir(parents=True, exist_ok=True)
        if html_path.parent != cache_dir:
            html_path = cache_dir / "source.html"
            if not html_path.is_file() or force_download:
                try:
                    html_path, _metadata = fetch_doc_html(
                        url,
                        output_dir=cache_dir,
                        force_download=force_download,
                    )
                    html = html_path.read_text(encoding="utf-8")
                    text, extracted_title = extract_doc_text(html, url=url)
                except (EngineeringFetchError, EngineeringExtractError) as exc:
                    raise EngineeringPrepareError(str(exc)) from exc

    text_path = cache_dir / "text.txt"
    write_text_file(text, output_path=text_path)

    if normalized_topic is None:
        raise EngineeringPrepareError(
            "Engineering topic is required. Pass --topic or set topic in engineering.yaml.",
        )

    prepared = PreparedEngineering(
        url=url,
        slug=resolved_slug,
        topic=normalized_topic,
        source_url=url,
        title=title or extracted_title,
        cache_dir=cache_dir,
        html_path=html_path,
        text_path=text_path,
    )

    return prepared
