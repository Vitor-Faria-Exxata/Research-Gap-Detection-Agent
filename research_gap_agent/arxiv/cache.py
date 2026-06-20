"""Disk-backed cache for arXiv data.

Two caches, both keyed on disk and addressable by arXiv content:

* `FullTextCache` — the markdown produced by the HTML or PDF converter,
  keyed by arxiv_id. Permanent (papers don't change). Eliminates the
  6 s / paper wait on repeat runs.

* `MetadataCache` — the list of `Paper`s returned by the API for a given
  query string, with a TTL. Eliminates the search call when the user
  re-runs the same topic.

Cache root defaults to `./cache/arxiv/` and can be overridden with the
`RGA_ARXIV_CACHE_DIR` env var. Set `RGA_ARXIV_CACHE=disabled` to bypass
the cache entirely.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from research_gap_agent.schemas import Paper


logger = logging.getLogger(__name__)


DEFAULT_CACHE_ROOT = Path("cache") / "arxiv"
DEFAULT_METADATA_TTL_S = 24 * 60 * 60  # 1 day


def _is_cache_enabled() -> bool:
    return os.environ.get("RGA_ARXIV_CACHE", "enabled").lower() not in (
        "0", "false", "no", "disabled",
    )


def _cache_root() -> Path:
    return Path(os.environ.get("RGA_ARXIV_CACHE_DIR", str(DEFAULT_CACHE_ROOT)))


# --------------------------------------------------------------------- #
# Full-text cache (markdown, keyed by arxiv_id, no TTL)
# --------------------------------------------------------------------- #


class FullTextCache:
    """Maps arxiv_id -> markdown text. Permanent."""

    def __init__(self, root: Optional[Path] = None):
        self.root = (root or _cache_root()) / "full_text"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, arxiv_id: str) -> Path:
        return self.root / f"{arxiv_id}.md"

    def get(self, arxiv_id: str) -> Optional[str]:
        if not _is_cache_enabled():
            return None
        path = self._path(arxiv_id)
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("FullTextCache: failed to read %s: %s", path, exc)
            return None

    def put(self, arxiv_id: str, markdown: str) -> None:
        if not _is_cache_enabled():
            return
        try:
            self._path(arxiv_id).write_text(markdown, encoding="utf-8")
        except OSError as exc:
            logger.warning("FullTextCache: failed to write %s: %s", arxiv_id, exc)

    def has(self, arxiv_id: str) -> bool:
        return self.get(arxiv_id) is not None

    def clear(self) -> int:
        n = 0
        for p in self.root.glob("*.md"):
            try:
                p.unlink()
                n += 1
            except OSError:
                pass
        return n


# --------------------------------------------------------------------- #
# Metadata cache (query -> list[Paper], TTL-bounded)
# --------------------------------------------------------------------- #


@dataclass(frozen=True)
class CachedMetadata:
    papers: list[Paper]
    stored_at: float

    def is_fresh(self, ttl_s: int) -> bool:
        return (time.time() - self.stored_at) < ttl_s


class MetadataCache:
    """Maps a normalized query string -> list[Paper] with a TTL."""

    def __init__(self, root: Optional[Path] = None, ttl_s: int = DEFAULT_METADATA_TTL_S):
        self.root = (root or _cache_root()) / "metadata"
        self.root.mkdir(parents=True, exist_ok=True)
        self.ttl_s = ttl_s

    @staticmethod
    def _key(query: str) -> str:
        # Stable, filesystem-safe filename.
        return "".join(c if (c.isalnum() or c in "-_") else "_" for c in query.strip())[:200]

    def _path(self, query: str) -> Path:
        return self.root / f"{self._key(query)}.json"

    def get(self, query: str) -> Optional[CachedMetadata]:
        if not _is_cache_enabled():
            return None
        path = self._path(query)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("MetadataCache: failed to read %s: %s", path, exc)
            return None
        papers = [Paper.model_validate(p) for p in data.get("papers", [])]
        return CachedMetadata(papers=papers, stored_at=float(data["stored_at"]))

    def get_fresh(self, query: str) -> Optional[list[Paper]]:
        cached = self.get(query)
        if cached is None or not cached.is_fresh(self.ttl_s):
            return None
        return cached.papers

    def put(self, query: str, papers: Iterable[Paper]) -> None:
        if not _is_cache_enabled():
            return
        payload = {
            "stored_at": time.time(),
            "papers": [p.model_dump(mode="json") for p in papers],
        }
        try:
            self._path(query).write_text(json.dumps(payload), encoding="utf-8")
        except OSError as exc:
            logger.warning("MetadataCache: failed to write %s: %s", query, exc)

    def clear(self) -> int:
        n = 0
        for p in self.root.glob("*.json"):
            try:
                p.unlink()
                n += 1
            except OSError:
                pass
        return n


# --------------------------------------------------------------------- #
# Convenience
# --------------------------------------------------------------------- #


def clear_all() -> dict[str, int]:
    """Wipe both caches. Returns counts of removed files per cache."""
    return {
        "full_text": FullTextCache().clear(),
        "metadata": MetadataCache().clear(),
    }
