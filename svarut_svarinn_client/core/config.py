"""Strict local settings, including per-purpose folders; no secret values stored."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field, fields
import hashlib
from pathlib import Path
import re
from typing import Any
from .paths import StorageError, REPOSITORY_ROOT
from .storage import atomic_json, read_json

@dataclass
class SvarUtSetup:
    api_base_url: str = ''
    account_id: str = ''
    integration_id: str = ''
    maskinporten_client_id: str = ''
    signing_key_file: str = ''
    maskinporten_base_url: str = ''
    maskinporten_key_id: str = ''
    signing_certificate_file: str = ''

@dataclass
class SvarInnSetup:
    api_base_url: str = ''
    service_username: str = ''
    private_key_file: str = ''
    public_certificate_file: str = ''

@dataclass
class LocalFolders:
    received: str = 'received'
    outgoing: str = 'outgoing'
    temp: str = 'temp'
    logs: str = 'logs'
    export: str = 'export'

@dataclass
class DisplaySetup:
    title: str = 'SvarUt/SvarInn Client'
    window_suffix: str = 'TEST'

@dataclass
class Setup:
    schema_version: int = 3
    environment: str = 'TEST'
    svarut: SvarUtSetup = field(default_factory=SvarUtSetup)
    svarinn: SvarInnSetup = field(default_factory=SvarInnSetup)
    folders: LocalFolders = field(default_factory=LocalFolders)
    display: DisplaySetup = field(default_factory=DisplaySetup)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.schema_version < 3:
            result.pop('folders')
            result.pop('display')
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> 'Setup':
        if not isinstance(value, dict):
            raise StorageError('Ukjent oppsettstruktur.')
        if type(value.get('schema_version')) is not int or value['schema_version'] not in (1, 2, 3):
            raise StorageError('Oppsettversjonen er ikke støttet.')
        version = value['schema_version']
        expected = {'schema_version', 'environment', 'svarut', 'svarinn'} | ({'folders', 'display'} if version == 3 else set())
        # Legacy test fixtures may have been generated from the current Setup
        # before their version number was changed to 1/2. Accept only the exact
        # untouched default extension in this case; never silently discard a
        # configured path or application title from a legacy-schema document.
        if version < 3 and set(value) == expected | {'folders', 'display'}:
            default_folders = asdict(LocalFolders())
            default_display = asdict(DisplaySetup())
            legacy_display = {'title': DisplaySetup.title}
            if value['folders'] != default_folders or value['display'] not in (default_display, legacy_display):
                raise StorageError('Eldre oppsett kan ikke inneholde egendefinerte kataloger eller tittel.')
            value = {k: v for k, v in value.items() if k not in ('folders', 'display')}
        if set(value) != expected:
            raise StorageError('Ukjent oppsettstruktur. Originalen er ikke endret.')
        if value['environment'] != 'TEST':
            raise StorageError('Kun TEST er tillatt i denne versjonen.')
        su = value['svarut']
        if version == 1:
            old = {'api_base_url', 'account_id', 'integration_id', 'maskinporten_client_id', 'signing_key_file'}
            if not isinstance(su, dict) or set(su) != old:
                raise StorageError('Ukjente felt i eldre oppsett.')
            su = {**su, 'maskinporten_base_url': '', 'maskinporten_key_id': '', 'signing_certificate_file': ''}
        folders = _group(LocalFolders, value['folders']) if version == 3 else LocalFolders()
        display_data = value['display'] if version == 3 else {'title': DisplaySetup.title}
        if isinstance(display_data, dict) and set(display_data) == {'title'}:
            display_data = {**display_data, 'window_suffix': 'TEST'}
        display = _group(DisplaySetup, display_data)
        if not display.title or len(display.title) > 90 or len(display.window_suffix) > 50:
            raise StorageError('Apptittel må være 1–90 tegn.')
        for name in fields(LocalFolders):
            path = getattr(folders, name.name)
            if not path or len(path) > 1024:
                raise StorageError('Alle kataloger må ha gyldig sti.')
        return cls(schema_version=2 if version < 3 else 3, svarut=_group(SvarUtSetup, su),
                   svarinn=_group(SvarInnSetup, value['svarinn']), folders=folders, display=display)

def _group(kind: type, value: Any) -> Any:
    names = {i.name for i in fields(kind)}
    if not isinstance(value, dict) or set(value) != names:
        raise StorageError('Ukjente oppsettfelt. Passord skal ikke lagres i oppsettet.')
    if any(not isinstance(t, str) or len(t) > 2048 or any(ord(c) < 32 or ord(c) == 127 for c in t) for t in value.values()):
        raise StorageError('Oppsettfelt har ugyldig innhold.')
    return kind(**{k: t.strip() for k, t in value.items()})

def folder_path(root: Path, value: str) -> Path:
    """Resolve relative folders below the data root; reject repository and traversal."""
    if not value or any(ord(c) < 32 for c in value):
        raise StorageError('Katalogstien er ugyldig.')
    candidate = Path(value).expanduser()
    if not candidate.is_absolute() and (candidate.drive or '..' in candidate.parts):
        raise StorageError('Relative kataloger kan ikke gå utenfor dataroten.')
    candidate = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if candidate == REPOSITORY_ROOT or candidate.is_relative_to(REPOSITORY_ROOT):
        raise StorageError('Kataloger for dokumenter og logger må ligge utenfor Git-repoet.')
    if candidate == root:
        raise StorageError('Velg en undermappe eller egen mappe, ikke selve programdataroten.')
    return candidate

class ConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self._fingerprint: str | None = None

    def _hash(self) -> str | None:
        try:
            if not self.path.exists():
                return None
            raw = self.path.read_bytes()
            if len(raw) > 128 * 1024:
                raise StorageError('Oppsettfilen er for stor.')
            return hashlib.sha256(raw).hexdigest()
        except OSError:
            raise StorageError('Kan ikke kontrollere lokal oppsettfil.') from None

    def load_or_create(self) -> Setup:
        if not self.path.exists():
            result = Setup()
            self.save(result)
            return result
        before = self._hash()
        result = Setup.from_dict(read_json(self.path))
        after = self._hash()
        if before != after:
            raise StorageError('Oppsettet ble endret under lesing.')
        self._fingerprint = after
        return result

    def save(self, setup: Setup) -> bool:
        cleaned = Setup.from_dict(setup.to_dict())
        if self._hash() != self._fingerprint:
            raise StorageError('Oppsettfilen er endret utenfor appen. Start på nytt.')
        if self.path.exists() and read_json(self.path) == cleaned.to_dict():
            return False
        atomic_json(self.path, cleaned.to_dict())
        self._fingerprint = self._hash()
        return True
