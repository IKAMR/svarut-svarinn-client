"""Bounded HTTPS transport. Test endpoints only; no redirects or automatic retry."""
from __future__ import annotations

import json
from http.client import HTTPException
import re
import socket
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler
from uuid import UUID

TEST_API_BASE = "https://test.svarut.ks.no/api"
TEST_MASKINPORTEN_BASE = "https://test.maskinporten.no/"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
TIMEOUT_SECONDS = 30


class ApiError(RuntimeError):
    """Only safe application-owned text and allowlisted diagnostics, never raw bodies."""
    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


def uuid_text(value: str, label: str) -> str:
    try:
        # Reject alternate UUID spellings in paths, but accept upper case input.
        if not isinstance(value, str) or len(value) != 36:
            raise ValueError
        return str(UUID(value))
    except (ValueError, AttributeError):
        raise ApiError(f"{label} må være en gyldig UUID.") from None


def test_base(value: str, *, maskinporten: bool = False) -> str:
    expected = TEST_MASKINPORTEN_BASE if maskinporten else TEST_API_BASE
    if not isinstance(value, str) or value not in {expected, expected.rstrip('/') + '/'}:
        # The issuer trailing slash is required for Maskinporten; accept a user
        # entering the origin without it and normalize before constructing JWT.
        if not (maskinporten and value == expected.rstrip('/')):
            raise ApiError("Ugyldig testadresse. Bruk 'Fyll tomme testadresser' i Oppsett. Produksjon er sperret.")
    return expected


def validate_target(method: str, url: str) -> None:
    """Protect even direct calls to the transport; no arbitrary URL with credentials."""
    try:
        parts = urlsplit(url)
    except (ValueError, TypeError):
        raise ApiError("Ugyldig API-adresse.") from None
    if parts.query or parts.fragment or parts.username or parts.password:
        raise ApiError("URL med ekstra parametre eller legitimasjon er sperret.")
    if method == 'POST' and url == TEST_MASKINPORTEN_BASE + 'token':
        return
    if parts.scheme != 'https' or parts.netloc != 'test.svarut.ks.no':
        raise ApiError("Bare godkjente HTTPS-testendepunkter kan kalles.")
    if method == 'GET' and parts.path == '/api/svarinn/v2/forsendelser':
        return
    match = re.fullmatch(r'/api/v3/kontoer/([a-f0-9-]{36})/forsendelser/(organisasjon|status/sok)', parts.path)
    if method == 'POST' and match:
        uuid_text(match[1], "Konto-ID")
        return
    raise ApiError("Denne API-operasjonen er ikke aktivert. Nedlasting og kvittering er sperret.")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def decode_json(raw: bytes):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise ApiError("Serveren returnerte ikke gyldig JSON. Ingen rårespons er logget.") from None


def http_error(status: int, raw: bytes) -> ApiError:
    hints = {
        400: "Forespørselen ble avvist. Kontroller oppsett, rettigheter og testdata.",
        401: "Autentisering avvist. Kontroller servicepassord eller Maskinporten/Fiks-legitimasjon.",
        403: "Tilgang avvist. Kontroller integrasjonens konto-/tjenestetilgang og autorisert organisasjon.",
        404: "Ressursen finnes ikke. Kontroller konto-ID, forsendelses-ID og testoppsett.",
        413: "Forsendelsen er for stor.",
        429: "For mange forespørsler. Vent før et nytt manuelt oppslag; sending gjentas ikke automatisk.",
    }
    hint = "Omdirigering er sperret; legitimasjon er ikke videresendt." if 300 <= status < 400 else hints.get(status, "Serveren kunne ikke fullføre forespørselen.")
    details = []
    try:
        value = decode_json(raw)
        if isinstance(value, dict):
            code = value.get('errorCode')
            if isinstance(code, str) and re.fullmatch(r'[A-Z]{1,10}-[0-9]{4}', code):
                details.append('Feilkode: ' + code)
            error_id = value.get('errorId')
            if isinstance(error_id, str):
                try:
                    details.append('Feil-ID: ' + uuid_text(error_id, 'Feil-ID'))
                except ApiError:
                    pass
            oauth = value.get('error')
            if oauth in ('invalid_grant', 'invalid_client', 'invalid_scope', 'invalid_request', 'unauthorized_client'):
                details.append('Maskinporten: ' + oauth)
    except (ApiError, TypeError):
        pass
    return ApiError(f"HTTP {status}: {hint}" + (' ' + '; '.join(details) if details else ''), status=status)


class HttpsTransport:
    def __init__(self):
        # Default certificate validation incl. OS trust store. Never verify=False.
        self._opener = build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))

    def request(self, method: str, url: str, *, headers: dict[str, str] | None = None,
                body: bytes | None = None):
        validate_target(method, url)
        header = {'Accept': 'application/json', 'User-Agent': 'SvarUtSvarInnClient', **(headers or {})}
        for name, value in header.items():
            if not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise ApiError("Ugyldig verdi i autentiseringsoppsettet.")
        try:
            request = Request(url, data=body, headers=header, method=method)
            with self._opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                # An opener must not silently send credentials to a new location.
                if response.geturl() != url:
                    raise ApiError("Uventet omdirigering i HTTP-transporten.")
                status = response.status
                raw = self._read(response)
                if status != 200:
                    raise http_error(status, raw)
                return decode_json(raw)
        except HTTPError as exc:
            try:
                raw = exc.read(65536)
            except (OSError, ValueError):
                raw = b''
            finally:
                exc.close()
            raise http_error(exc.code, raw) from None
        except (TimeoutError, socket.timeout):
            raise ApiError("Tidsavbrudd mot testmiljøet. Sending gjentas ikke automatisk.") from None
        except ssl.SSLError:
            raise ApiError("TLS-kontroll feilet. Kontroller sertifikater, klokke og eventuell virksomhetsproxy.") from None
        except URLError as exc:
            if isinstance(exc.reason, ssl.SSLError):
                text = "TLS-kontroll feilet. Kontroller sertifikater og eventuell virksomhetsproxy."
            else:
                text = "Kunne ikke kontakte testmiljøet. Kontroller nettverk, DNS, brannmur og proxy."
            raise ApiError(text) from None
        except (OSError, ValueError, UnicodeError, HTTPException):
            raise ApiError("HTTP-kallet kunne ikke fullføres. Ingen råfeil eller legitimasjon er logget.") from None

    @staticmethod
    def _read(response) -> bytes:
        chunks = []
        total = 0
        started = time.monotonic()
        while True:
            data = response.read(min(65536, MAX_RESPONSE_BYTES + 1 - total))
            total += len(data)
            if total > MAX_RESPONSE_BYTES:
                raise ApiError("API-svaret overstiger klientens grense på 4 MiB.")
            if time.monotonic() - started > 60:
                raise ApiError("API-svaret tok for lang tid. Ingen automatisk gjentakelse.")
            if not data:
                return b''.join(chunks)
            chunks.append(data)
