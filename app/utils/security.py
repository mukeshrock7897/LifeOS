from __future__ import annotations

from pathlib import Path

from app.config import settings


def is_path_allowed(path: Path) -> bool:
    """Return True iff `path` is inside one of the allowed base dirs."""
    try:
        resolved = path.expanduser().resolve()
    except Exception:
        resolved = path.expanduser().absolute()

    for base in settings.allowed_base_paths:
        try:
            resolved.relative_to(base)
            return True
        except ValueError:
            continue
    return False
