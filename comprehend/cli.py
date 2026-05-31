"""Comprehend command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from comprehend.pdf.download import PaperDownloadError
from comprehend.pdf.extract import extract_figure_by_xref, extract_paper, render_page_region
from comprehend.prepare import prepare_paper
from comprehend.publish.github_wiki import WikiConfig, WikiPublishError, ensure_wiki_checkout, publish_wiki_page, wiki_page_exists
from comprehend.queue import (
    QueueStatus,
    load_paper_queue,
    next_pending_item,
    prepare_queue_entry,
    queue_items,
)
from comprehend.render.manim_render import render_manim_scene
from comprehend.render.mermaid_render import render_mermaid
from comprehend.render.visuals import VisualRenderError, render_summary_visuals
from comprehend.summary.schema import load_summary, render_markdown, save_summary
from comprehend.util import default_cache_dir, default_repo_from_git


def _wiki_config(repo: str | None, wiki_dir: Path | None) -> WikiConfig:
    resolved_repo = repo or default_repo_from_git()
    if resolved_repo is None:
        raise click.ClickException(
            "Could not infer GitHub repo. Pass --repo owner/name.",
        )

    cache_root = default_cache_dir()
    resolved_wiki_dir = wiki_dir or (cache_root / "wiki" / resolved_repo.replace("/", "-"))

    config = WikiConfig(repo=resolved_repo, wiki_dir=resolved_wiki_dir)

    return config


def _sync_wiki_for_status(config: WikiConfig) -> None:
    try:
        ensure_wiki_checkout(config)
    except WikiPublishError:
        pass


@click.group()
@click.version_option(package_name="comprehend")
def main() -> None:
    """ML paper summaries with visuals for GitHub wiki publishing."""


@main.group()
def pdf() -> None:
    """PDF download and extraction commands."""


@pdf.command("download")
@click.argument("url")
@click.option(
    "--cache-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for paper.pdf",
)
def pdf_download(url: str, cache_dir: Path | None) -> None:
    """Download a paper PDF from arXiv or a direct PDF URL."""
    cache_root = default_cache_dir()

    try:
        prepared = prepare_paper(
            url,
            cache_root=cache_root,
            slug=cache_dir.name if cache_dir is not None else None,
        )
    except PaperDownloadError as exc:
        raise click.ClickException(str(exc)) from exc

    payload = {
        "pdf_path": str(prepared.pdf_path),
        "cache_dir": str(prepared.cache_dir),
        "slug": prepared.slug,
        "pdf_url": prepared.pdf_url,
        "title": prepared.title,
    }
    click.echo(json.dumps(payload, indent=2))


@pdf.command("extract")
@click.argument("pdf_path", type=click.Path(path_type=Path, exists=True))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory for text.txt and figure metadata",
)
def pdf_extract(pdf_path: Path, output_dir: Path | None) -> None:
    """Extract text and figure catalog from a local PDF."""
    target_dir = output_dir or pdf_path.parent
    extracted = extract_paper(pdf_path, output_dir=target_dir)

    payload = {
        "text_path": str(extracted.text_path),
        "page_count": extracted.page_count,
        "figure_count": len(extracted.figures),
    }
    click.echo(json.dumps(payload, indent=2))


@pdf.command("crop")
@click.argument("pdf_path", type=click.Path(path_type=Path, exists=True))
@click.option(
    "--page",
    type=int,
    required=True,
    help="1-based page number",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output PNG path",
)
@click.option(
    "--xref",
    type=int,
    default=None,
    help="Extract embedded image by xref instead of rendering page",
)
@click.option(
    "--clip",
    nargs=4,
    type=float,
    default=None,
    help="Clip rectangle: x0 y0 x1 y1",
)
def pdf_crop(
    pdf_path: Path,
    page: int,
    output: Path,
    xref: int | None,
    clip: tuple[float, float, float, float] | None,
) -> None:
    """Extract a figure from a PDF page or by xref."""
    if xref is not None:
        rendered = extract_figure_by_xref(pdf_path, xref, output_path=output)
    else:
        rendered = render_page_region(
            pdf_path,
            page=page,
            output_path=output,
            clip=clip,
        )

    click.echo(str(rendered))


@main.command("prepare")
@click.argument("url")
@click.option(
    "--repo",
    default=None,
    help="GitHub repo owner/name for wiki deduplication",
)
@click.option(
    "--wiki-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Local wiki checkout path",
)
@click.option(
    "--slug",
    default=None,
    help="Explicit wiki slug override",
)
def prepare_cmd(
    url: str,
    repo: str | None,
    wiki_dir: Path | None,
    slug: str | None,
) -> None:
    """Download, extract, and report whether the paper is already on the wiki."""
    cache_root = default_cache_dir()
    config = _wiki_config(repo, wiki_dir)
    _sync_wiki_for_status(config)

    try:
        prepared = prepare_paper(url, cache_root=cache_root, slug=slug)
    except PaperDownloadError as exc:
        raise click.ClickException(str(exc)) from exc

    if config.wiki_dir.is_dir():
        already_published = wiki_page_exists(prepared.slug, wiki_dir=config.wiki_dir)
    else:
        already_published = False

    payload = {
        "url": prepared.url,
        "slug": prepared.slug,
        "pdf_url": prepared.pdf_url,
        "title": prepared.title,
        "cache_dir": str(prepared.cache_dir),
        "pdf_path": str(prepared.pdf_path),
        "text_path": str(prepared.extracted.text_path),
        "figures_path": str(prepared.figures_json_path),
        "already_published": already_published,
        "wiki_repo": config.repo,
    }
    click.echo(json.dumps(payload, indent=2))

    if already_published:
        sys.exit(0)


@main.group()
def render() -> None:
    """Visual rendering commands."""


@render.command("mermaid")
@click.argument("source_file", type=click.Path(path_type=Path, exists=True))
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output PNG path",
)
def render_mermaid_cmd(source_file: Path, output: Path) -> None:
    """Render a Mermaid diagram file to PNG."""
    source = source_file.read_text(encoding="utf-8")
    rendered = render_mermaid(source, output_path=output)
    click.echo(str(rendered))


@render.command("manim")
@click.argument("scene_file", type=click.Path(path_type=Path, exists=True))
@click.option(
    "--scene-class",
    required=True,
    help="Manim Scene class name",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output PNG path",
)
def render_manim_cmd(scene_file: Path, scene_class: str, output: Path) -> None:
    """Render a Manim scene to a static PNG."""
    rendered = render_manim_scene(
        scene_file,
        scene_name=scene_class,
        output_path=output,
    )
    click.echo(str(rendered))


@render.command("summary")
@click.argument("summary_json", type=click.Path(path_type=Path, exists=True))
@click.option(
    "--pdf-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Source PDF for extract visuals",
)
@click.option(
    "--assets-dir",
    type=click.Path(path_type=Path),
    required=True,
    help="Directory for rendered PNG assets",
)
def render_summary_cmd(
    summary_json: Path,
    pdf_path: Path | None,
    assets_dir: Path,
) -> None:
    """Render all visuals defined in a summary JSON file."""
    summary = load_summary(summary_json)

    try:
        rendered = render_summary_visuals(
            summary,
            output_dir=assets_dir,
            pdf_path=pdf_path,
        )
    except VisualRenderError as exc:
        raise click.ClickException(str(exc)) from exc

    save_summary(summary, summary_json)
    payload = {visual_id: str(path) for visual_id, path in rendered.items()}
    click.echo(json.dumps(payload, indent=2))


@main.command("assemble")
@click.argument("summary_json", type=click.Path(path_type=Path, exists=True))
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output markdown path",
)
def assemble_cmd(summary_json: Path, output: Path) -> None:
    """Assemble wiki markdown from a summary JSON file."""
    summary = load_summary(summary_json)
    markdown = render_markdown(summary)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    click.echo(str(output))


@main.group()
def wiki() -> None:
    """GitHub wiki commands."""


@wiki.command("exists")
@click.argument("slug")
@click.option(
    "--repo",
    default=None,
    help="GitHub repo owner/name",
)
@click.option(
    "--wiki-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Local wiki checkout path",
)
def wiki_exists(slug: str, repo: str | None, wiki_dir: Path | None) -> None:
    """Check whether a wiki page exists."""
    config = _wiki_config(repo, wiki_dir)

    if not config.wiki_dir.is_dir():
        click.echo("false")
        return

    exists = wiki_page_exists(slug, wiki_dir=config.wiki_dir)
    click.echo("true" if exists else "false")


@wiki.command("publish")
@click.argument("summary_json", type=click.Path(path_type=Path, exists=True))
@click.option(
    "--assets-dir",
    type=click.Path(path_type=Path),
    required=True,
    help="Directory containing rendered PNG assets",
)
@click.option(
    "--repo",
    default=None,
    help="GitHub repo owner/name",
)
@click.option(
    "--wiki-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Local wiki checkout path",
)
@click.option(
    "--skip-if-exists/--force",
    default=True,
    show_default=True,
    help="Skip publishing when the wiki page already exists",
)
def wiki_publish(
    summary_json: Path,
    assets_dir: Path,
    repo: str | None,
    wiki_dir: Path | None,
    skip_if_exists: bool,
) -> None:
    """Publish a summary JSON and assets to the GitHub wiki."""
    summary = load_summary(summary_json)
    config = _wiki_config(repo, wiki_dir)

    if skip_if_exists and config.wiki_dir.is_dir():
        if wiki_page_exists(summary.slug, wiki_dir=config.wiki_dir):
            click.echo(f"Skipped: wiki page already exists for slug '{summary.slug}'")
            return

    markdown = render_markdown(summary)
    assets: dict[str, Path] = {}

    for visual in summary.visuals:
        asset_name = visual.asset_filename
        if asset_name is None:
            raise click.ClickException(
                f"Visual {visual.id} has no asset_filename; run render summary first",
            )

        asset_path = assets_dir / asset_name
        if not asset_path.is_file():
            raise click.ClickException(f"Missing asset: {asset_path}")

        assets[asset_name] = asset_path

    try:
        page_path = publish_wiki_page(
            slug=summary.slug,
            markdown=markdown,
            assets=assets,
            config=config,
            title=summary.title,
            tags=summary.tags,
        )
    except WikiPublishError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(page_path)


@main.group()
def queue() -> None:
    """Paper queue commands."""


@queue.command("status")
@click.option(
    "--papers-file",
    type=click.Path(path_type=Path),
    default="papers.yaml",
    show_default=True,
    help="Path to papers.yaml",
)
@click.option(
    "--repo",
    default=None,
    help="GitHub repo owner/name",
)
@click.option(
    "--wiki-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Local wiki checkout path",
)
def queue_status(
    papers_file: Path,
    repo: str | None,
    wiki_dir: Path | None,
) -> None:
    """Show pending and published papers from papers.yaml."""
    if not papers_file.is_file():
        raise click.ClickException(f"Papers file not found: {papers_file}")

    config = _wiki_config(repo, wiki_dir)
    _sync_wiki_for_status(config)
    entries = load_paper_queue(papers_file)
    items = queue_items(entries, wiki_config=config)

    payload = [
        {
            "url": item.url,
            "slug": item.slug,
            "tags": item.tags,
            "status": item.status.value,
        }
        for item in items
    ]
    click.echo(json.dumps(payload, indent=2))


@queue.command("next")
@click.option(
    "--papers-file",
    type=click.Path(path_type=Path),
    default="papers.yaml",
    show_default=True,
    help="Path to papers.yaml",
)
@click.option(
    "--repo",
    default=None,
    help="GitHub repo owner/name",
)
@click.option(
    "--wiki-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Local wiki checkout path",
)
@click.option(
    "--prepare/--no-prepare",
    default=True,
    show_default=True,
    help="Download and extract the next pending paper",
)
def queue_next(
    papers_file: Path,
    repo: str | None,
    wiki_dir: Path | None,
    prepare: bool,
) -> None:
    """Return the next pending paper and optionally prepare local artifacts."""
    if not papers_file.is_file():
        raise click.ClickException(f"Papers file not found: {papers_file}")

    config = _wiki_config(repo, wiki_dir)
    _sync_wiki_for_status(config)
    entries = load_paper_queue(papers_file)
    items = queue_items(entries, wiki_config=config)
    pending = next_pending_item(items)

    if pending is None:
        click.echo(json.dumps({"status": "empty"}, indent=2))
        return

    payload: dict[str, object] = {
        "url": pending.url,
        "slug": pending.slug,
        "tags": pending.tags,
        "status": pending.status.value,
    }

    if prepare:
        try:
            prepared = prepare_paper(pending.url, cache_root=default_cache_dir())
        except PaperDownloadError as exc:
            raise click.ClickException(str(exc)) from exc

        payload.update(
            {
                "pdf_url": prepared.pdf_url,
                "title": prepared.title,
                "cache_dir": str(prepared.cache_dir),
                "pdf_path": str(prepared.pdf_path),
                "text_path": str(prepared.extracted.text_path),
                "figures_path": str(prepared.figures_json_path),
            },
        )

    click.echo(json.dumps(payload, indent=2))


@queue.command("run")
@click.option(
    "--papers-file",
    type=click.Path(path_type=Path),
    default="papers.yaml",
    show_default=True,
    help="Path to papers.yaml",
)
@click.option(
    "--repo",
    default=None,
    help="GitHub repo owner/name",
)
@click.option(
    "--wiki-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Local wiki checkout path",
)
def queue_run(
    papers_file: Path,
    repo: str | None,
    wiki_dir: Path | None,
) -> None:
    """Prepare all pending papers and list those needing agent summarization."""
    if not papers_file.is_file():
        raise click.ClickException(f"Papers file not found: {papers_file}")

    config = _wiki_config(repo, wiki_dir)
    _sync_wiki_for_status(config)
    entries = load_paper_queue(papers_file)
    items = queue_items(entries, wiki_config=config)
    pending_items = [item for item in items if item.status == QueueStatus.PENDING]

    prepared_items: list[dict[str, object]] = []
    for item in pending_items:
        try:
            cache_dir = prepare_queue_entry(item)
        except PaperDownloadError as exc:
            prepared_items.append(
                {
                    "url": item.url,
                    "slug": item.slug,
                    "tags": item.tags,
                    "error": str(exc),
                },
            )
            continue

        prepared_items.append(
            {
                "url": item.url,
                "slug": item.slug,
                "tags": item.tags,
                "cache_dir": str(cache_dir),
            },
        )

    payload = {
        "pending_count": len(pending_items),
        "papers": prepared_items,
    }
    click.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
