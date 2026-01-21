"""
Core module initialization.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)


# Enable WAL mode for SQLite to prevent "database is locked" errors
def enable_sqlite_wal(sender, connection, **kwargs):
    """Enable WAL mode for SQLite connections for better concurrency."""
    if connection.vendor == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")


# Connect the signal
from django.db.backends.signals import connection_created
connection_created.connect(enable_sqlite_wal)
