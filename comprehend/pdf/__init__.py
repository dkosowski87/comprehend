"""PDF package exports."""

from comprehend.pdf.download import (
    PaperDownloadError,
    download_paper,
    fetch_arxiv_metadata,
    paper_cache_dir,
    resolve_pdf_url,
)
from comprehend.pdf.extract import (
    ExtractedPaper,
    FigureInfo,
    extract_figure_by_xref,
    extract_paper,
    extract_text,
    list_figures,
    render_page_region,
)
from comprehend.pdf.figures import (
    FigureRegion,
    figure_clip,
    figure_clip_for_xref,
    list_figure_regions,
    resolve_figure_region,
)

__all__ = [
    "ExtractedPaper",
    "FigureInfo",
    "FigureRegion",
    "PaperDownloadError",
    "download_paper",
    "extract_figure_by_xref",
    "extract_paper",
    "extract_text",
    "fetch_arxiv_metadata",
    "figure_clip",
    "figure_clip_for_xref",
    "list_figure_regions",
    "list_figures",
    "paper_cache_dir",
    "render_page_region",
    "resolve_figure_region",
    "resolve_pdf_url",
]
