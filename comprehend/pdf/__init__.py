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

__all__ = [
    "ExtractedPaper",
    "FigureInfo",
    "PaperDownloadError",
    "download_paper",
    "extract_figure_by_xref",
    "extract_paper",
    "extract_text",
    "fetch_arxiv_metadata",
    "list_figures",
    "paper_cache_dir",
    "render_page_region",
    "resolve_pdf_url",
]
