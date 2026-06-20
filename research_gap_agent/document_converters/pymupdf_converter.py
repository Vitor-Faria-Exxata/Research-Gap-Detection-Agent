"""PyMuPDF-based document converter.

PDF *downloads* (which hit arxiv.org and count against the legacy API
quota) are serialized via the shared arXiv throttle. PDF *conversion* is
CPU-bound and runs in a process pool.
"""

import concurrent.futures
import logging
import os

from .document_converter import DocumentConverter
from .ensure_local_file import download_to_path


logger = logging.getLogger(__name__)


def _convert_local(local_path: str) -> str:
    """Convert an already-local PDF to markdown. Pure CPU work."""
    import pymupdf4llm
    return pymupdf4llm.to_markdown(local_path)


class PyMuPDFConverter(DocumentConverter):

    def convert(self, source: str) -> str:
        if source.startswith("http://") or source.startswith("https://"):
            path = download_to_path(source)
            try:
                return _convert_local(path)
            finally:
                _safe_unlink(path)
        return _convert_local(source)

    def convert_batch(self, sources: list[str]) -> list[str]:
        """Download PDFs serially (rate-limited), convert in parallel.

        arXiv's legacy API rule forces single-connection downloads; the
        actual markdown extraction is CPU-bound and benefits from a pool.
        """
        local_paths: list[str] = []
        temp_paths: list[str] = []

        try:
            for src in sources:
                if src.startswith("http://") or src.startswith("https://"):
                    path = download_to_path(src)
                    local_paths.append(path)
                    temp_paths.append(path)
                else:
                    local_paths.append(src)

            with concurrent.futures.ProcessPoolExecutor() as executor:
                results = list(executor.map(_convert_local, local_paths))
            return results
        finally:
            for p in temp_paths:
                _safe_unlink(p)


def _safe_unlink(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
