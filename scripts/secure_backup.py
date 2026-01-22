#!/usr/bin/env python3
"""
Secure backup runner for CSU Tracker.

Creates:
- Encrypted per-user snapshots (from backups.tasks.create_backup_snapshot)
- Optional encrypted SQLite database backups

Designed for PythonAnywhere scheduled tasks (no Celery worker required).
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import fcntl


def _setup_django() -> None:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    import django
    django.setup()


def _get_logger() -> logging.Logger:
    logger = logging.getLogger("secure_backup")
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def _lock_file(lock_path: Path, logger: logging.Logger):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = lock_path.open("a+")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        logger.warning("Backup already running, exiting")
        lock_handle.close()
        return None
    return lock_handle


def _get_backup_dir():
    from django.conf import settings
    base_dir = Path(os.environ.get("CSU_BACKUP_DIR", settings.BASE_DIR / "secure_backups"))
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def _get_backup_fernet():
    from django.conf import settings
    from cryptography.fernet import Fernet, MultiFernet

    backup_key = os.environ.get("BACKUP_ENCRYPTION_KEY")
    if backup_key:
        return Fernet(backup_key.encode())

    keys = getattr(settings, "FERNET_KEYS", None)
    if not keys:
        raise RuntimeError("FERNET_KEYS is not configured")
    if isinstance(keys, str):
        keys = [keys]
    return MultiFernet([
        Fernet(key.encode() if isinstance(key, str) else key)
        for key in keys
    ])


def _encrypt_file(source: Path, dest: Path) -> None:
    fernet = _get_backup_fernet()
    encrypted = fernet.encrypt(source.read_bytes())
    dest.write_bytes(encrypted)
    os.chmod(dest, 0o600)


def _backup_sqlite_database(backup_dir: Path, logger: logging.Logger) -> Path | None:
    from django.conf import settings

    db_settings = settings.DATABASES["default"]
    engine = db_settings.get("ENGINE", "")
    if engine != "django.db.backends.sqlite3":
        logger.warning("DB backup skipped (only sqlite supported in this script)")
        return None

    db_path = Path(db_settings.get("NAME", ""))
    if not db_path.is_absolute():
        db_path = settings.BASE_DIR / db_path
    if not db_path.exists():
        logger.warning("SQLite DB file not found, skipping DB backup")
        return None

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    temp_path = backup_dir / f"db_backup_{timestamp}.sqlite3"
    encrypted_path = backup_dir / f"db_backup_{timestamp}.sqlite3.enc"

    try:
        with sqlite3.connect(db_path) as src, sqlite3.connect(temp_path) as dest:
            src.backup(dest)
        _encrypt_file(temp_path, encrypted_path)
        temp_path.unlink(missing_ok=True)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return encrypted_path


def _backup_user_snapshots(include_all_users: bool, logger: logging.Logger) -> tuple[int, int]:
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from backups.tasks import create_backup_snapshot
    from core.security import hash_sensitive_data
    from subscriptions.entitlements import has_entitlement

    User = get_user_model()
    success = 0
    failed = 0

    for user in User.objects.filter(is_active=True).iterator():
        if not include_all_users and not has_entitlement(user, "cloud_backup"):
            continue
        try:
            result = create_backup_snapshot(user.id)
            if result == "completed":
                success += 1
                logger.info(
                    "Snapshot created for user_id=%s user_hash=%s",
                    user.id,
                    hash_sensitive_data(user.email),
                )
            else:
                failed += 1
                logger.warning(
                    "Snapshot failed for user_id=%s user_hash=%s status=%s",
                    user.id,
                    hash_sensitive_data(user.email),
                    result,
                )
        except Exception as exc:
            failed += 1
            logger.warning(
                "Snapshot error for user_id=%s user_hash=%s error=%s",
                user.id,
                hash_sensitive_data(user.email),
                exc,
            )

    return success, failed


def _prune_snapshots(retention_days: int, logger: logging.Logger) -> int:
    if retention_days <= 0:
        return 0
    from django.utils import timezone
    from backups.models import BackupSnapshot

    cutoff = timezone.now() - timedelta(days=retention_days)
    to_delete = BackupSnapshot.objects.filter(created_at__lt=cutoff)
    count = 0
    for snapshot in to_delete.iterator():
        if snapshot.file:
            snapshot.file.delete(save=False)
        count += 1
    to_delete.delete()
    if count:
        logger.info("Pruned %s old snapshot(s)", count)
    return count


def _prune_db_backups(backup_dir: Path, retention_days: int, logger: logging.Logger) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    deleted = 0
    for path in backup_dir.glob("db_backup_*.sqlite3.enc"):
        mtime = datetime.utcfromtimestamp(path.stat().st_mtime)
        if mtime < cutoff:
            path.unlink(missing_ok=True)
            deleted += 1
    if deleted:
        logger.info("Pruned %s old DB backup file(s)", deleted)
    return deleted


def main() -> int:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description="CSU Tracker secure backups")
    parser.add_argument(
        "--mode",
        choices=["snapshots", "db", "full"],
        default="full",
        help="What to back up (default: full)",
    )
    parser.add_argument(
        "--include-all-users",
        action="store_true",
        help="Back up all active users (not just cloud_backup entitlement)",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.environ.get("CSU_BACKUP_RETENTION_DAYS", "30")),
        help="Retention window in days (default: env CSU_BACKUP_RETENTION_DAYS or 30)",
    )

    args = parser.parse_args()
    _setup_django()
    logger = _get_logger()
    backup_dir = _get_backup_dir()
    lock_handle = _lock_file(backup_dir / ".backup.lock", logger)
    if not lock_handle:
        return 1

    try:
        logger.info("Backup started (mode=%s)", args.mode)
        if args.mode in {"snapshots", "full"}:
            ok, failed = _backup_user_snapshots(args.include_all_users, logger)
            logger.info("Snapshots completed: %s ok, %s failed", ok, failed)

        if args.mode in {"db", "full"}:
            encrypted_path = _backup_sqlite_database(backup_dir, logger)
            if encrypted_path:
                logger.info("DB backup saved to %s", encrypted_path)

        _prune_snapshots(args.retention_days, logger)
        _prune_db_backups(backup_dir, args.retention_days, logger)
        logger.info("Backup finished")
        return 0
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
