"""Link concept mentions in paper wiki markdown."""

from __future__ import annotations

import re


def paper_links_to_concept(markdown: str, *, concept_slug: str) -> bool:
    """Return whether the paper page already links to a concept slug."""
    pattern = re.compile(rf"\]\({re.escape(concept_slug)}\)")

    return pattern.search(markdown) is not None


def patch_first_concept_mention(
    markdown: str,
    *,
    term: str,
    concept_slug: str,
) -> tuple[str, bool]:
    """Link the first safe occurrence of ``term`` to a concept wiki page.

    Args:
        markdown: Paper wiki markdown body.
        term: Phrase to search for (case-insensitive).
        concept_slug: Target wiki slug such as ``concept-cyclic-shift``.

    Returns:
        Tuple of ``(patched_markdown, linked)``. ``linked`` is ``False`` when no
        suitable mention was found.
    """
    pattern = re.compile(re.escape(term), re.IGNORECASE)

    for match in pattern.finditer(markdown):
        start = match.start()
        end = match.end()

        if not _can_link_at(markdown, start=start, end=end):
            continue

        original = markdown[start:end]
        replacement = f"[{original}]({concept_slug})"
        patched = markdown[:start] + replacement + markdown[end:]

        return patched, True

    return markdown, False


def _can_link_at(text: str, *, start: int, end: int) -> bool:
    before = text[:start]
    after = text[end:]

    if before.count("[") > before.count("]"):
        return False

    if after.startswith("]("):
        return False

    if start > 0 and text[start - 1] == "[":
        return False

    if _inside_math_delimiters(text, start):
        return False

    return True


def _inside_math_delimiters(text: str, position: int) -> bool:
    before = text[:position]
    double_dollar_parity = before.count("$$") % 2

    return double_dollar_parity == 1
