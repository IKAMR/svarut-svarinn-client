"""Runtime files live outside the source tree unless an ignored area is chosen."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class StorageError(RuntimeError):
    """Safe, human-readable error; never wrap raw configuration contents."""


@dataclass(frozen=True)
class AppPaths:
    root: Path

    @property
    def setup(self) -> Path:
        return self.root / "setup.json"

    @property
    def ui_state(self) -> Path:
        return self.root / "ui-state.json"

    @property
    def activity(self) -> Path:
        return self.root / "logs" / "activity.jsonl"

    @property
    def lock(self) -> Path:
        return self.root / "runtime.lock"

    def prepare(self) -> None:
        try:
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.activity.parent.mkdir(mode=0o700, exist_ok=True)
        except OSError:
            raise StorageError("Kan ikke opprette lokal datamappe. Kontroller tilgang og ledig plass.") from None


def resolve_paths(override: str | None = None) -> AppPaths:
    configured = override or os.environ.get("SVARUT_SVARINN_HOME")
    if configured:
        root = Path(configured).expanduser().resolve()
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        root = (base / "SvarUtSvarInnClient").resolve()
    else:
        root = (Path.home() / ".local" / "share" / "svarut-svarinn-client").resolve()
    if root == REPOSITORY_ROOT or root.is_relative_to(REPOSITORY_ROOT):
        relative = root.relative_to(REPOSITORY_ROOT)
        if not relative.parts or relative.parts[0] not in {".local", "local-data"}:
            raise StorageError("Velg en datamappe utenfor repoet, eller .local/local-data i repoet.")
    return AppPaths(root)
