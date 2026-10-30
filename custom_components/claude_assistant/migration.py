"""Pure config-entry migration helpers (no Home Assistant imports, unit-tested directly)."""

from __future__ import annotations

from typing import Any

from .const import (
    AUTH_TYPE_API_KEY,
    CONF_AUTH_TYPE,
    LEGACY_AUTH_TYPE_PERSONAL,
    LEGACY_CONF_SESSION_KEY,
)

# Config entry version written by 1.2.0 (session-key mode removed).
ENTRY_VERSION = 3
# Marker kept in entry data so setup can explain why the entry needs a new API key.
SESSION_MODE_REMOVED = "session_mode_removed"


def strip_session_mode(data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return entry data without any stored claude.ai session key.

    The second value is True when the entry was configured in session-key mode;
    such an entry has no API key and cannot start until it is set up again.
    The input mapping is not modified.
    """
    new = dict(data)
    legacy = new.get(CONF_AUTH_TYPE) == LEGACY_AUTH_TYPE_PERSONAL
    new.pop(LEGACY_CONF_SESSION_KEY, None)
    if legacy:
        new[CONF_AUTH_TYPE] = AUTH_TYPE_API_KEY
        new[SESSION_MODE_REMOVED] = True
    return new, legacy
