"""HTTP fetch helpers for engineering documentation pages."""

from __future__ import annotations

from pathlib import Path

import httpx

from comprehend.util import parse_arxiv_id


class EngineeringFetchError(Exception):
    """Raised when a documentation page cannot be downloaded."""


def is_paper_url(url: str) -> bool:
    """Return whether a URL looks like a paper rather than documentation.

    Args:
        url: User-provided URL.

    Returns:
        ``True`` when the URL is arXiv or a direct PDF link.
    """
    if parse_arxiv_id(url) is not None:
        return True

    parsed = url.lower().split("?", maxsplit=1)[0]

    return parsed.endswith(".pdf")


def fetch_doc_html(
    url: str,
    *,
    output_dir: Path,
    force_download: bool = False,
) -> tuple[Path, dict[str, str]]:
    """Download a documentation or tutorial HTML page.

    Args:
        url: Documentation or tutorial URL.
        output_dir: Directory where ``source.html`` will be written.
        force_download: Re-fetch even when ``source.html`` exists.

    Returns:
        Tuple of ``(html_path, metadata)``.

    Raises:
        EngineeringFetchError: If the URL is unsupported or download fails.
    """
    if is_paper_url(url):
        raise EngineeringFetchError(
            f"URL looks like a paper, not documentation: {url}. "
            "Use `comprehend prepare` for papers.",
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "source.html"
    metadata: dict[str, str] = {
        "source_url": url,
    }

    if html_path.is_file() and not force_download:
        return html_path, metadata

    headers = {
        "User-Agent": "comprehend/0.1 (+https://github.com/dkosowski87/comprehend)",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        with httpx.Client(follow_redirects=True, timeout=120.0, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type.lower() and "text/" not in content_type.lower():
                raise EngineeringFetchError(
                    f"URL did not return HTML (content-type: {content_type})",
                )
            html_path.write_bytes(response.content)
    except httpx.HTTPError as exc:
        raise EngineeringFetchError(f"Failed to download documentation page: {exc}") from exc

    if not html_path.exists() or html_path.stat().st_size == 0:
        raise EngineeringFetchError("Downloaded HTML is empty or missing")

    return html_path, metadata
