"""
TEMPORARY diagnostic instrumentation for TTFB investigation.

Provides:
  - RequestTimingMiddleware: logs total request time, query count/time, per-middleware breakdown
  - timed_section(): context manager for timing code blocks inside views
  - FernetDecryptCounter: monkey-patch wrapper to count/time every decrypt call

REMOVE THIS FILE after profiling is complete.
"""

import functools
import logging
import time

from django.db import connection, reset_queries

logger = logging.getLogger("perf")
# Ensure output goes to console even if logging isn't configured for this logger
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[PERF] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False


# ---------------------------------------------------------------------------
# 1. Context manager for timing code sections inside views
# ---------------------------------------------------------------------------

class timed_section:
    """
    Usage:
        with timed_section("label", request) as t:
            ... expensive work ...
        # t.elapsed is available after the block
    """

    def __init__(self, label, request=None):
        self.label = label
        self.request = request
        self.start = None
        self.elapsed = None
        self.queries_before = 0

    def __enter__(self):
        self.queries_before = len(connection.queries)
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self.start
        queries_in_section = len(connection.queries) - self.queries_before
        ms = self.elapsed * 1000
        logger.info(
            "  %-40s %8.1f ms  (%d queries)",
            self.label,
            ms,
            queries_in_section,
        )
        if self.request is not None and hasattr(self.request, "_perf_sections"):
            self.request._perf_sections.append(
                (self.label, ms, queries_in_section)
            )
        return False  # don't suppress exceptions


# ---------------------------------------------------------------------------
# 2. Fernet decrypt counter (monkey-patch)
# ---------------------------------------------------------------------------

_fernet_stats = {
    "calls": 0,
    "total_ms": 0.0,
}


def patch_fernet_decrypt():
    """
    Monkey-patch EncryptedFieldMixin._decrypt to count calls and time.
    Call once at startup (e.g. in AppConfig.ready or at module import time).
    """
    from core.fields import EncryptedFieldMixin

    original = EncryptedFieldMixin._decrypt

    @functools.wraps(original)
    def timed_decrypt(self, value):
        t0 = time.perf_counter()
        result = original(self, value)
        dt = (time.perf_counter() - t0) * 1000
        _fernet_stats["calls"] += 1
        _fernet_stats["total_ms"] += dt
        return result

    EncryptedFieldMixin._decrypt = timed_decrypt


def reset_fernet_stats():
    _fernet_stats["calls"] = 0
    _fernet_stats["total_ms"] = 0.0


def get_fernet_stats():
    return dict(_fernet_stats)


# Auto-patch on import so every request is measured
patch_fernet_decrypt()


# ---------------------------------------------------------------------------
# 3. Request-level timing middleware
# ---------------------------------------------------------------------------

# Paths to instrument (prefix match)
_TRACKED_PREFIXES = (
    "/tracking/",
    "/",   # catch-all — remove if too noisy
)


class RequestTimingMiddleware:
    """
    Add as the FIRST entry in MIDDLEWARE to capture total wall-clock time.
    Logs:
      - total request duration
      - total SQL query count and cumulative SQL time
      - Fernet decrypt count and time
      - per-section breakdown (populated by timed_section in views)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only instrument tracked paths
        if not any(request.path.startswith(p) for p in _TRACKED_PREFIXES):
            return self.get_response(request)

        # Force query logging even when DEBUG=False (connection.queries
        # is only populated when the connection wrapper has force_debug_cursor).
        connection.force_debug_cursor = True

        # Reset counters
        reset_queries()
        reset_fernet_stats()
        request._perf_sections = []
        request._perf_start = time.perf_counter()

        # ---- pre-view middleware time ----
        # (We can't split individual middlewares here, but the view's
        #  first timed_section will let us subtract view time from total.)

        response = self.get_response(request)

        total_ms = (time.perf_counter() - request._perf_start) * 1000

        queries = connection.queries[:]
        q_count = len(queries)
        q_time_ms = sum(float(q.get("time", 0)) for q in queries) * 1000

        fernet = get_fernet_stats()

        # Compute view-internal time vs middleware overhead
        view_ms = sum(s[1] for s in getattr(request, "_perf_sections", []))
        middleware_overhead_ms = total_ms - view_ms

        logger.info("=" * 72)
        logger.info(
            "REQUEST  %s %s  -> %s",
            request.method,
            request.path,
            response.status_code,
        )
        logger.info("-" * 72)
        logger.info("  Total wall-clock:          %8.1f ms", total_ms)
        logger.info("  SQL queries:               %8d  (%8.1f ms)", q_count, q_time_ms)
        logger.info(
            "  Fernet decrypts:           %8d  (%8.1f ms)",
            fernet["calls"],
            fernet["total_ms"],
        )
        logger.info("  View sections (sum):       %8.1f ms", view_ms)
        logger.info("  Middleware overhead (est):  %8.1f ms", middleware_overhead_ms)
        logger.info("-" * 72)

        # Per-section breakdown
        for label, ms, qc in getattr(request, "_perf_sections", []):
            logger.info("  %-40s %8.1f ms  (%d queries)", label, ms, qc)

        # Slow queries (>10 ms)
        slow = [(float(q.get("time", 0)) * 1000, q["sql"]) for q in queries if float(q.get("time", 0)) > 0.01]
        if slow:
            logger.info("-" * 72)
            logger.info("  SLOW QUERIES (>10 ms):")
            for ms_q, sql in sorted(slow, reverse=True):
                logger.info("    %8.1f ms  %s", ms_q, sql[:200])

        # Duplicate query detection
        sql_list = [q["sql"] for q in queries]
        seen = {}
        for s in sql_list:
            seen[s] = seen.get(s, 0) + 1
        dupes = {s: c for s, c in seen.items() if c > 1}
        if dupes:
            logger.info("-" * 72)
            logger.info("  DUPLICATE QUERIES:")
            for sql, count in sorted(dupes.items(), key=lambda x: -x[1]):
                logger.info("    x%d  %s", count, sql[:200])

        logger.info("=" * 72)

        # Restore default cursor behaviour
        connection.force_debug_cursor = False

        return response
