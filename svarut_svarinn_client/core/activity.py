"""Allowlisted local events. No free text, account identifiers or file paths."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .. import __version__
from .paths import StorageError

EVENT_TEXT = {
    "app_started": "Klienten startet i TEST. Nettverkskall krever en brukerhandling.",
    "maskinporten_ok": "Maskinporten-test fullført; token er ikke logget.",
    "svarinn_list_ok": "SvarInn-forsendelsesliste hentet; ingen dokumenter lastet ned eller kvittert.",
    "send_started": "Testforsendelse registrert for sending i lokal utgående journal.",
    "send_accepted": "KS aksepterte testforsendelsen; ID er lagret i lokal utgående journal.",
    "send_rejected": "Testforsendelsen ble avvist av KS. Se lokal utgående journal.",
    "send_unknown": "Sendeutfall er ukjent. Manuell avstemming kreves før eventuell ny sending.",
    "status_ok": "Statusoppslag utført mot KS-test.",
    "api_error": "API-handlingen kunne ikke fullføres. Detaljverdier er ikke logget.",
    "session_cleared": "Passordfelt og tokenbuffer tømt for denne økten.",
    "setup_saved": "Lokalt oppsett lagret.",
    "setup_checked": "Lokal oppsettkontroll utført; ingen tilkobling testet.",
    "app_closed": "Klienten avsluttet.",
    "ui_error": "Uventet GUI-feil. Ingen detaljverdier er logget.",
}


class ActivityLog:
    def __init__(self, path: Path):
        self.path = path

    def append(self, event: str) -> None:
        if event not in EVENT_TEXT:
            raise ValueError("Unknown activity event")
        record = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "event": event, "version": __version__, "environment": "TEST"}
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
        except OSError:
            raise StorageError("Aktivitetsloggen kunne ikke skrives. Kontroller lokal datamappe.") from None

    def recent(self, count: int = 300) -> list[tuple[str, str]]:
        if not self.path.exists():
            return []
        rows: deque[tuple[str, str]] = deque(maxlen=count)
        try:
            with self.path.open(encoding="utf-8") as stream:
                for line in stream:
                    if len(line) > 2048:
                        continue
                    try:
                        record = json.loads(line)
                        if not isinstance(record, dict):
                            continue
                        event = record.get("event")
                        stamp = record.get("time")
                        if not isinstance(event, str) or event not in EVENT_TEXT or not isinstance(stamp, str):
                            continue
                        # Parse and reconstruct, never echo arbitrary log fields.
                        parsed = datetime.fromisoformat(stamp)
                        if parsed.tzinfo is None:
                            continue
                        rows.append((parsed.astimezone().isoformat(timespec="seconds"), EVENT_TEXT[event]))
                    except (ValueError, TypeError, KeyError):
                        continue
        except (OSError, UnicodeError):
            raise StorageError("Aktivitetsloggen kunne ikke leses.") from None
        return list(rows)
