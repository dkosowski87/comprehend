"""Tests for GitHub wiki helpers."""

from pathlib import Path

from comprehend.publish.github_wiki import _update_engineering_index, _update_papers_index


def test_update_papers_index_creates_page(tmp_path: Path) -> None:
    _update_papers_index(
        wiki_dir=tmp_path,
        slug="arxiv-2304-08069",
        title="Example Paper",
        tags=["transformer", "efficiency"],
    )

    content = (tmp_path / "Papers.md").read_text(encoding="utf-8")

    assert content.startswith("# Papers\n\n")
    assert "[Example Paper](arxiv-2304-08069)" in content
    assert "`transformer`, `efficiency`" in content


def test_update_papers_index_skips_duplicate_slug(tmp_path: Path) -> None:
    papers_path = tmp_path / "Papers.md"
    papers_path.write_text(
        "# Papers\n\n- [Example Paper](arxiv-2304-08069) — `transformer` — 2026-01-01\n",
        encoding="utf-8",
    )

    _update_papers_index(
        wiki_dir=tmp_path,
        slug="arxiv-2304-08069",
        title="Renamed Title",
        tags=["other"],
    )

    content = papers_path.read_text(encoding="utf-8")

    assert content.count("arxiv-2304-08069") == 1
    assert "Renamed Title" not in content


def test_update_engineering_index_creates_page(tmp_path: Path) -> None:
    _update_engineering_index(
        wiki_dir=tmp_path,
        slug="engineering-pytorch-cuda-semantics",
        title="PyTorch CUDA Semantics",
        topic="pytorch",
        tags=["pytorch", "cuda"],
    )

    content = (tmp_path / "Engineering.md").read_text(encoding="utf-8")

    assert content.startswith("# Engineering\n\n")
    assert "[PyTorch CUDA Semantics](engineering-pytorch-cuda-semantics)" in content
    assert "`pytorch`" in content
