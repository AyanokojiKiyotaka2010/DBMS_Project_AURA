"""Tiny dependency-free time helper (importable without FastAPI / bcrypt)."""
from datetime import datetime, timezone


def now_db() -> datetime:
    """Naive UTC 'now' — what DATETIME columns hold."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
