"""Strict local setup schema. No credentials, account defaults or automatic repair."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
import hashlib
from pathlib import Path
from typing import Any

from .paths import StorageError
from .storage import atomic_json, read_json


@dataclass
class SvarUtSetup:
    api_base_url: str = ""
    account_id: str = ""
    integration_id: str = ""
    maskinporten_client_id: str = ""
    signing_key_file: str = ""


@dataclass
class SvarInnSetup:
    api_base_url: str = ""
    service_username: str = ""
    private_key_file: str = ""
    public_certificate_file: str = ""


@dataclass
class Setup:
    schema_version: int = 1
    environment: str = "TEST"
    svarut: SvarUtSetup = field(default_factory=SvarUtSetup)
    svarinn: SvarInnSetup = field(default_factory=SvarInnSetup)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Setup":
        if set(value) != {"schema_version", "environment", "svarut", "svarinn"}:
            raise StorageError("Ukjent oppsettstruktur. Originalen er ikke endret.")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise StorageError("Oppsettversjonen er ikke støttet. Originalen er ikke endret.")
        if value["environment"] != "TEST":
            raise StorageError("Denne versjonen tillater bare TEST. Produksjon er sperret.")
        return cls(svarut=_group(SvarUtSetup, value["svarut"]),
                   svarinn=_group(SvarInnSetup, value["svarinn"]))


def _group(kind: type, value: Any) -> Any:
    names = {item.name for item in fields(kind)}
    if not isinstance(value, dict) or set(value) != names:
        raise StorageError("Ukjente oppsettfelt. Passord skal ikke legges i setup.json.")
    if any(not isinstance(text, str) or len(text) > 2048 or
           any(ord(char) < 32 for char in text) for text in value.values()):
        raise StorageError("Oppsettfelt har ugyldig type eller innhold.")
    return kind(**{key: text.strip() for key, text in value.items()})


class ConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self._fingerprint: str | None = None

    def _hash(self) -> str | None:
        try:
            if not self.path.exists():
                return None
            with self.path.open("rb") as stream:
                raw = stream.read(128 * 1024 + 1)
            if len(raw) > 128 * 1024:
                raise StorageError("Oppsettfilen er for stor.")
            return hashlib.sha256(raw).hexdigest()
        except OSError:
            raise StorageError("Kan ikke kontrollere lokal oppsettfil.") from None

    def load_or_create(self) -> Setup:
        if not self.path.exists():
            result = Setup()
            self.save(result)
            return result
        before = self._hash()
        result = Setup.from_dict(read_json(self.path))
        after = self._hash()
        if before != after:
            raise StorageError("Oppsettet ble endret under lesing. Start klienten på nytt.")
        self._fingerprint = after
        return result

    def save(self, setup: Setup) -> bool:
        cleaned = Setup.from_dict(setup.to_dict())
        if self._hash() != self._fingerprint:
            raise StorageError("Oppsettfilen er endret utenfor appen. Start på nytt før lagring.")
        if self.path.exists() and read_json(self.path) == cleaned.to_dict():
            return False
        atomic_json(self.path, cleaned.to_dict())
        self._fingerprint = self._hash()
        return True
