"""Shared local application layer with explicit test-only KS operations."""
from __future__ import annotations

from dataclasses import dataclass

from .activity import ActivityLog
from .config import ConfigStore, Setup, folder_path
from .paths import AppPaths, StorageError
from .readiness import Check, inspect_setup
from .a3_operations import DownloadOperations


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
        self.activity = ActivityLog(folder_path(paths.root, self.setup.folders.logs) / 'activity.jsonl')
        self.gateway = DownloadOperations(paths, activity=self.activity)
        self.gateway.received_dir = folder_path(paths.root, self.setup.folders.received)

    def save(self, candidate: Setup) -> SaveResult:
        cleaned = Setup.from_dict(candidate.to_dict())
        for name in ('received', 'outgoing', 'temp', 'logs', 'export'):
            folder_path(self.paths.root, getattr(cleaned.folders, name))
        changed = self.store.save(cleaned)
        self.setup = cleaned
        self.gateway.received_dir = folder_path(self.paths.root, cleaned.folders.received)
        if changed:
            self.gateway.clear_secrets()
            new_log = folder_path(self.paths.root, cleaned.folders.logs) / 'activity.jsonl'
            if new_log != self.activity.path:
                self.activity = ActivityLog(new_log)
                self.gateway.activity = self.activity
        warning = ""
        if changed:
            try:
                self.activity.append("setup_saved")
            except StorageError:
                warning = "Oppsettet er lagret, men hendelsen kunne ikke skrives til aktivitetsloggen."
        return SaveResult(changed, warning)

    def inspect(self, candidate: Setup | None = None) -> list[Check]:
        return inspect_setup(candidate or self.setup)
