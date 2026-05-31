"""GitHub wiki clone, deduplication, and publishing."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class WikiPublishError(Exception):
    """Raised when wiki operations fail."""


@dataclass(frozen=True)
class WikiConfig:
    """Configuration for a GitHub wiki repository."""

    repo: str
    wiki_dir: Path


def wiki_remote_url(repo: str) -> str:
    """Build the SSH clone URL for a GitHub wiki repository.

    Args:
        repo: Repository slug ``owner/name``.

    Returns:
        Wiki git remote URL.
    """
    return f"git@github.com:{repo}.wiki.git"


def ensure_wiki_checkout(
    config: WikiConfig,
    *,
    clone_if_missing: bool = True,
) -> Path:
    """Ensure the wiki repository exists locally.

    Args:
        config: Wiki configuration.
        clone_if_missing: Clone the wiki when the local directory is absent.

    Returns:
        Path to the wiki working tree.

    Raises:
        WikiPublishError: If clone or update fails.
    """
    if config.wiki_dir.is_dir() and (config.wiki_dir / ".git").is_dir():
        _run_git(["pull", "--ff-only"], cwd=config.wiki_dir)

        return config.wiki_dir

    if not clone_if_missing:
        raise WikiPublishError(
            f"Wiki checkout not found: {config.wiki_dir}",
        )

    config.wiki_dir.parent.mkdir(parents=True, exist_ok=True)
    remote = wiki_remote_url(config.repo)

    try:
        _run_git(
            ["clone", remote, str(config.wiki_dir)],
        )
    except WikiPublishError as exc:
        raise WikiPublishError(
            f"Failed to clone wiki for {config.repo}. "
            "Enable the wiki in repository settings and ensure SSH access.",
        ) from exc

    return config.wiki_dir


def wiki_page_exists(slug: str, *, wiki_dir: Path) -> bool:
    """Check whether a wiki page already exists.

    Args:
        slug: Page slug without ``.md`` suffix.
        wiki_dir: Local wiki checkout path.

    Returns:
        ``True`` when ``{slug}.md`` exists in the wiki repo.
    """
    page_path = wiki_dir / f"{slug}.md"

    return page_path.is_file()


def publish_wiki_page(
    *,
    slug: str,
    markdown: str,
    assets: dict[str, Path],
    config: WikiConfig,
    title: str,
    tags: list[str],
) -> str:
    """Publish or update a wiki page and its assets.

    Args:
        slug: Wiki page slug.
        markdown: Page markdown body.
        assets: Mapping of asset filename to local PNG path.
        config: Wiki configuration.
        title: Paper title for the index page.
        tags: Paper tags for the index page.

    Returns:
        Published wiki page URL path (without domain).

    Raises:
        WikiPublishError: If git operations fail.
    """
    wiki_dir = ensure_wiki_checkout(config)
    page_path = wiki_dir / f"{slug}.md"
    assets_dir = wiki_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    page_path.write_text(markdown, encoding="utf-8")

    for asset_name, asset_path in assets.items():
        if not asset_path.is_file():
            raise WikiPublishError(f"Asset not found: {asset_path}")

        destination = assets_dir / asset_name
        destination.write_bytes(asset_path.read_bytes())

    _update_home_index(
        wiki_dir=wiki_dir,
        slug=slug,
        title=title,
        tags=tags,
    )

    _run_git(["add", page_path.name, "assets", "Home.md"], cwd=wiki_dir)

    if _git_has_changes(wiki_dir):
        message = f"Add summary: {title}"
        _run_git(["commit", "-m", message], cwd=wiki_dir)
        _run_git(["push", "origin", "HEAD"], cwd=wiki_dir)

    page_url_path = f"/{config.repo}/wiki/{slug}"

    return page_url_path


def publish_concept_page(
    *,
    slug: str,
    markdown: str,
    assets: dict[str, Path],
    config: WikiConfig,
    name: str,
    tags: list[str],
) -> str:
    """Publish a concept wiki page and its assets.

    Args:
        slug: Concept wiki slug such as ``concept-cyclic-shift``.
        markdown: Concept page markdown body.
        assets: Mapping of asset filename to local PNG path.
        config: Wiki configuration.
        name: Concept display name for the index page.
        tags: Concept tags for the index page.

    Returns:
        Published wiki page URL path (without domain).

    Raises:
        WikiPublishError: If git operations fail.
    """
    wiki_dir = ensure_wiki_checkout(config)
    page_path = wiki_dir / f"{slug}.md"
    assets_dir = wiki_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    page_path.write_text(markdown, encoding="utf-8")

    for asset_name, asset_path in assets.items():
        if not asset_path.is_file():
            raise WikiPublishError(f"Asset not found: {asset_path}")

        destination = assets_dir / asset_name
        destination.write_bytes(asset_path.read_bytes())

    _update_concepts_index(
        wiki_dir=wiki_dir,
        slug=slug,
        name=name,
        tags=tags,
    )

    _run_git(["add", page_path.name, "assets", "Concepts.md"], cwd=wiki_dir)

    if _git_has_changes(wiki_dir):
        message = f"Add concept: {name}"
        _run_git(["commit", "-m", message], cwd=wiki_dir)
        _run_git(["push", "origin", "HEAD"], cwd=wiki_dir)

    page_url_path = f"/{config.repo}/wiki/{slug}"

    return page_url_path


def patch_paper_concept_links(
    *,
    paper_slug: str,
    concept_slug: str,
    terms: list[str],
    config: WikiConfig,
) -> bool:
    """Add first-mention links from a paper wiki page to a concept page.

    Args:
        paper_slug: Paper wiki slug.
        concept_slug: Concept wiki slug.
        terms: Phrases to link (first match wins across all terms).
        config: Wiki configuration.

    Returns:
        ``True`` when the paper page was updated.

    Raises:
        WikiPublishError: If the paper page is missing or git operations fail.
    """
    from comprehend.concept.linkify import (
        paper_links_to_concept,
        patch_first_concept_mention,
    )

    wiki_dir = ensure_wiki_checkout(config)
    page_path = wiki_dir / f"{paper_slug}.md"
    if not page_path.is_file():
        raise WikiPublishError(f"Paper wiki page not found: {paper_slug}")

    markdown = page_path.read_text(encoding="utf-8")
    if paper_links_to_concept(markdown, concept_slug=concept_slug):
        return False

    patched = markdown
    linked = False
    for term in terms:
        patched, term_linked = patch_first_concept_mention(
            patched,
            term=term,
            concept_slug=concept_slug,
        )
        if term_linked:
            linked = True
            break

    if not linked:
        return False

    page_path.write_text(patched, encoding="utf-8")
    _run_git(["add", page_path.name], cwd=wiki_dir)

    if _git_has_changes(wiki_dir):
        message = f"Link {concept_slug} in {paper_slug}"
        _run_git(["commit", "-m", message], cwd=wiki_dir)
        _run_git(["push", "origin", "HEAD"], cwd=wiki_dir)

    return True


def _update_concepts_index(
    *,
    wiki_dir: Path,
    slug: str,
    name: str,
    tags: list[str],
) -> None:
    concepts_path = wiki_dir / "Concepts.md"
    tag_text = ", ".join(f"`{tag}`" for tag in tags)
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    entry = f"- [{name}]({slug}) — {tag_text} — {timestamp}"

    if concepts_path.is_file():
        content = concepts_path.read_text(encoding="utf-8")
    else:
        content = "# Concepts\n\n"

    if re.search(rf"\]\({re.escape(slug)}\)", content):
        return

    if not content.endswith("\n"):
        content += "\n"

    content += entry + "\n"
    concepts_path.write_text(content, encoding="utf-8")


def _update_home_index(
    *,
    wiki_dir: Path,
    slug: str,
    title: str,
    tags: list[str],
) -> None:
    home_path = wiki_dir / "Home.md"
    tag_text = ", ".join(f"`{tag}`" for tag in tags)
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    entry = f"- [{title}]({slug}) — {tag_text} — {timestamp}"

    if home_path.is_file():
        content = home_path.read_text(encoding="utf-8")
    else:
        content = "# Paper summaries\n\n"

    if re.search(rf"\]\({re.escape(slug)}\)", content):
        return

    if not content.endswith("\n"):
        content += "\n"

    content += entry + "\n"
    home_path.write_text(content, encoding="utf-8")


def _run_git(args: list[str], *, cwd: Path | None = None) -> None:
    command = ["git", *args]
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown error"
        raise WikiPublishError(f"git {' '.join(args)} failed: {stderr}") from exc


def _git_has_changes(wiki_dir: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
        cwd=wiki_dir,
    )

    return bool(result.stdout.strip())
