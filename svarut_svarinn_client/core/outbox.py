"""Small local SQLite send journal. No document contents or credentials."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3

from .network import ApiError
from .paths import StorageError


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class OutboxStore:
    def __init__(self, path: Path):
        self.path = path
        try:
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(path, os.O_CREAT | os.O_WRONLY, 0o600)
            os.close(fd)
            with self._db() as db:
                version = db.execute('PRAGMA user_version').fetchone()[0]
                if version not in (0, 1):
                    raise StorageError("Utgående journal har en ukjent versjon. Originalen beholdes.")
                db.execute("""CREATE TABLE IF NOT EXISTS sends (
                    reference TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                    account_id TEXT NOT NULL, api_base TEXT NOT NULL,
                    recipient TEXT NOT NULL, recipient_name TEXT NOT NULL,
                    title TEXT NOT NULL, filename TEXT NOT NULL, sha256 TEXT NOT NULL,
                    created TEXT NOT NULL, updated TEXT NOT NULL,
                    state TEXT NOT NULL, remote_id TEXT NOT NULL DEFAULT '',
                    ks_status TEXT NOT NULL DEFAULT '', status_time TEXT NOT NULL DEFAULT '',
                    http_status INTEGER)""")
                db.execute('CREATE INDEX IF NOT EXISTS sends_fingerprint ON sends(fingerprint)')
                db.execute('PRAGMA user_version=1')
        except OSError:
            raise StorageError("Kan ikke opprette lokal utgående journal.") from None

    @contextmanager
    def _db(self):
        connection = None
        try:
            connection = sqlite3.connect(self.path, timeout=5)
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA synchronous=FULL')
            with connection:
                yield connection
        except sqlite3.Error:
            raise StorageError("Utgående journal kunne ikke leses eller lagres. Ikke send på nytt uten avstemming.") from None
        finally:
            if connection is not None:
                connection.close()

    def recover(self) -> None:
        # Called once by the process owner while holding the runtime instance lock.
        with self._db() as db:
            db.execute("UPDATE sends SET state='UNKNOWN',updated=? WHERE state='SENDING'", (stamp(),))

    def begin(self, *, reference: str, fingerprint: str, account_id: str, api_base: str,
              recipient: str, recipient_name: str, title: str, filename: str, sha256: str) -> None:
        now = stamp()
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT reference FROM sends WHERE fingerprint=? AND state IN ('SENDING','UNKNOWN','ACCEPTED') LIMIT 1", (fingerprint,)).fetchone()
            if row:
                raise ApiError("En identisk testforsendelse er allerede registrert. Se utgående journal; ikke send på nytt ved ukjent utfall. Endre tittelen for en bevisst ny test.")
            db.execute('INSERT INTO sends(reference,fingerprint,account_id,api_base,recipient,recipient_name,title,filename,sha256,created,updated,state) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (reference,fingerprint,account_id,api_base,recipient,recipient_name,title,filename,sha256,now,now,'SENDING'))

    def outcome(self, reference: str, state: str, *, remote_id: str = '', http_status: int | None = None) -> None:
        if state not in ('UNKNOWN', 'REJECTED', 'ACCEPTED'):
            raise ValueError('Invalid state')
        with self._db() as db:
            cursor = db.execute('UPDATE sends SET state=?,remote_id=?,http_status=?,updated=? WHERE reference=?',
                               (state,remote_id,http_status,stamp(),reference))
            if cursor.rowcount != 1:
                raise StorageError("Lokal forsendelsesreferanse mangler i journalen.")

    def status(self, account_id: str, remote_id: str, value: str, changed_at: str) -> None:
        with self._db() as db:
            db.execute('UPDATE sends SET ks_status=?,status_time=?,updated=? WHERE account_id=? AND remote_id=?',
                       (value,changed_at,stamp(),account_id,remote_id))

    def recent(self, limit: int = 100) -> list[dict]:
        with self._db() as db:
            return [dict(row) for row in db.execute('SELECT * FROM sends ORDER BY created DESC, rowid DESC LIMIT ?', (limit,))]
