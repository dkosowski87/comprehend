"""Tests for paperswithcode.co client and queue import."""

from __future__ import annotations

from pathlib import Path

import httpx
import yaml

from comprehend.pwc.client import PapersWithCodeClient
from comprehend.pwc.import_queue import import_conference_papers
from comprehend.queue import load_paper_queue


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/conferences/cvpr-2026/papers"):
            page = int(request.url.params.get("page", "1"))
            presentation = request.url.params.get("presentation")
            if presentation == "oral" and page == 1:
                return httpx.Response(
                    200,
                    json={
                        "count": 2,
                        "next_page": 2,
                        "previous_page": None,
                        "results": [
                            {
                                "id": "1",
                                "title": "Oral One",
                                "arxiv_id": "2605.11111",
                                "url_abs": "https://arxiv.org/abs/2605.11111",
                            },
                            {
                                "id": "2",
                                "title": "Oral Two",
                                "arxiv_id": "2605.22222",
                                "url_abs": "https://arxiv.org/abs/2605.22222",
                            },
                        ],
                    },
                )
            if presentation == "oral" and page == 2:
                return httpx.Response(
                    200,
                    json={
                        "count": 2,
                        "next_page": None,
                        "previous_page": 1,
                        "results": [
                            {
                                "id": "3",
                                "title": "Oral Three",
                                "arxiv_id": "2605.33333",
                                "url_abs": "https://arxiv.org/abs/2605.33333",
                            },
                        ],
                    },
                )

        return httpx.Response(404, json={"detail": "Not Found"})

    return httpx.MockTransport(handler)


def test_iter_conference_papers_follows_pagination() -> None:
    transport = _mock_transport()
    http_client = httpx.Client(
        base_url="https://paperswithcode.co/api/v1",
        transport=transport,
    )
    client = PapersWithCodeClient(client=http_client)

    papers = list(client.iter_conference_papers("cvpr-2026", presentation="oral"))

    assert [paper.title for paper in papers] == [
        "Oral One",
        "Oral Two",
        "Oral Three",
    ]
    client.close()


def test_import_conference_papers_skips_existing(tmp_path: Path) -> None:
    papers_file = tmp_path / "papers.yaml"
    papers_file.write_text(
        yaml.dump(
            {
                "papers": [
                    {
                        "url": "https://arxiv.org/abs/2605.11111",
                        "slug": "arxiv-2605-11111",
                        "title": "Already Queued",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    transport = _mock_transport()
    http_client = httpx.Client(
        base_url="https://paperswithcode.co/api/v1",
        transport=transport,
    )
    client = PapersWithCodeClient(client=http_client)

    result = import_conference_papers(
        papers_file,
        "cvpr-2026",
        presentation="oral",
        client=client,
    )

    assert result.fetched == 3
    assert result.added_count == 2
    assert result.skipped_count == 1
    assert result.skipped[0].title == "Oral One"
    assert "already in queue" in result.skipped[0].reason

    entries = load_paper_queue(papers_file)
    assert len(entries) == 3
    assert entries[-1].resolve_slug() == "arxiv-2605-33333"

    client.close()


def test_import_conference_papers_dry_run(tmp_path: Path) -> None:
    papers_file = tmp_path / "papers.yaml"
    papers_file.write_text("papers: []\n", encoding="utf-8")

    transport = _mock_transport()
    http_client = httpx.Client(
        base_url="https://paperswithcode.co/api/v1",
        transport=transport,
    )
    client = PapersWithCodeClient(client=http_client)

    result = import_conference_papers(
        papers_file,
        "cvpr-2026",
        presentation="oral",
        client=client,
        dry_run=True,
    )

    assert result.added_count == 3
    assert load_paper_queue(papers_file) == []

    client.close()
