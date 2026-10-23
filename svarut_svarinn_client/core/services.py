"""Shared application layer. Real KS operations are deliberately unavailable."""
from __future__ import annotations

from dataclasses import dataclass

from .activity import ActivityLog
from .config import ConfigStore, Setup
from .paths import AppPaths, StorageError
from .readiness import Check, inspect_setup


class OperationUnavailable(RuntimeError):
    pass


class KsGateway:
    """Fail closed even when called without a GUI. No HTTP client in a1."""

    @staticmethod
    def _blocked() -> None:
        raise OperationUnavailable("API-operasjoner er ikke implementert i denne versjonen.")

    def send(self) -> None:
        self._blocked()

    def status(self) -> None:
        self._blocked()

    def receive(self) -> None:
        self._blocked()

    def acknowledge(self) -> None:
        self._blocked()


@dataclass(frozen=True)
class SaveResult:
    changed: bool
    warning: str = ""


class AppService:
    def __init__(self, paths: AppPaths):
        paths.prepare()
        self.paths = paths
        self.store = ConfigStore(paths.setup)
        self.setup = self.store.load_or_create()
        self.activity = ActivityLog(paths.activity)
        self.gateway = KsGateway()

    def save(self, candidate: Setup) -> SaveResult:
        cleaned = Setup.from_dict(candidate.to_dict())
        changed = self.store.save(cleaned)
        self.setup = cleaned
        warning = ""
        if changed:
            try:
                self.activity.append("setup_saved")
            except StorageError:
                # Setup is already committed. Do not report it as a failed save.
                warning = "Oppsettet er lagret, men hendelsen kunne ikke skrives til aktivitetsloggen."
        return SaveResult(changed, warning)

    def inspect(self, candidate: Setup | None = None) -> list[Check]:
        return inspect_setup(candidate or self.setup)
