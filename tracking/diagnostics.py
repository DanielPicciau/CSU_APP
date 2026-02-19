"""
Diagnostic stubs.

The heavy profiling instrumentation (RequestTimingMiddleware,
patch_fernet_decrypt, detailed per-section timing) has been removed because
it added measurable overhead to every request:

  - ``connection.force_debug_cursor = True`` forced Django to record every SQL
    query in memory on every request, even with DEBUG=False.
  - A monkey-patch on ``EncryptedFieldMixin._decrypt`` added timing calls to
    every Fernet decryption.
  - ``timed_section`` counted queries via ``len(connection.queries)`` on entry
    and exit, which is only meaningful when debug cursor is active.

``timed_section`` is kept as a **zero-cost no-op** context manager so that
call sites do not need to be changed.
"""


class timed_section:
    """No-op context manager — retained so call sites don't need changes."""

    __slots__ = ()

    def __init__(self, label, request=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
