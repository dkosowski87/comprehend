"""Tests for paper queue loading."""

import json
from pathlib import Path
from types import SimpleNamespace

import yaml
from click.testing import CliRunner

from comprehend import cli
from comprehend.queue import (
    PaperQueueEntry,
    add_paper_to_queue,
    find_paper_entry,
    load_paper_queue,
)


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
    )

    assert entry.resolve_slug() == "arxiv-2103-14030"


def test_add_paper_to_queue(tmp_path: Path) -> None:
    papers_file = tmp_path / "papers.yaml"
    papers_file.write_text(
        "papers:\n"
        "  - url: https://arxiv.org/abs/2012.12877\n"
        "    slug: arxiv-2012-12877\n"
        "    title: DeiT\n",
        encoding="utf-8",
    )

    entry = add_paper_to_queue(
        papers_file,
        url="https://arxiv.org/abs/9999.99999",
        slug="arxiv-9999-99999",
        title="Test Paper",
    )

    assert entry.resolve_slug() == "arxiv-9999-99999"
    reloaded = load_paper_queue(papers_file)
    assert len(reloaded) == 2


def test_queue_next_prepares_pending_paper(tmp_path: Path, monkeypatch) -> None:
    papers_file = tmp_path / "papers.yaml"
    cache_root = tmp_path / "cache"
    paper_cache = cache_root / "arxiv-9999-99999"
    papers_file.write_text(
        "papers:\n"
        "  - url: https://arxiv.org/abs/9999.99999\n"
        "    slug: arxiv-9999-99999\n"
        "    title: Test Paper\n",
        encoding="utf-8",
    )

    prepared = SimpleNamespace(
        pdf_url="https://arxiv.org/pdf/9999.99999.pdf",
        title="Prepared Test Paper",
        cache_dir=paper_cache,
        pdf_path=paper_cache / "paper.pdf",
        figures_json_path=paper_cache / "figures.json",
        extracted=SimpleNamespace(text_path=paper_cache / "text.txt"),
    )

    monkeypatch.setattr(cli, "_sync_wiki_for_status", lambda config: None)
    monkeypatch.setattr(cli, "default_cache_dir", lambda: cache_root)
    monkeypatch.setattr(cli, "prepare_paper", lambda *args, **kwargs: prepared)

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        [
            "queue",
            "next",
            "--papers-file",
            str(papers_file),
            "--repo",
            "owner/repo",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["slug"] == "arxiv-9999-99999"
    assert payload["title"] == "Prepared Test Paper"
    assert payload["text_path"] == str(paper_cache / "text.txt")
