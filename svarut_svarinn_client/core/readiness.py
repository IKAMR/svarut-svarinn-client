"""Offline completeness checks, not authentication or a production approval."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from .config import Setup

# Public protocol safety policy, NOT an account/configuration default.
# Only the test API base documented by KS on 2026-10-23 is accepted here.
TEST_API_HOSTS = frozenset({"test.svarut.ks.no"})


@dataclass(frozen=True)
class Check:
    area: str
    label: str
    state: str
    detail: str


def valid_test_api_url(value: str) -> bool:
    try:
        parts = urlsplit(value)
        return (parts.scheme == "https" and parts.hostname in TEST_API_HOSTS and
                parts.netloc in TEST_API_HOSTS and parts.username is None and
                parts.password is None and parts.port is None and
                parts.path in {"/api", "/api/"} and not parts.query and not parts.fragment)
    except ValueError:
        return False


def _identifier(area: str, label: str, value: str, uuid: bool = False) -> Check:
    if not value:
        return Check(area, label, "Mangler", "Fylles ut lokalt i Oppsett.")
    if uuid:
        try:
            UUID(value)
        except ValueError:
            return Check(area, label, "Ugyldig", "Forventet UUID-format.")
    return Check(area, label, "Registrert", "Kun lokal formatkontroll; ikke verifisert hos KS.")


def _url(area: str, value: str) -> Check:
    if not value:
        return Check(area, "API-base-URL", "Mangler", "Bruk API-adressen i docs/KS-API.md, ikke portaladressen.")
    if not valid_test_api_url(value):
        return Check(area, "API-base-URL", "Ugyldig", "Bare dokumentert HTTPS-testadresse tillates.")
    return Check(area, "API-base-URL", "Registrert", "Testadresse gjenkjent; ingen tilkobling utført.")


def _file(area: str, label: str, value: str) -> Check:
    if not value:
        return Check(area, label, "Mangler", "Velg en eksisterende lokal fil.")
    try:
        path = Path(value).expanduser()
        valid = path.is_absolute() and path.is_file()
    except (OSError, ValueError):
        valid = False
    if not valid:
        return Check(area, label, "Ugyldig", "Filen finnes ikke, eller stien er ikke absolutt.")
    return Check(area, label, "Registrert", "Kun filens eksistens er kontrollert, ikke nøkkel eller sertifikat.")


def inspect_setup(setup: Setup) -> list[Check]:
    su, si = setup.svarut, setup.svarinn
    return [
        _url("SvarUt", su.api_base_url),
        _identifier("SvarUt", "Konto-ID", su.account_id, uuid=True),
        _identifier("SvarUt", "Integrasjons-ID", su.integration_id, uuid=True),
        _identifier("SvarUt", "Maskinporten klient-ID", su.maskinporten_client_id),
        _file("SvarUt", "Signeringsnøkkel / sertifikatfil", su.signing_key_file),
        Check("SvarUt", "Autentisering og sending", "Ikke implementert", "Maskinporten og hemmelighetshåndtering kommer i senere increment."),
        _url("SvarInn", si.api_base_url),
        _identifier("SvarInn", "Service-brukernavn", si.service_username),
        _file("SvarInn", "Privat PEM-nøkkel", si.private_key_file),
        _file("SvarInn", "Offentlig PEM-sertifikat", si.public_certificate_file),
        Check("SvarInn", "Mottak og kvittering", "Ikke implementert", "Service-passord, dekryptering og varig mottak er ikke testet."),
    ]
