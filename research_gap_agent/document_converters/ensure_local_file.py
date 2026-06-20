"""Download a URL to a temp file (or yield a local path as-is).

Honors the arXiv legacy API rate limit. Even non-arXiv URLs go through the
same throttle so that a batch of arXiv PDFs mixed with other downloads
can't accidentally open a second connection.
"""

import contextlib
import logging
import os
import tempfile

import requests

from research_gap_agent.arxiv import wait as arxiv_throttle_wait


logger = logging.getLogger(__name__)


@contextlib.contextmanager
def ensure_local_file(source: str):
    """If `source` is a URL, downloads it to a temp file and yields the path.

    The temp file is cleaned up on exit. Local paths are yielded as-is.
    """
    if not (source.startswith("http://") or source.startswith("https://")):
        yield source
        return

    # arXiv legacy API rule: ≤ 1 request / 3 s, single connection.
    arxiv_throttle_wait()

    response = requests.get(source, stream=True, timeout=60)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        temp_path = temp_file.name

    try:
        yield temp_path
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def download_to_path(url: str, suffix: str = ".pdf") -> str:
    """Download `url` to a temp file, return the path.

    Caller is responsible for cleanup. Respects the arXiv throttle.
    """
    arxiv_throttle_wait()
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
        return f.name
