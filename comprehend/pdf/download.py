"""PDF download helpers."""

from __future__ import annotations

from pathlib import Path

import arxiv
import httpx

from comprehend.util import parse_arxiv_id, slugify


class PaperDownloadError(Exception):
    """Raised when a paper cannot be downloaded."""


def resolve_pdf_url(url: str) -> tuple[str, str | None]:
    """Resolve a paper URL to a direct PDF URL.

    Supports arXiv abstract pages, arXiv PDF links, and direct PDF URLs.

    Args:
        url: User-provided paper URL.

    Returns:
        Tuple of ``(pdf_url, arxiv_id)``. ``arxiv_id`` is ``None`` for non-arXiv URLs.

    Raises:
        PaperDownloadError: If the URL cannot be resolved.
    """
    arxiv_id = parse_arxiv_id(url)
    if arxiv_id is not None:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        return pdf_url, arxiv_id

    parsed = url.lower().split("?", maxsplit=1)[0]
    if parsed.endswith(".pdf"):
        return url, None

    raise PaperDownloadError(
        f"Unsupported URL (expected arXiv or direct PDF): {url}",
    )


def fetch_arxiv_metadata(arxiv_id: str) -> arxiv.Result:
    """Fetch arXiv metadata for an identifier.

    Args:
        arxiv_id: arXiv paper id.

    Returns:
        arXiv search result with title and PDF link.

    Raises:
        PaperDownloadError: If metadata lookup fails.
    """
    base_id = arxiv_id.split("v", maxsplit=1)[0]
    search = arxiv.Search(id_list=[base_id], max_results=1)
    client = arxiv.Client(
        page_size=1,
        delay_seconds=3.0,
        num_retries=3,
    )
    results = list(client.results(search))
    if not results:
        raise PaperDownloadError(f"No arXiv paper found for id: {arxiv_id}")

    return results[0]


def download_paper(
    url: str,
    *,
    output_dir: Path,
) -> tuple[Path, dict[str, str]]:
    """Download a paper PDF to ``output_dir``.

    Args:
        url: arXiv abstract page, arXiv PDF link, or direct PDF URL.
        output_dir: Directory where ``paper.pdf`` will be written.

    Returns:
        Tuple of ``(pdf_path, metadata)``. Metadata includes ``pdf_url``,
        optional ``arxiv_id``, and optional ``title``.

    Raises:
        PaperDownloadError: If download fails.
    """
    pdf_url, arxiv_id = resolve_pdf_url(url)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "paper.pdf"

    metadata: dict[str, str] = {
        "source_url": url,
        "pdf_url": pdf_url,
    }

    if arxiv_id is not None:
        metadata["arxiv_id"] = arxiv_id
        try:
            arxiv_result = fetch_arxiv_metadata(arxiv_id)
            metadata["title"] = arxiv_result.title
        except (PaperDownloadError, arxiv.ArxivError):
            # Title lookup is optional; arXiv API rate limits (429) must not block PDF download.
            pass

    try:
        with httpx.Client(follow_redirects=True, timeout=120.0) as client:
            response = client.get(pdf_url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not pdf_url.endswith(".pdf"):
                raise PaperDownloadError(
                    f"URL did not return a PDF (content-type: {content_type})",
                )
            pdf_path.write_bytes(response.content)
    except httpx.HTTPError as exc:
        raise PaperDownloadError(f"Failed to download PDF: {exc}") from exc

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise PaperDownloadError("Downloaded PDF is empty or missing")

    return pdf_path, metadata


def paper_cache_dir(
    url: str,
    *,
    cache_root: Path,
    slug: str | None = None,
) -> Path:
    """Return the cache directory for a paper URL.

    Args:
        url: Paper URL.
        cache_root: Root cache directory.
        slug: Optional explicit slug; inferred from arXiv id or URL otherwise.

    Returns:
        Cache directory path for the paper.
    """
    arxiv_id = parse_arxiv_id(url)
    if slug is not None:
        directory_name = slug
    elif arxiv_id is not None:
        directory_name = arxiv_id.replace(".", "-")
    else:
        directory_name = slugify(url)

    paper_dir = cache_root / "papers" / directory_name

    return paper_dir
