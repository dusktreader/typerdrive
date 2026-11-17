"""Provide an atomic write helper."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write(
    path: Path,
    data: bytes,
    *,
    create_only: bool = False,
) -> None:
    """
    Atomically write bytes to a path with private permissions.

    Use a hard link for create-only writes so an existing destination cannot be replaced.
    """
    fd, name = tempfile.mkstemp(prefix=".typerdrive-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if create_only:
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
