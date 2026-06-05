"""Import conference papers from paperswithcode.co into papers.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from comprehend.pwc.client import PapersWithCodeClient
from comprehend.pwc.models import ConferencePaper, PresentationFilter
from comprehend.queue import add_paper_to_queue, load_paper_queue
from comprehend.util import parse_arxiv_id


@dataclass(frozen=True)
class ImportSkippedPaper:
    """Paper skipped because it is already queued."""

    title: str
    url: str
    reason: str


@dataclass(frozen=True)
class ImportAddedPaper:
    """Paper appended to papers.yaml."""

    title: str
    url: str
    slug: str


@dataclass(frozen=True)
class ImportConferenceResult:
    """Summary of importing one conference filter into papers.yaml."""

    conference_slug: str
    presentation: PresentationFilter
    fetched: int
    added: tuple[ImportAddedPaper, ...]
    skipped: tuple[ImportSkippedPaper, ...]

    @property
    def added_count(self) -> int:
        return len(self.added)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


def _queue_index(entries: list) -> tuple[set[str], set[str], set[str]]:
    urls: set[str] = set()
    arxiv_ids: set[str] = set()
    titles: set[str] = set()

    for entry in entries:
        urls.add(entry.url.rstrip("/"))
        arxiv_id = parse_arxiv_id(entry.url)
        if arxiv_id is not None:
            arxiv_ids.add(arxiv_id)
        if entry.title:
            titles.add(entry.title.strip().lower())

    return urls, arxiv_ids, titles


def _is_already_queued(
    paper: ConferencePaper,
    *,
    urls: set[str],
    arxiv_ids: set[str],
    titles: set[str],
) -> str | None:
    url = paper.queue_url()
    if url is None:
        return "missing arXiv URL"

    if url.rstrip("/") in urls:
        return "url already in queue"

    if paper.arxiv_id and paper.arxiv_id in arxiv_ids:
        return "arXiv id already in queue"

    if paper.title.strip().lower() in titles:
        return "title already in queue"

    return None


def import_conference_papers(
    papers_file: Path,
    conference_slug: str,
    *,
    presentation: PresentationFilter = "all",
    client: PapersWithCodeClient | None = None,
    dry_run: bool = False,
) -> ImportConferenceResult:
    """Fetch conference papers and append new ones to ``papers.yaml``.

    Args:
        papers_file: Path to ``papers.yaml``.
        conference_slug: Conference slug such as ``cvpr-2026``.
        presentation: Optional presentation filter (``oral``, ``spotlight``, etc.).
        client: Optional API client for tests.
        dry_run: When True, report additions without writing ``papers.yaml``.

    Returns:
        Import summary with added and skipped papers.
    """
    owns_client = client is None
    api = client or PapersWithCodeClient()

    try:
        papers = list(
            api.iter_conference_papers(
                conference_slug,
                presentation=presentation,
            ),
        )
        entries = load_paper_queue(papers_file)
        urls, arxiv_ids, titles = _queue_index(entries)

        added: list[ImportAddedPaper] = []
        skipped: list[ImportSkippedPaper] = []

        for paper in papers:
            url = paper.queue_url()
            if url is None:
                skipped.append(
                    ImportSkippedPaper(
                        title=paper.title,
                        url="",
                        reason="missing arXiv URL",
                    ),
                )
                continue

            reason = _is_already_queued(
                paper,
                urls=urls,
                arxiv_ids=arxiv_ids,
                titles=titles,
            )
            if reason is not None:
                skipped.append(
                    ImportSkippedPaper(
                        title=paper.title,
                        url=url,
                        reason=reason,
                    ),
                )
                continue

            slug = paper.queue_slug()
            if dry_run:
                added.append(ImportAddedPaper(title=paper.title, url=url, slug=slug or ""))
            else:
                entry = add_paper_to_queue(
                    papers_file,
                    url=url,
                    slug=slug,
                    title=paper.title,
                )
                added.append(
                    ImportAddedPaper(
                        title=entry.title or paper.title,
                        url=entry.url,
                        slug=entry.resolve_slug(),
                    ),
                )

            urls.add(url.rstrip("/"))
            if paper.arxiv_id:
                arxiv_ids.add(paper.arxiv_id)
            titles.add(paper.title.strip().lower())

        return ImportConferenceResult(
            conference_slug=conference_slug,
            presentation=presentation,
            fetched=len(papers),
            added=tuple(added),
            skipped=tuple(skipped),
        )
    finally:
        if owns_client:
            api.close()
