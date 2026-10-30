"""Shared local application layer with explicit test-only KS operations."""
from __future__ import annotations

from dataclasses import dataclass

from .activity import ActivityLog
from .config import ConfigStore, Setup
from .paths import AppPaths, StorageError
from .readiness import Check, inspect_setup
from .ks_api import TestOperations


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
        self.gateway = TestOperations(paths, activity=self.activity)

    def save(self, candidate: Setup) -> SaveResult:
        cleaned = Setup.from_dict(candidate.to_dict())
        changed = self.store.save(cleaned)
        self.setup = cleaned
        if changed:
            self.gateway.clear_secrets()
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
