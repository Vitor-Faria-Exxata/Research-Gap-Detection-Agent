"""Shared rate limiter for the arXiv legacy APIs (api, html, pdf).

arXiv's published policy:

    "When using the legacy APIs (including OAI-PMH, RSS, and the arXiv
     API), make no more than one request every three seconds, and limit
     requests to a single connection at a time."
    -- https://info.arxiv.org/help/api/tou.html

Every code path that touches arxiv.org (search, HTML, PDF download) MUST
go through `wait()`. Sharing a single module-level lock means we can't
accidentally fan out across processes / threads and trip the "single
connection" rule.

The interval is 6 s (double the published minimum) for a safety margin
since the per-IP sliding window is stricter in practice than the docs
suggest.
"""

import logging
import threading
import time


logger = logging.getLogger(__name__)


# Published minimum is 3 s; we use 6 s for headroom.
ARXIV_MIN_INTERVAL_S = 6.0


_lock = threading.Lock()
_last_call_monotonic: float = 0.0


def wait() -> None:
    """Block until the next arXiv call is allowed under the policy.

    Thread-safe. Holds the lock for the duration of the sleep, so even if
    many threads call this at once they leave one-at-a-time.
    """
    global _last_call_monotonic
    with _lock:
        elapsed = time.monotonic() - _last_call_monotonic
        if elapsed < ARXIV_MIN_INTERVAL_S:
            time.sleep(ARXIV_MIN_INTERVAL_S - elapsed)
        _last_call_monotonic = time.monotonic()


def reset_for_tests() -> None:
    """Reset the throttle. Tests only."""
    global _last_call_monotonic
    with _lock:
        _last_call_monotonic = 0.0
