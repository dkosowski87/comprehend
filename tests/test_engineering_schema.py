"""Tests for engineering summary schema."""

from pathlib import Path

import pytest

from comprehend.engineering.schema import (
    CodeExample,
    EngineeringSummary,
    load_engineering_summary,
    render_markdown,
    save_engineering_summary,
)
from comprehend.summary.schema import VisualSpec, VisualType


def test_render_engineering_markdown_includes_code_and_topic() -> None:
    summary = EngineeringSummary(
        title="CUDA Streams",
        source_url="https://docs.nvidia.com/cuda/cuda-c-programming-guide/",
        topic="cuda",
        tags=["cuda"],
        slug="engineering-cuda-streams",
        keywords=["stream"],
        problem=["Host and device work are asynchronous."],
        solution=["CUDA streams order kernels and copies."],
        key_concepts=["A stream is a FIFO queue of GPU work."],
        code_examples=[
            CodeExample(
                id="3a",
                title="Create a stream",
                language="cpp",
                code="cudaStream_t stream;\ncudaStreamCreate(&stream);",
            ),
        ],
        visuals=[
            VisualSpec(
                id="4a",
                caption="Stream execution",
                type=VisualType.MERMAID,
                description="Host enqueues, GPU executes",
                mermaid_source="flowchart LR\n  Host --> GPU",
                asset_filename="engineering-cuda-streams-4a.png",
            ),
        ],
    )

    markdown = render_markdown(summary)

    assert "## 4. Code examples" in markdown
    assert "```cpp" in markdown
    assert "**Topic:** `cuda`" in markdown
    assert "engineering-cuda-streams-4a.png" in markdown


def test_engineering_summary_rejects_extract_visual() -> None:
    with pytest.raises(ValueError, match="extract visuals are not supported"):
        EngineeringSummary(
            title="Bad",
            source_url="https://example.com",
            topic="cuda",
            tags=["cuda"],
            slug="engineering-bad",
            problem=["p"],
            solution=["s"],
            key_concepts=["k"],
            visuals=[
                VisualSpec(
                    id="4a",
                    caption="nope",
                    type=VisualType.EXTRACT,
                    description="nope",
                    page=1,
                    figure_number=1,
                ),
            ],
        )


def test_save_and_load_engineering_summary(tmp_path: Path) -> None:
    summary = EngineeringSummary(
        title="Triton Basics",
        source_url="https://triton-lang.org/",
        topic="triton",
        tags=["triton"],
        slug="engineering-triton-basics",
        problem=["Writing CUDA kernels by hand is slow."],
        solution=["Triton provides a Python DSL for tile-based GPU kernels."],
        key_concepts=["Programs map to blocks; each program uses a tile of data."],
    )
    path = tmp_path / "summary.json"
    save_engineering_summary(summary, path)
    loaded = load_engineering_summary(path)

    assert loaded.slug == summary.slug
    assert loaded.topic == "triton"
