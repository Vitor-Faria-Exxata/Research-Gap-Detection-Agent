"""arXiv-specific helpers: rate limiting and disk-backed caching.

Public surface (re-exported for convenience):

* `wait` — the shared throttle. Every code path that talks to arxiv.org
  (search, HTML, PDF download) MUST call this first.
* `FullTextCache`, `MetadataCache` — on-disk caches that let repeat
  runs skip the network entirely.
* `clear_all` — wipe both caches.
"""

from .cache import (
    DEFAULT_METADATA_TTL_S,
    CachedMetadata,
    FullTextCache,
    MetadataCache,
    clear_all,
)
from .throttle import ARXIV_MIN_INTERVAL_S, reset_for_tests, wait


__all__ = [
    "ARXIV_MIN_INTERVAL_S",
    "wait",
    "reset_for_tests",
    "FullTextCache",
    "MetadataCache",
    "CachedMetadata",
    "DEFAULT_METADATA_TTL_S",
    "clear_all",
]
