"""Allowed topic tags for paper and concept summaries."""

from __future__ import annotations

MAX_PAPER_TAGS = 5

ALLOWED_PAPER_TAGS: frozenset[str] = frozenset(
    {
        "3d-reconstruction",
        "4d-reconstruction",
        "6dof-pose-estimation",
        "auto-encoders",
        "autonomous-driving",
        "continual-learning",
        "contrastive-learning",
        "data-representation",
        "depth-estimation",
        "diffusion",
        "distillation",
        "domain-adaptation",
        "few-shot-learning",
        "flow-maps",
        "flow-matching",
        "generative-adversarial-networks",
        "gaussian-splatting",
        "grounding",
        "human-body-modeling",
        "image-captioning",
        "image-classification",
        "image-editing",
        "image-generation",
        "image-retrieval",
        "image-restoration",
        "implicit-representations",
        "instance-segmentation",
        "jepa",
        "keypoint-detection",
        "language",
        "masked-image-modeling",
        "motion-estimation",
        "multi-view-stereo",
        "neural-architecture-search",
        "neural-radiance-fields",
        "neural-rendering",
        "neural-tangent-kernels",
        "normalizing-flows",
        "novel-view-synthesis",
        "object-detection",
        "object-tracking",
        "ocr",
        "open-vocabulary",
        "optimization",
        "optical-flow",
        "panoptic-segmentation",
        "physically-based-rendering",
        "representation-learning",
        "robotics",
        "robustness",
        "scene-generation",
        "scene-understanding",
        "self-supervised-learning",
        "semantic-segmentation",
        "slam",
        "speculative-decoding",
        "stereo-matching",
        "structure-from-motion",
        "super-resolution",
        "synthetic-data",
        "temporal-coherence",
        "transformers",
        "video-generation",
        "vision",
        "vision-transformers",
        "visual-odometry",
        "visual-question-answering",
        "visual-tracking",
        "vlm",
        "world-simulation",
        "zero-shot",
    },
)


def validate_paper_tags(tags: list[str]) -> list[str]:
    """Validate summary tags against the allowed vocabulary.

    Args:
        tags: Tag slugs from ``summary.json``.

    Returns:
        The validated tag list.

    Raises:
        ValueError: If tag count or values are invalid.
    """
    if len(tags) > MAX_PAPER_TAGS:
        raise ValueError(f"At most {MAX_PAPER_TAGS} tags are allowed per summary")

    invalid = sorted({tag for tag in tags if tag not in ALLOWED_PAPER_TAGS})
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_PAPER_TAGS))
        invalid_text = ", ".join(invalid)
        raise ValueError(
            f"Unknown tag(s): {invalid_text}. Allowed tags: {allowed}",
        )

    return tags


def format_allowed_tags_for_docs() -> str:
    """Return a comma-separated list of allowed tags for agent prompts."""
    return ", ".join(f"`{tag}`" for tag in sorted(ALLOWED_PAPER_TAGS))
