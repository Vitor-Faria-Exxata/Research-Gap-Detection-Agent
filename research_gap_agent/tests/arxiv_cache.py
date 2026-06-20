"""Tests for the arXiv cache layer.

Uses a temp dir so it doesn't touch the real `cache/arxiv/`.
"""

import json
import os
import tempfile
import time
from datetime import date
from pathlib import Path
from unittest.mock import patch

from research_gap_agent.arxiv import (
    FullTextCache,
    MetadataCache,
    clear_all,
)
from research_gap_agent.arxiv.cache import _is_cache_enabled
from research_gap_agent.schemas import Paper


def _paper(arxiv_id: str) -> Paper:
    return Paper(
        id=f"arxiv:{arxiv_id}",
        source="arxiv",
        title=f"Test {arxiv_id}",
        abstract=f"Abstract for {arxiv_id}",
        authors=["Test Author"],
        published_date=date(2024, 1, 1),
        url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        is_open_access=True,
        arxiv_id=arxiv_id,
    )


def test_full_text_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        cache = FullTextCache(root=Path(tmp))
        assert cache.get("2401.00001") is None

        cache.put("2401.00001", "# Markdown\nHello world")
        assert cache.get("2401.00001") == "# Markdown\nHello world"
        assert cache.has("2401.00001")

        n = cache.clear()
        assert n == 1
        assert cache.get("2401.00001") is None
    print("  [ok] full-text roundtrip + clear")


def test_full_text_disabled_by_env():
    with tempfile.TemporaryDirectory() as tmp:
        cache = FullTextCache(root=Path(tmp))
        with patch.dict(os.environ, {"RGA_ARXIV_CACHE": "disabled"}):
            assert _is_cache_enabled() is False
            cache.put("2401.00001", "should not be written")
            assert cache.get("2401.00001") is None
    print("  [ok] RGA_ARXIV_CACHE=disabled bypasses the cache")


def test_full_text_custom_dir():
    with tempfile.TemporaryDirectory() as tmp:
        custom = Path(tmp) / "my_cache"
        cache = FullTextCache(root=custom)
        cache.put("2401.00001", "x")
        assert (custom / "full_text" / "2401.00001.md").exists()
    print("  [ok] custom cache root honored")


def test_metadata_roundtrip_with_ttl():
    with tempfile.TemporaryDirectory() as tmp:
        cache = MetadataCache(root=Path(tmp), ttl_s=60)
        assert cache.get_fresh("a query") is None

        papers = [_paper("2401.00001"), _paper("2401.00002")]
        cache.put("a query", papers)

        loaded = cache.get_fresh("a query")
        assert loaded is not None
        assert [p.arxiv_id for p in loaded] == ["2401.00001", "2401.00002"]
    print("  [ok] metadata roundtrip with TTL")


def test_metadata_ttl_expiry():
    with tempfile.TemporaryDirectory() as tmp:
        cache = MetadataCache(root=Path(tmp), ttl_s=0)
        papers = [_paper("2401.00001")]
        cache.put("q", papers)
        time.sleep(0.01)
        # ttl_s=0 means everything is stale
        assert cache.get_fresh("q") is None
        # but `get` (no freshness check) still returns it
        stale = cache.get("q")
        assert stale is not None and not stale.is_fresh(ttl_s=0)
    print("  [ok] metadata TTL expiry works")


def test_metadata_query_key_normalization():
    with tempfile.TemporaryDirectory() as tmp:
        cache = MetadataCache(root=Path(tmp), ttl_s=60)
        cache.put("a query with / slashes & special?chars", [_paper("1")])
        files = list((Path(tmp) / "metadata").glob("*.json"))
        assert len(files) == 1
        # Filename should be filesystem-safe
        assert "/" not in files[0].name
        assert "&" not in files[0].name
    print("  [ok] query key normalized to safe filename")


def test_clear_all():
    with tempfile.TemporaryDirectory() as tmp:
        # Point the env override so clear_all wipes the temp dir, not
        # the user's real cache.
        with patch.dict(os.environ, {"RGA_ARXIV_CACHE_DIR": tmp}):
            FullTextCache().put("1", "x")
            MetadataCache().put("q", [_paper("1")])
            counts = clear_all()
            assert counts == {"full_text": 1, "metadata": 1}
            assert FullTextCache().get("1") is None
            assert MetadataCache().get_fresh("q") is None
    print("  [ok] clear_all wipes both caches")


if __name__ == "__main__":
    test_full_text_roundtrip()
    test_full_text_disabled_by_env()
    test_full_text_custom_dir()
    test_metadata_roundtrip_with_ttl()
    test_metadata_ttl_expiry()
    test_metadata_query_key_normalization()
    test_clear_all()
    print("\nall passed")
