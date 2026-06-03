"""Concept prepare workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from comprehend.concept.linkify import paper_links_to_concept
from comprehend.pdf.download import paper_cache_dir
from comprehend.publish.github_wiki import WikiConfig, wiki_page_exists
from comprehend.queue import find_concept_ref, find_paper_entry, load_paper_queue
from comprehend.summary.schema import load_summary
from comprehend.util import (
    concept_cache_dir,
    concept_display_name,
    concept_wiki_slug,
    default_cache_dir,
)


class ConceptPrepareError(Exception):
    """Raised when concept preparation cannot proceed."""


@dataclass(frozen=True)
class PreparedConcept:
    """Local artifacts and metadata for a concept run."""

    concept_id: str
    concept_slug: str
    concept_name: str
    terms: list[str]
    paper_slug: str
    paper_title: str | None
    paper_url: str
    paper_tags: list[str]
    cache_dir: Path
    concept_json_path: Path
    paper_summary_path: Path | None
    paper_wiki_path: Path | None
    concept_already_published: bool
    paper_published: bool
    paper_already_links_concept: bool


def prepare_concept(
    *,
    paper_slug: str,
    concept_id: str,
    papers_file: Path,
    wiki_config: WikiConfig,
    cache_root: Path | None = None,
) -> PreparedConcept:
    """Validate prerequisites and paths for a concept explanation run.

    Args:
        paper_slug: Published paper wiki slug.
        concept_id: Concept id from ``papers.yaml``.
        papers_file: Path to ``papers.yaml``.
        wiki_config: Wiki configuration.
        cache_root: Optional cache root override.

    Returns:
        Prepared concept metadata for agent work.

    Raises:
        ConceptPrepareError: If prerequisites are missing.
    """
    if not papers_file.is_file():
        raise ConceptPrepareError(f"Papers file not found: {papers_file}")

    entries = load_paper_queue(papers_file)
    paper_entry = find_paper_entry(entries, paper_slug=paper_slug)
    if paper_entry is None:
        raise ConceptPrepareError(
            f"Paper slug '{paper_slug}' not found in {papers_file}",
        )

    concept_ref = find_concept_ref(paper_entry, concept_id=concept_id)
    if concept_ref is None:
        raise ConceptPrepareError(
            f"Concept '{concept_id}' not declared for paper '{paper_slug}' in {papers_file}",
        )

    cache = cache_root or default_cache_dir()
    concept_slug = concept_wiki_slug(concept_id)
    concept_dir = concept_cache_dir(concept_id, cache_root=cache)
    concept_json_path = concept_dir / "concept.json"

    if not wiki_config.wiki_dir.is_dir():
        raise ConceptPrepareError(
            "Wiki checkout not found. Run a wiki command first or publish a paper summary.",
        )

    paper_published = wiki_page_exists(paper_slug, wiki_dir=wiki_config.wiki_dir)
    if not paper_published:
        raise ConceptPrepareError(
            f"Paper wiki page '{paper_slug}' must exist before adding concepts. "
            "Publish the paper summary first.",
        )

    paper_wiki_path = wiki_config.wiki_dir / f"{paper_slug}.md"
    wiki_text = paper_wiki_path.read_text(encoding="utf-8")
    paper_already_links_concept = paper_links_to_concept(
        wiki_text,
        concept_slug=concept_slug,
    )

    paper_cache = paper_cache_dir(paper_entry.url, cache_root=cache, slug=paper_slug)
    summary_path = paper_cache / "summary.json"
    paper_summary_path: Path | None = None
    paper_title = paper_entry.title
    if summary_path.is_file():
        paper_summary_path = summary_path
        if paper_title is None:
            paper_title = load_summary(summary_path).title

    concept_already_published = wiki_page_exists(
        concept_slug,
        wiki_dir=wiki_config.wiki_dir,
    )

    prepared = PreparedConcept(
        concept_id=concept_id,
        concept_slug=concept_slug,
        concept_name=concept_display_name(concept_id),
        terms=list(concept_ref.terms),
        paper_slug=paper_slug,
        paper_title=paper_title,
        paper_url=paper_entry.url,
        paper_tags=list(paper_entry.tags),
        cache_dir=concept_dir,
        concept_json_path=concept_json_path,
        paper_summary_path=paper_summary_path,
        paper_wiki_path=paper_wiki_path,
        concept_already_published=concept_already_published,
        paper_published=paper_published,
        paper_already_links_concept=paper_already_links_concept,
    )

    return prepared
