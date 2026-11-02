"""SvarInn V2: bounded CMS download/decryption and verified local receipt. No ACK."""
from __future__ import annotations

import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

from .network import ApiError, test_base, uuid_text, http_error, TIMEOUT_SECONDS
from urllib.request import Request
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
import ssl
import socket
import time

MAX_DELIVERY = 200 * 1024 * 1024
MAX_FILES = 500


def _openssl() -> str:
    found = shutil.which('openssl')
    candidates = [found, r'C:\Program Files\OpenSSL-Win64\bin\openssl.exe',
                  r'C:\Program Files (x86)\OpenSSL-Win32\bin\openssl.exe']
    for item in candidates:
        if item and Path(item).is_file():
            return item
    raise ApiError('OpenSSL ble ikke funnet. Installer OpenSSL eller legg openssl.exe i PATH.')


def _safe_name(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 240:
        raise ApiError('Ugyldig filnavn i forsendelsen.')
    if value in ('.', '..') or any(c in value for c in '/\\:') or any(ord(c) < 32 for c in value):
        raise ApiError('Utrygt filnavn i forsendelsen; utpakking stoppet.')
    return value


def _decrypt(encrypted: bytes, private_key: Path, certificate: Path, staging: Path) -> bytes:
    if not private_key.is_file() or not certificate.is_file():
        raise ApiError('Velg eksisterende privat PEM-nokkel og offentlig sertifikat i Oppsett.')
    encrypted_file = staging / 'forsendelse.cms'
    zip_file = staging / 'forsendelse.zip'
    encrypted_file.write_bytes(encrypted)
    command = [_openssl(), 'cms', '-decrypt', '-binary', '-inform', 'DER',
               '-in', str(encrypted_file), '-recip', str(certificate),
               '-inkey', str(private_key), '-out', str(zip_file)]
    try:
        result = subprocess.run(command, capture_output=True, timeout=120, check=False,
                                stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        raise ApiError('Dekryptering kunne ikke gjennomfores. Ingen nokkeldata logget.') from None
    if result.returncode != 0:
        raise ApiError('CMS-dekryptering feilet. Kontroller at privat nokkel samsvarer med sertifikatet.')
    if not zip_file.is_file() or zip_file.stat().st_size > MAX_DELIVERY:
        raise ApiError('Dekryptert levering mangler eller overstiger 200 MiB.')
    return zip_file.read_bytes()


def _safe_ks_hint(raw: bytes) -> str:
    """Classify KS diagnostics without exposing untrusted error text or secrets.

    A response may contain personally identifying fields, document names or even
    credentials. Only return a fixed application-owned hint; never echo raw JSON.
    """
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (UnicodeError, ValueError):
        return ''
    if not isinstance(payload, dict):
        return ''
    values = [payload.get(key) for key in ('feilmelding', 'message', 'detail', 'error_description')]
    content = ' '.join(value.casefold()[:2000] for value in values if isinstance(value, str))
    if any(word in content for word in ('sertifikat', 'certificate', 'krypter', 'encrypt', 'public key', 'offentlig nøkkel')):
        return ' KS meldte et mulig problem med kryptering eller mottakersertifikat.'
    if any(word in content for word in ('tilgang', 'permission', 'authoriz', 'unauthoriz')):
        return ' KS meldte et mulig tilgangsproblem for mottakersystemet.'
    if any(word in content for word in ('forsendelse', 'shipment', 'not found')):
        return ' KS meldte et mulig problem med forsendelsen eller dens status.'
    return ''


def _download(transport, url: str, authorization: str) -> bytes:
    """Strictly scoped binary GET; legacy JSON transport continues blocking binary URLs."""
    prefix = 'https://test.svarut.ks.no/api/svarinn/v2/forsendelser/'
    if not url.startswith(prefix) or urlsplit(url).query or urlsplit(url).fragment:
        raise ApiError('Ugyldig nedlastingsadresse.')
    uuid_text(url.removeprefix(prefix), 'Forsendelses-ID')
    request = Request(url, headers={'Authorization': authorization,
                    'Accept': '*/*',
                    'User-Agent': 'SvarUtSvarInnClient'}, method='GET')
    try:
        with transport._opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.geturl() != url or response.status != 200:
                raise ApiError('SvarInn returnerte uventet HTTP-respons eller omdirigering.')
            chunks, size = [], 0
            started = time.monotonic()
            while True:
                chunk = response.read(min(65536, MAX_DELIVERY + 1 - size))
                size += len(chunk)
                if size > MAX_DELIVERY or time.monotonic() - started > 180:
                    raise ApiError('Nedlastingen overskred grensen for storrelse eller tid.')
                if not chunk:
                    return b''.join(chunks)
                chunks.append(chunk)
    except HTTPError as exc:
        try:
            data = exc.read(65536)
        except OSError:
            data = b''
        finally:
            exc.close()
        error = http_error(exc.code, data)
        # Add only a fixed, classified hint. Do not disclose raw server text.
        hint = _safe_ks_hint(data)
        raise ApiError(str(error) + hint + ' Fase: nedlasting (ingen fil mottatt).', status=exc.code) from None
    except (OSError, URLError, ssl.SSLError, socket.timeout, TimeoutError):
        raise ApiError('SvarInn-nedlasting feilet. Ingen raa respons eller legitimasjon logget.') from None


def receive_delivery(transport, *, base_url: str, authorization: str, metadata: dict,
                     private_key_file: str, public_certificate_file: str, data_root: Path) -> dict:
    """No acknowledgement request is ever sent. Metadata comes from fresh KS list."""
    shipment = uuid_text(metadata.get('id'), 'Forsendelses-ID')
    expected_files = metadata.get('filer')
    if not isinstance(expected_files, list) or not expected_files or len(expected_files) > MAX_FILES:
        raise ApiError('Ufullstendig eller for stor filliste fra KS.')
    expected = {}
    for entry in expected_files:
        if not isinstance(entry, dict):
            raise ApiError('Ugyldige filmetadata fra KS.')
        name = _safe_name(entry.get('filnavn'))
        digest = entry.get('hash')
        size = entry.get('storrelse')
        if name in expected or not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdefABCDEF' for c in digest):
            raise ApiError('Manglende eller ugyldig SHA-256 fra KS.')
        if type(size) is not int or not 0 <= size <= MAX_DELIVERY:
            raise ApiError('Ugyldig filstorrelse fra KS.')
        expected[name] = (digest.lower(), size)
    base = test_base(base_url)
    root = data_root / 'received'
    target = root / shipment
    if target.exists():
        raise ApiError('Denne forsendelsen finnes allerede lokalt. Ingen overskriving; kontroller mottaksmappen.')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    # A successful HTTP download is evidence and must survive later failures.
    # Create a private staging directory; publish the raw delivery atomically
    # before any CMS processing. No automatic retries or overwrites.
    stage = Path(tempfile.mkdtemp(prefix='.incoming-', dir=root))
    published = False
    try:
        encrypted = _download(transport, base + '/svarinn/v2/forsendelser/' + shipment, authorization)
        if not encrypted or len(encrypted) > MAX_DELIVERY:
            raise ApiError('Tom eller for stor kryptert levering.')
        (stage / 'forsendelse.cms').write_bytes(encrypted)
        (stage / 'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
        _write_verification(stage, shipment, 'DOWNLOADED', [], 'Pakken er lagret; behandling ikke fullfort.')
        stage.rename(target)
        published = True
    except (OSError, ValueError):
        raise ApiError('Kunne ikke lagre nedlastet leveranse. Ingen mottakskvittering sendt.') from None
    finally:
        if not published:
            shutil.rmtree(stage, ignore_errors=True)

    verified = []
    try:
        plain = _decrypt(encrypted, Path(private_key_file), Path(public_certificate_file), target)
        plain_path = target / 'forsendelse.zip'  # Name is provisional until format is identified.
        if plain.startswith(b'%PDF-'):
            plain_path.rename(target / 'forsendelse.pdf')
            if len(expected) != 1:
                raise ApiError('Dekryptert PDF, men KS oppgir flere filer. Originalen beholdes.')
            name, (digest, size) = next(iter(expected.items()))
            if len(plain) != size or hashlib.sha256(plain).hexdigest() != digest:
                raise ApiError('Dekryptert PDF samsvarer ikke med KS sin SHA-256 eller filstorrelse.')
            docs = target / 'documents'
            docs.mkdir(mode=0o700)
            (docs / name).write_bytes(plain)
            verified.append({'filnavn': name, 'sha256': digest, 'bytes': size, 'status': 'VERIFIED'})
        elif zipfile.is_zipfile(io.BytesIO(plain)):
            docs = target / 'documents'
            docs.mkdir(mode=0o700)
            with zipfile.ZipFile(io.BytesIO(plain)) as archive:
                members = archive.infolist()
                if len(members) != len(expected):
                    raise ApiError('Antall dokumenter i ZIP samsvarer ikke med KS-metadata.')
                seen = set()
                total_unpacked = 0
                for member in members:
                    name = _safe_name(member.filename)
                    if member.is_dir() or name not in expected or name in seen or member.flag_bits & 1:
                        raise ApiError('Uventet, duplisert eller kryptert ZIP-oppforing.')
                    seen.add(name)
                    digest, size = expected[name]
                    total_unpacked += member.file_size
                    if total_unpacked > MAX_DELIVERY or member.file_size != size or member.file_size > MAX_DELIVERY:
                        raise ApiError('Filstorrelse avviker fra KS-metadata.')
                    with archive.open(member) as stream:
                        data = stream.read(size + 1)
                    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
                        raise ApiError('SHA-256 eller filstorrelse stemmer ikke med KS-metadata.')
                    (docs / name).write_bytes(data)
                    verified.append({'filnavn': name, 'sha256': digest, 'bytes': size, 'status': 'VERIFIED'})
        else:
            plain_path.rename(target / 'forsendelse.decrypted.bin')
            raise ApiError('Dekryptert innhold er verken ZIP eller PDF. Pakken er beholdt for inspeksjon.')
        _write_verification(target, shipment, 'VERIFIED', verified)
        return {'id': shipment, 'path': str(target), 'files': len(verified)}
    except (ApiError, zipfile.BadZipFile, RuntimeError, OSError, ValueError) as exc:
        # On error, keep encrypted CMS and any decrypted container, but never
        # publish a partly verified documents directory as a valid receipt.
        shutil.rmtree(target / 'documents', ignore_errors=True)
        message = str(exc) if isinstance(exc, ApiError) else 'Behandling av nedlastet pakke feilet.'
        try:
            _write_verification(target, shipment, 'INSPECTION_REQUIRED', [], message)
        except OSError:
            raise ApiError('Nedlastet pakke er lagret, men kontrollrapporten kunne ikke oppdateres. Sjekk mottaksmappen.') from None
        raise ApiError(message + ' Originalpakken er lagret lokalt under received/' + shipment + '. Ingen kvittering sendt.') from None


def _write_verification(folder: Path, shipment: str, status: str, files: list, note: str = '') -> None:
    """Only app-owned diagnostics; no server error bodies or credential content."""
    report = {'forsendelseId': shipment, 'status': status, 'acknowledged': False,
              'updatedUtc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'files': files, 'note': note}
    temporary = folder / 'verification.json.tmp'
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(folder / 'verification.json')
