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

    def convert(self, source: str) -> str | None:
        if source.startswith("http://") or source.startswith("https://"):
            try:
                path = download_to_path(source)
            except Exception as exc:
                logger.warning("Failed to download %s: %s", source, exc)
                return None
            try:
                return _convert_local(path)
            finally:
                _safe_unlink(path)
        return _convert_local(source)

    def convert_batch(self, sources: list[str]) -> list[str | None]:
        """Download PDFs serially (rate-limited), convert in parallel.

        arXiv's legacy API rule forces single-connection downloads; the
        actual markdown extraction is CPU-bound and benefits from a pool.

        Returns one entry per source: a markdown string on success, None on
        any download or conversion failure (so the caller can skip that paper
        without aborting the whole batch).
        """
        # (local_path_or_None, is_temp)
        download_results: list[tuple[str | None, bool]] = []

        for src in sources:
            if src.startswith("http://") or src.startswith("https://"):
                try:
                    path = download_to_path(src)
                    download_results.append((path, True))
                except Exception as exc:
                    logger.warning("Failed to download %s: %s", src, exc)
                    download_results.append((None, False))
            else:
                download_results.append((src, False))

        # Build index mapping from pool position -> original source index.
        local_paths = [(i, path) for i, (path, _) in enumerate(download_results) if path is not None]
        results: list[str | None] = [None] * len(sources)

        if local_paths:
            indices, paths = zip(*local_paths)
            try:
                with concurrent.futures.ProcessPoolExecutor() as executor:
                    converted = list(executor.map(_convert_local, paths))
                for idx, text in zip(indices, converted):
                    results[idx] = text
            except Exception as exc:
                logger.warning("ProcessPoolExecutor failed, falling back to serial conversion: %s", exc)
                for idx, path in zip(indices, paths):
                    try:
                        results[idx] = _convert_local(path)
                    except Exception as e:
                        logger.warning("Conversion failed for index %d: %s", idx, e)

        for _, (path, is_temp) in enumerate(download_results):
            if is_temp and path:
                _safe_unlink(path)

        return results


def _safe_unlink(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
