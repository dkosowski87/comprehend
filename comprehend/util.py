"""Shared utilities for comprehend."""

from __future__ import annotations

import re
from pathlib import Path

ARXIV_ABS_PATTERN = re.compile(
    r"arxiv\.org/abs/(?P<id>[\d.]+(?:v\d+)?)",
    re.IGNORECASE,
)
ARXIV_PDF_PATTERN = re.compile(
    r"arxiv\.org/pdf/(?P<id>[\d.]+(?:v\d+)?)",
    re.IGNORECASE,
)


def default_cache_dir() -> Path:
    """Return the default local cache directory for paper assets."""
    cache_dir = Path.cwd() / ".comprehend"

    return cache_dir


def slugify(text: str, *, max_length: int = 80) -> str:
    """Convert text into a wiki-safe slug.

    Args:
        text: Source string, typically a paper title or identifier.
        max_length: Maximum slug length.

    Returns:
        Lowercase hyphenated slug.
    """
    normalized = text.lower()
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    normalized = re.sub(r"[\s_-]+", "-", normalized).strip("-")

    if len(normalized) <= max_length:
        return normalized

    trimmed = normalized[:max_length].rstrip("-")

    return trimmed


def parse_arxiv_id(url: str) -> str | None:
    """Extract an arXiv identifier from a URL, if present.

    Args:
        url: Paper URL or PDF URL.

    Returns:
        arXiv id string, or ``None`` when the URL is not arXiv.
    """
    for pattern in (ARXIV_ABS_PATTERN, ARXIV_PDF_PATTERN):
        match = pattern.search(url)
        if match is not None:
            return match.group("id")

    return None


def arxiv_slug(arxiv_id: str) -> str:
    """Build a stable wiki slug from an arXiv id.

    Args:
        arxiv_id: arXiv identifier such as ``2012.12877``.

    Returns:
        Slug prefixed with ``arxiv-``.
    """
    safe_id = arxiv_id.replace(".", "-")

    return f"arxiv-{safe_id}"


def default_repo_from_git() -> str | None:
    """Infer ``owner/repo`` from the current git remote when available.

    Returns:
        Repository slug, or ``None`` when inference fails.
    """
    git_config = Path.cwd() / ".git" / "config"
    if not git_config.is_file():
        return None

    config_text = git_config.read_text(encoding="utf-8")
    for line in config_text.splitlines():
        line = line.strip()
        if not line.startswith("url"):
            continue

        _, _, remote_url = line.partition("=")
        remote_url = remote_url.strip()
        match = re.search(r"github\.com[:/](?P<repo>[^/\s]+/[^/\s]+?)(?:\.git)?$", remote_url)
        if match is not None:
            return match.group("repo")

    return None
