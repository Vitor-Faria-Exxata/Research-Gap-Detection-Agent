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

The interval is 10 s (3× the published minimum)
"""

import logging
import random
import threading
import time


logger = logging.getLogger(__name__)


ARXIV_MIN_INTERVAL_S = 10.0
_JITTER_MAX_S = 2.0


_lock = threading.Lock()
_next_allowed_monotonic: float = 0.0


def wait() -> None:
    """Block until the next arXiv call is allowed under the policy.

    Thread-safe. Holds the lock for the duration of the sleep so that even
    if many threads call this at once they drain one-at-a-time and each
    gets its own slot separated by ARXIV_MIN_INTERVAL_S.
    """
    global _next_allowed_monotonic
    with _lock:
        now = time.monotonic()
        delay = _next_allowed_monotonic - now
        if delay > 0:
            time.sleep(delay)
        jitter = random.uniform(0, _JITTER_MAX_S)
        _next_allowed_monotonic = time.monotonic() + ARXIV_MIN_INTERVAL_S + jitter


def extend(extra_seconds: float) -> None:
    global _next_allowed_monotonic
    with _lock:
        _next_allowed_monotonic = max(
            _next_allowed_monotonic,
            time.monotonic() + extra_seconds,
        )
    logger.debug("arXiv throttle extended by %.1fs", extra_seconds)


def reset_for_tests() -> None:
    """Reset the throttle. Tests only."""
    global _next_allowed_monotonic
    with _lock:
        _next_allowed_monotonic = 0.0
