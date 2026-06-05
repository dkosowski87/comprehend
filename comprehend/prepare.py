"""Paper preparation workflow helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from comprehend.pdf.download import PaperDownloadError, download_paper, paper_cache_dir
from comprehend.pdf.extract import ExtractedPaper, extract_paper, list_figures
from comprehend.pdf.figures import list_figure_regions
from comprehend.util import arxiv_slug, parse_arxiv_id, slugify


@dataclass(frozen=True)
class PreparedPaper:
    """Local artifacts for a downloaded and extracted paper."""

    url: str
    slug: str
    pdf_url: str
    title: str | None
    cache_dir: Path
    pdf_path: Path
    extracted: ExtractedPaper
    figures_json_path: Path


def infer_slug(
    url: str,
    *,
    title: str | None = None,
    explicit_slug: str | None = None,
) -> str:
    """Infer a wiki slug from URL metadata.

    Args:
        url: Source paper URL.
        title: Optional paper title.
        explicit_slug: Optional override slug.

    Returns:
        Wiki page slug.
    """
    if explicit_slug is not None:
        return explicit_slug

    arxiv_id = parse_arxiv_id(url)
    if arxiv_id is not None:
        return arxiv_slug(arxiv_id)

    if title is not None:
        return slugify(title)

    return slugify(url)


def prepare_paper(
    url: str,
    *,
    cache_root: Path,
    slug: str | None = None,
    force_download: bool = False,
) -> PreparedPaper:
    """Download and extract a paper into the local cache.

    Args:
        url: arXiv or direct PDF URL.
        cache_root: Root cache directory.
        slug: Optional explicit wiki slug.
        force_download: Re-download even when ``paper.pdf`` exists.

    Returns:
        Prepared paper artifacts.

    Raises:
        PaperDownloadError: If download fails.
    """
    provisional_slug = infer_slug(url, explicit_slug=slug)
    cache_dir = paper_cache_dir(url, cache_root=cache_root, slug=provisional_slug)
    pdf_path = cache_dir / "paper.pdf"

    metadata: dict[str, str] = {}
    if force_download or not pdf_path.is_file():
        pdf_path, metadata = download_paper(url, output_dir=cache_dir)
    else:
        metadata["source_url"] = url
        arxiv_id = parse_arxiv_id(url)
        if arxiv_id is not None:
            metadata["arxiv_id"] = arxiv_id
            metadata["pdf_url"] = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        else:
            metadata["pdf_url"] = url

    title = metadata.get("title")
    resolved_slug = infer_slug(url, title=title, explicit_slug=slug)
    if resolved_slug != provisional_slug:
        cache_dir = paper_cache_dir(url, cache_root=cache_root, slug=resolved_slug)
        if pdf_path.parent != cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = cache_dir / "paper.pdf"
            if not pdf_path.is_file() and (provisional_slug != resolved_slug):
                pdf_path, metadata = download_paper(url, output_dir=cache_dir)

    extracted = extract_paper(pdf_path, output_dir=cache_dir)
    figures = list_figures(pdf_path)
    figure_regions = list_figure_regions(pdf_path)
    figures_json_path = cache_dir / "figures.json"
    figures_payload = {
        "embedded_images": [
            {
                "page": figure.page,
                "index": figure.index,
                "width": figure.width,
                "height": figure.height,
                "xref": figure.xref,
            }
            for figure in figures
        ],
        "figure_regions": [
            {
                "page": region.page,
                "number": region.number,
                "clip": list(region.clip),
            }
            for region in figure_regions
        ],
    }

    figures_json_path.write_text(
        json.dumps(figures_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    pdf_url = metadata.get("pdf_url", url)
    prepared = PreparedPaper(
        url=url,
        slug=resolved_slug,
        pdf_url=pdf_url,
        title=title,
        cache_dir=cache_dir,
        pdf_path=pdf_path,
        extracted=extracted,
        figures_json_path=figures_json_path,
    )

    return prepared
