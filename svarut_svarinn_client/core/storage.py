"""Atomic local writes and one active process per data directory."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .paths import StorageError

MAX_JSON_BYTES = 128 * 1024


def read_json(path: Path) -> dict[str, Any]:
    try:
        if path.stat().st_size > MAX_JSON_BYTES:
            raise StorageError("Oppsettfilen er for stor. Originalen er ikke endret.")
        # Read a bounded amount even if a different process changes the file.
        with path.open("rb") as stream:
            raw = stream.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            raise StorageError("Oppsettfilen er for stor. Originalen er ikke endret.")
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object)
        if not isinstance(value, dict):
            raise ValueError("object required")
        return value
    except (OSError, ValueError, UnicodeError):
        raise StorageError("Kan ikke lese gyldig JSON-oppsett. Originalen er ikke endret.") from None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    """Replace only after the complete UTF-8 file has been flushed to disk."""
    temporary: Path | None = None
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".pending-", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError:
        raise StorageError("Lagring mislyktes. Forrige oppsett er beholdt dersom det fantes.") from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


class InstanceLock:
    """OS lock: released after a crash; the lock file itself may remain."""

    def __init__(self, path: Path):
        self.path = path
        self._stream = None

    def acquire(self) -> None:
        if self._stream is not None:
            return
        stream = None
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            stream = self.path.open("a+b")
            if self.path.stat().st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._stream = stream
        except OSError:
            if stream is not None:
                stream.close()
            raise StorageError("Datamappen er i bruk eller kan ikke låses. Lukk andre klientvinduer.") from None

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    def __enter__(self) -> "InstanceLock":
        self.acquire()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
