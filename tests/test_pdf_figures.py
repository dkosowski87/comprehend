"""Tests for PDF figure region detection."""

from pathlib import Path

import fitz
import pytest

from comprehend.pdf.figures import (
    figure_clip,
    figure_clip_for_xref,
    list_figure_regions,
    resolve_figure_region,
)
from comprehend.render.extract_figure import render_extracted_figure
from comprehend.summary.schema import VisualSpec, VisualType


CACHE_ROOT = Path(".comprehend/papers")


def _require_pdf(slug: str) -> Path:
    pdf_path = CACHE_ROOT / slug / "paper.pdf"
    if not pdf_path.is_file():
        pytest.skip(f"Missing cached PDF: {pdf_path}")

    return pdf_path


def test_figure_clip_detects_rt_detr_overview() -> None:
    pdf_path = _require_pdf("arxiv-2304-08069")

    clip = figure_clip(pdf_path, page=5, figure_number=4)

    assert clip[2] - clip[0] > 400
    assert clip[3] - clip[1] > 150


def test_figure_clip_detects_sam_overview() -> None:
    pdf_path = _require_pdf("arxiv-2304-02643")

    clip = figure_clip(pdf_path, page=5, figure_number=4)

    assert clip[2] - clip[0] > 400
    assert clip[3] - clip[1] > 120


def test_figure_clip_for_xref_covers_composite_figure() -> None:
    pdf_path = _require_pdf("arxiv-2304-08069")

    resolved = figure_clip_for_xref(pdf_path, 429)
    assert resolved is not None

    page, clip = resolved
    assert page == 5
    assert clip[2] - clip[0] > 400


def test_list_figure_regions_includes_captions() -> None:
    pdf_path = _require_pdf("arxiv-2304-08069")

    regions = list_figure_regions(pdf_path)
    figure_four = next(
        region for region in regions if region.page == 5 and region.number == 4
    )

    assert "RT-DETR" in figure_four.caption or "Overview" in figure_four.caption


def test_list_figure_regions_includes_numbered_figures() -> None:
    pdf_path = _require_pdf("arxiv-2304-08069")

    regions = list_figure_regions(pdf_path)
    numbers = {region.number for region in regions if region.page == 5}

    assert 4 in numbers
    assert 5 in numbers


def test_figure_clip_excludes_merged_body_text_block() -> None:
    pdf_path = _require_pdf("arxiv-2312-08344")

    clip = figure_clip(pdf_path, page=1, figure_number=1)

    assert clip[3] - clip[1] < 550


def test_figure_clip_tightens_vertical_bounds() -> None:
    pdf_path = _require_pdf("arxiv-2304-02643")

    clip = figure_clip(pdf_path, page=1, figure_number=1)

    assert clip[3] - clip[1] < 250


def test_list_figure_regions_detects_caption_without_colon() -> None:
    pdf_path = _require_pdf("arxiv-2504-13181")

    regions = list_figure_regions(pdf_path)
    figure_one = next(
        region for region in regions if region.page == 2 and region.number == 1
    )

    assert "Perception Encoder" in figure_one.caption


def test_render_extracted_figure_uses_composite_region_for_xref(tmp_path: Path) -> None:
    pdf_path = _require_pdf("arxiv-2304-08069")
    visual = VisualSpec(
        id="5a",
        caption="Overview",
        type=VisualType.EXTRACT,
        description="RT-DETR architecture",
        page=5,
        xref=429,
    )

    rendered_path = render_extracted_figure(
        pdf_path,
        visual,
        slug="arxiv-2304-08069",
        output_dir=tmp_path,
    )

    image = fitz.open(rendered_path)
    width = image[0].rect.width
    height = image[0].rect.height
    image.close()

    assert width > 700
    assert height > 200


def test_render_extracted_figure_with_figure_number(tmp_path: Path) -> None:
    pdf_path = _require_pdf("arxiv-2304-02643")
    visual = VisualSpec(
        id="5a",
        caption="SAM overview",
        type=VisualType.EXTRACT,
        description="SAM architecture",
        page=5,
        figure_number=4,
    )

    rendered_path = render_extracted_figure(
        pdf_path,
        visual,
        slug="arxiv-2304-02643",
        output_dir=tmp_path,
    )

    image = fitz.open(rendered_path)
    width = image[0].rect.width
    height = image[0].rect.height
    image.close()

    assert width > 700
    assert height > 200


def test_resolve_figure_region_requires_selector() -> None:
    pdf_path = _require_pdf("arxiv-2304-08069")

    with pytest.raises(ValueError, match="figure_number, xref, or clip"):
        resolve_figure_region(pdf_path, page=5)
