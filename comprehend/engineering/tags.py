"""Topic vocabulary for engineering summaries."""

from __future__ import annotations

ALLOWED_ENGINEERING_TOPICS: frozenset[str] = frozenset(
    {
        "algorithms",
        "apple",
        "camera",
        "cuda",
        "jetson",
        "memory",
        "nvidia",
        "onnx",
        "pytorch",
        "tensorrt",
        "triton",
    },
)

MAX_ENGINEERING_TAGS = 5


def validate_engineering_topic(topic: str) -> str:
    """Validate a primary engineering topic slug.

    Args:
        topic: Topic slug such as ``cuda`` or ``pytorch``.

    Returns:
        Normalized topic slug.

    Raises:
        ValueError: When the topic is not in the allowed vocabulary.
    """
    normalized = topic.strip().lower()
    if normalized not in ALLOWED_ENGINEERING_TOPICS:
        allowed = ", ".join(sorted(ALLOWED_ENGINEERING_TOPICS))
        raise ValueError(
            f"Invalid engineering topic '{topic}'. Allowed topics: {allowed}",
        )

    return normalized


def validate_engineering_tags(tags: list[str]) -> list[str]:
    """Validate secondary tags for an engineering summary.

    Tags must be drawn from the same topic vocabulary as the primary topic.

    Args:
        tags: Tag list from ``summary.json``.

    Returns:
        Normalized unique tags, at most :data:`MAX_ENGINEERING_TAGS`.

    Raises:
        ValueError: When any tag is invalid or the list is too long.
    """
    if len(tags) > MAX_ENGINEERING_TAGS:
        raise ValueError(
            f"At most {MAX_ENGINEERING_TAGS} tags allowed, got {len(tags)}",
        )

    normalized_tags: list[str] = []
    for tag in tags:
        normalized_tags.append(validate_engineering_topic(tag))

    unique_tags = list(dict.fromkeys(normalized_tags))

    return unique_tags
