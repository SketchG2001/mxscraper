"""Shared FastAPI dependencies."""

from __future__ import annotations

import uuid

from services.mx_api import MXPlayerAPI

_api_instance: MXPlayerAPI | None = None


def get_api() -> MXPlayerAPI:
    """Singleton MXPlayerAPI instance (one per process, random userid)."""
    global _api_instance
    if _api_instance is None:
        _api_instance = MXPlayerAPI(userid=str(uuid.uuid4()))
    return _api_instance
