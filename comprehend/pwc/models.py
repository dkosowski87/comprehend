"""Pydantic models for paperswithcode.co API responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PresentationFilter = Literal["oral", "spotlight", "outstanding", "all"]


class Conference(BaseModel):
    """Conference metadata from paperswithcode.co."""

    id: str
    name: str
    slug: str
    short_name: str | None = None
    year: int | None = None
    url: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    venue: str | None = None
    location: str | None = None
    description: str | None = None
    paper_count: int | None = None


class ConferencePaper(BaseModel):
    """One paper listed under a conference proceeding."""

    id: str
    title: str
    arxiv_id: str | None = None
    url_abs: str | None = None
    url_pdf: str | None = None
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    presentation: str | None = None

    def queue_url(self) -> str | None:
        """Return an arXiv abstract URL suitable for ``papers.yaml``."""
        if self.url_abs:
            return self.url_abs.rstrip("/")

        if self.arxiv_id:
            return f"https://arxiv.org/abs/{self.arxiv_id}"

        return None

    def queue_slug(self) -> str | None:
        """Return a wiki slug when an arXiv id is available."""
        if not self.arxiv_id:
            return None

        safe_id = self.arxiv_id.replace(".", "-")

        return f"arxiv-{safe_id}"


class PaginatedConferences(BaseModel):
    """Paginated conference list."""

    count: int
    next_page: int | None = None
    previous_page: int | None = None
    results: list[Conference]


class PaginatedConferencePapers(BaseModel):
    """Paginated conference paper list."""

    count: int
    next_page: int | None = None
    previous_page: int | None = None
    results: list[ConferencePaper]
