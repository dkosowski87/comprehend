"""Tests for engineering queue loading."""

import yaml

from comprehend.engineering.queue import (
    EngineeringQueueEntry,
    add_engineering_to_queue,
    load_engineering_queue,
)


def test_load_engineering_queue(tmp_path) -> None:
    engineering_file = tmp_path / "engineering.yaml"
    engineering_file.write_text(
        yaml.dump(
            {
                "engineering": [
                    {
                        "url": "https://pytorch.org/docs/stable/notes/cuda.html",
                        "slug": "engineering-pytorch-cuda-semantics",
                        "title": "PyTorch CUDA Semantics",
                        "topic": "pytorch",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    entries = load_engineering_queue(engineering_file)

    assert len(entries) == 1
    assert entries[0].topic == "pytorch"
    assert entries[0].resolve_slug() == "engineering-pytorch-cuda-semantics"
    assert entries[0].resolve_topic() == "pytorch"


def test_add_engineering_to_queue(tmp_path) -> None:
    engineering_file = tmp_path / "engineering.yaml"
    engineering_file.write_text("engineering: []\n", encoding="utf-8")

    entry = add_engineering_to_queue(
        engineering_file,
        url="https://onnx.ai/onnx/intro/",
        topic="onnx",
        title="ONNX Introduction",
    )

    assert isinstance(entry, EngineeringQueueEntry)
    assert entry.resolve_topic() == "onnx"
    assert entry.resolve_slug().startswith("engineering-")

    entries = load_engineering_queue(engineering_file)
    assert len(entries) == 1
