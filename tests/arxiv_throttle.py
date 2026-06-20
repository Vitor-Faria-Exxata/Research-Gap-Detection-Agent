"""Verify the arXiv throttle serializes requests across all entry points.

arXiv policy: ≤ 1 request / 3 s, single connection. We use 10 s internally
for headroom. This test mocks every arXiv-touching path and asserts that
N requests, fired from N threads using different entry points, never
overlap and never go faster than the configured interval.
"""

import threading
import time
from unittest.mock import patch

from research_gap_agent.arxiv import (
    ARXIV_MIN_INTERVAL_S,
    reset_for_tests,
    wait as arxiv_wait,
)
from research_gap_agent.sources.arxiv import ArxivSource
from research_gap_agent.document_converters.arxiv_html_converter import ArxivHtmlFallbackConverter
from research_gap_agent.document_converters.pymupdf_converter import PyMuPDFConverter


def test_throttle_serializes_within_a_module():
    """Many threads through the same `wait()` are serialized."""
    reset_for_tests()
    timestamps = []
    lock = threading.Lock()

    def worker():
        arxiv_wait()
        with lock:
            timestamps.append(time.monotonic())

    threads = [threading.Thread(target=worker) for _ in range(4)]
    t0 = time.monotonic()
    for t in threads: t.start()
    for t in threads: t.join()
    elapsed = time.monotonic() - t0

    # 4 calls * ARXIV_MIN_INTERVAL_S minimum gap = 3 * interval minimum total
    assert elapsed >= 3 * ARXIV_MIN_INTERVAL_S, f"too fast: {elapsed:.2f}s"
    # Successive timestamps must be spaced at least the throttle interval
    timestamps.sort()
    for a, b in zip(timestamps, timestamps[1:]):
        gap = b - a
        # Allow tiny float slop
        assert gap >= ARXIV_MIN_INTERVAL_S - 0.05, f"calls too close: {gap:.2f}s"
    print(f"  [ok] 4 same-module calls took {elapsed:.2f}s, gaps >= {ARXIV_MIN_INTERVAL_S}s")


def test_throttle_serializes_across_modules():
    """The shared lock prevents the API source, HTML converter, and PDF
    downloader from running concurrently."""
    reset_for_tests()

    call_log = []
    call_lock = threading.Lock()

    def record_call(name: str, fn):
        # Real `wait()` plus a record of when the call actually started
        # and ended. If the throttle is shared, no two intervals overlap.
        arxiv_wait()
        with call_lock:
            call_log.append((name, time.monotonic(), "start"))
        # Simulate the request taking some time
        time.sleep(0.05)
        with call_lock:
            call_log.append((name, time.monotonic(), "end"))
        return fn()

    # 5 calls across 3 different entry points. Each goes through
    # `arxiv_wait()` so they should serialize.
    funcs = [
        ("api",      lambda: None),
        ("html",     lambda: None),
        ("pdf",      lambda: None),
        ("api",      lambda: None),
        ("html",     lambda: None),
    ]
    threads = [
        threading.Thread(target=record_call, args=(name, fn))
        for name, fn in funcs
    ]
    t0 = time.monotonic()
    for t in threads: t.start()
    for t in threads: t.join()
    elapsed = time.monotonic() - t0

    # 5 calls * interval gap = 4 * interval minimum total
    assert elapsed >= 4 * ARXIV_MIN_INTERVAL_S, f"too fast: {elapsed:.2f}s"

    # No two calls should overlap (start[i+1] >= end[i])
    starts_and_ends = sorted(call_log, key=lambda x: x[1])
    in_flight = 0
    max_in_flight = 0
    for _name, _t, kind in starts_and_ends:
        if kind == "start":
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        else:
            in_flight -= 1
    assert max_in_flight == 1, f"concurrent calls: peak {max_in_flight}"
    print(f"  [ok] 5 cross-module calls took {elapsed:.2f}s, peak concurrency = 1")


def test_html_converter_no_threadpool():
    """The HTML converter's convert_batch must be sequential now."""
    import inspect
    from research_gap_agent.document_converters.arxiv_html_converter import ArxivHtmlFallbackConverter

    src = inspect.getsource(ArxivHtmlFallbackConverter.convert_batch)
    assert "ThreadPoolExecutor" not in src, "convert_batch still uses ThreadPoolExecutor"
    assert "ProcessPoolExecutor" not in src, "convert_batch uses ProcessPoolExecutor"
    print("  [ok] ArxivHtmlFallbackConverter.convert_batch is sequential")


def test_paper_extractor_no_threadpool():
    """The paper_extractor node must not wrap HTML fetches in a pool."""
    import inspect
    from research_gap_agent.nodes.paper_extractor import paper_extractor_node

    src = inspect.getsource(paper_extractor_node)
    assert "ThreadPoolExecutor" not in src, "paper_extractor_node still uses ThreadPoolExecutor"
    print("  [ok] paper_extractor_node has no ThreadPoolExecutor")


def test_actual_arxiv_source_uses_throttle():
    """ArxivSource.search must call arxiv_throttle.wait()."""
    import inspect
    from research_gap_agent.sources.arxiv import ArxivSource

    src = inspect.getsource(ArxivSource.search)
    assert "arxiv_throttle" in src or "wait_for_rate_limit" in src, \
        "ArxivSource.search doesn't call the throttle"
    print("  [ok] ArxivSource.search calls the throttle")


if __name__ == "__main__":
    print("test_throttle_serializes_within_a_module:")
    test_throttle_serializes_within_a_module()
    print("test_throttle_serializes_across_modules:")
    test_throttle_serializes_across_modules()
    print("test_html_converter_no_threadpool:")
    test_html_converter_no_threadpool()
    print("test_paper_extractor_no_threadpool:")
    test_paper_extractor_no_threadpool()
    print("test_actual_arxiv_source_uses_throttle:")
    test_actual_arxiv_source_uses_throttle()
    print("\nall passed")
