"""Text extraction for engineering documentation pages."""

from __future__ import annotations

from pathlib import Path

import trafilatura
from trafilatura.metadata import extract_metadata


class EngineeringExtractError(Exception):
    """Raised when documentation content cannot be extracted."""


def extract_doc_text(
    html: str,
    *,
    url: str,
) -> tuple[str, str | None]:
    """Extract main documentation text and title from HTML.

    Args:
        html: Raw HTML content.
        url: Source page URL for metadata extraction.

    Returns:
        Tuple of ``(text, title)``.
    """
    metadata = extract_metadata(html, default_url=url)
    title = metadata.title if metadata is not None else None

    text = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        include_links=False,
        output_format="txt",
    )
    if not text or not text.strip():
        raise EngineeringExtractError("No main documentation text could be extracted")

    extracted_text = text.strip()

    return extracted_text, title


def write_text_file(
    text: str,
    *,
    output_path: Path,
) -> Path:
    """Write extracted documentation text to disk.

    Args:
        text: Extracted plain text.
        output_path: Destination path, typically ``text.txt``.

    Returns:
        Written path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")

    return output_path
