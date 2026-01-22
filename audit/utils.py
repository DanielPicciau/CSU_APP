"""
Helpers for writing audit log entries.
"""

from typing import Optional

from .models import AuditLog


def log_event(
    action: str,
    target_type: str,
    target_id: str = "",
    actor=None,
    metadata: Optional[dict] = None,
) -> AuditLog:
    """Create an audit log entry."""
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else "",
        metadata_json=metadata or {},
    )
