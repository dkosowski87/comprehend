"""HTTP client for the paperswithcode.co public API."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from comprehend.pwc.models import (
    Conference,
    ConferencePaper,
    PaginatedConferencePapers,
    PaginatedConferences,
    PresentationFilter,
)

DEFAULT_BASE_URL = "https://paperswithcode.co/api/v1"
DEFAULT_ITEMS_PER_PAGE = 100


class PapersWithCodeError(RuntimeError):
    """Raised when the paperswithcode.co API returns an error."""


class PapersWithCodeClient:
    """Client for paperswithcode.co conference and paper listings."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": "comprehend/0.1 (+https://github.com/dkosowski87/comprehend)",
            },
        )

    def close(self) -> None:
        """Close the underlying HTTP client when owned by this instance."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> PapersWithCodeClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        response = self._client.get(path, params=params)
        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise PapersWithCodeError(
                f"paperswithcode.co API error {response.status_code} for {path}: {detail}",
            )

        return response.json()

    def list_conferences(
        self,
        *,
        page: int = 1,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
    ) -> PaginatedConferences:
        """List conferences tracked on paperswithcode.co."""
        payload = self._get(
            "/conferences",
            params={"page": page, "items_per_page": items_per_page},
        )

        return PaginatedConferences.model_validate(payload)

    def get_conference(self, conference_slug: str) -> Conference:
        """Fetch metadata for one conference."""
        payload = self._get(f"/conferences/{conference_slug}")

        return Conference.model_validate(payload)

    def list_conference_papers(
        self,
        conference_slug: str,
        *,
        presentation: PresentationFilter = "all",
        page: int = 1,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
    ) -> PaginatedConferencePapers:
        """List papers accepted to a conference proceeding."""
        params: dict[str, Any] = {
            "page": page,
            "items_per_page": items_per_page,
        }
        if presentation != "all":
            params["presentation"] = presentation

        payload = self._get(
            f"/conferences/{conference_slug}/papers",
            params=params,
        )

        return PaginatedConferencePapers.model_validate(payload)

    def iter_conference_papers(
        self,
        conference_slug: str,
        *,
        presentation: PresentationFilter = "all",
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
    ) -> Iterator[ConferencePaper]:
        """Yield every paper for a conference, following pagination."""
        page = 1
        while True:
            batch = self.list_conference_papers(
                conference_slug,
                presentation=presentation,
                page=page,
                items_per_page=items_per_page,
            )
            yield from batch.results

            if batch.next_page is None:
                break

            page = batch.next_page
