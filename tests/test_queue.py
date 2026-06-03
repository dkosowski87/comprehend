"""Tests for paper queue loading."""

from pathlib import Path

import yaml

from comprehend.queue import PaperQueueEntry, find_paper_entry, load_paper_queue


def test_load_paper_queue_slug_and_title(tmp_path: Path) -> None:
    papers_file = tmp_path / "papers.yaml"
    papers_file.write_text(
        yaml.dump(
            {
                "papers": [
                    {
                        "url": "https://arxiv.org/abs/2304.08069",
                        "slug": "arxiv-2304-08069",
                        "title": "DETRs Beat YOLOs on Real-time Object Detection",
                        "tags": ["vision"],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    entries = load_paper_queue(papers_file)

    assert len(entries) == 1
    assert entries[0].slug == "arxiv-2304-08069"
    assert entries[0].title == "DETRs Beat YOLOs on Real-time Object Detection"
    assert entries[0].resolve_slug() == "arxiv-2304-08069"


def test_find_paper_entry_by_explicit_slug(tmp_path: Path) -> None:
    papers_file = tmp_path / "papers.yaml"
    papers_file.write_text(
        yaml.dump(
            {
                "papers": [
                    {
                        "url": "https://arxiv.org/abs/2304.08069",
                        "slug": "arxiv-2304-08069",
                        "title": "RT-DETR",
                        "tags": [],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    entries = load_paper_queue(papers_file)
    found = find_paper_entry(entries, paper_slug="arxiv-2304-08069")

    assert found is not None
    assert isinstance(found, PaperQueueEntry)


def test_resolve_slug_falls_back_to_url(tmp_path: Path) -> None:
    entry = PaperQueueEntry(
        url="https://arxiv.org/abs/2103.14030",
        tags=[],
        concepts=[],
    )

    assert entry.resolve_slug() == "arxiv-2103-14030"
