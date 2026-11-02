"""Remember an optional data root independently of the configured data root.

An explicit --data-dir or SVARUT_SVARINN_HOME always wins. A newly selected
root is activated at the next startup, with no implicit copying or deletion.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

from .paths import REPOSITORY_ROOT, StorageError


def default_root() -> Path:
    if sys.platform == 'win32':
        return (Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local') / 'SvarUtSvarInnClient').resolve()
    return (Path.home() / '.local' / 'share' / 'svarut-svarinn-client').resolve()


def preference_file() -> Path:
    return default_root() / 'data-root-choice.json'


def validate_root(candidate: str | Path) -> Path:
    if not str(candidate).strip() or any(ord(c) < 32 or ord(c) == 127 for c in str(candidate)):
        raise StorageError('Ugyldig programdatarot.')
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        raise StorageError('Programdatarot må være en absolutt katalogsti.')
    path = path.resolve()
    if path == REPOSITORY_ROOT or path.is_relative_to(REPOSITORY_ROOT):
        relative = path.relative_to(REPOSITORY_ROOT)
        if not relative.parts or relative.parts[0] not in {'.local', 'local-data'}:
            raise StorageError('Velg datamappe utenfor Git-repoet, eller .local/local-data i repoet.')
    return path


def preferred_root() -> Path:
    location = preference_file()
    if not location.exists():
        return default_root()
    try:
        if location.stat().st_size > 4096:
            raise ValueError('too large')
        data = json.loads(location.read_text(encoding='utf-8'))
        if type(data) is not dict or set(data) != {'version', 'root'} or data['version'] != 1:
            raise ValueError('invalid schema')
        return validate_root(data['root'])
    except (OSError, ValueError, TypeError, UnicodeError):
        raise StorageError('Lagret programdatarot er ugyldig. Rett eller fjern data-root-choice.json i standard programdatamappe.') from None


def save_preferred_root(root: str | Path) -> Path:
    from .storage import atomic_json
    path = validate_root(root)
    # Returning to the default needs no existing folder: startup can create it.
    if path == default_root().resolve():
        reset_preferred_root()
        return path
    # Validate access without replacing/migrating existing setup or files.
    if not path.is_dir():
        raise StorageError('Mappen finnes ikke. Opprett og velg mappen før du bytter programdatarot.')
    if not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        raise StorageError('Du mangler tilgang til valgt programdatarot.')
    preference_file().parent.mkdir(parents=True, exist_ok=True)
    atomic_json(preference_file(), {'version': 1, 'root': str(path)})
    return path


def reset_preferred_root() -> Path:
    location = preference_file()
    try:
        location.unlink(missing_ok=True)
    except OSError:
        raise StorageError('Kunne ikke gjenopprette standard programdatarot.') from None
    return default_root()
