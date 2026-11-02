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


def receipt_info(root: Path, shipment: str) -> dict:
    """Read-only inventory. Existing and legacy data are never repaired implicitly."""
    shipment = uuid_text(shipment, 'Forsendelses-ID')
    folder = root / shipment
    if not folder.exists():
        return {'exists': False, 'path': str(folder), 'attempts': [], 'legacy': False, 'status': 'NEW'}
    if not folder.is_dir() or folder.is_symlink():
        return {'exists': True, 'path': str(folder), 'attempts': [], 'legacy': False, 'status': 'UNKNOWN'}
    legacy = any((folder / x).exists() for x in ('metadata.json', 'forsendelse.cms', 'verification.json', 'forsendelse.zip'))
    attempts = []
    unknown = []
    for child in sorted(folder.iterdir()):
        if child.name in ('metadata.json','forsendelse.cms','verification.json','forsendelse.zip','forsendelse.pdf','forsendelse.decrypted.bin','documents'):
            continue
        if child.name.startswith('attempt-') and len(child.name) == 11 and child.name[8:].isdigit() and child.is_dir() and not child.is_symlink():
            attempts.append({'name': child.name, 'path': str(child), 'status': _receipt_status(child)})
        else:
            unknown.append(child.name)
    status = 'UNKNOWN' if unknown or (not legacy and not attempts) else (
        attempts[-1]['status'] if attempts else _receipt_status(folder))
    return {'exists': True, 'path': str(folder), 'attempts': attempts, 'legacy': legacy,
            'status': status, 'unknown': bool(unknown)}


def _receipt_status(folder: Path) -> str:
    try:
        data = json.loads((folder / 'verification.json').read_text(encoding='utf-8'))
        status = data.get('status')
        return status if status in ('VERIFIED','VERIFIED_WITH_WARNINGS','INSPECTION_REQUIRED','DOWNLOADED') else 'UNKNOWN'
    except (OSError, ValueError, TypeError):
        return 'UNKNOWN'


def receipt_folder(root: Path, shipment: str, name: str | None = None) -> Path:
    """Resolve a selected attempt or legacy receipt without accepting arbitrary paths."""
    shipment = uuid_text(shipment, 'Forsendelses-ID')
    target = root / shipment
    if name is None:
        info = receipt_info(root, shipment)
        if info['attempts']:
            return Path(info['attempts'][-1]['path'])
        if (target / 'metadata.json').is_file():
            return target
        raise ApiError('Ingen lagret mottakskontroll er tilgjengelig.')
    if not (name.startswith('attempt-') and len(name)==11 and name[8:].isdigit()):
        raise ApiError('Ugyldig forsøks-ID.')
    return target / name


def receive_delivery(transport, *, base_url: str, authorization: str, metadata: dict,
                     private_key_file: str, public_certificate_file: str, data_root: Path,
                     received_dir: Path | None = None, allow_existing: bool = False) -> dict:
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
    root = received_dir if received_dir is not None else data_root / 'received'
    parent = root / shipment
    info = receipt_info(root, shipment)
    if info['exists'] and not allow_existing:
        raise ApiError('Forsendelsen finnes allerede lokalt. Velg en handling i dialogen.')
    if info.get('status') == 'UNKNOWN' and info['exists'] and not info['attempts'] and not info['legacy']:
        raise ApiError('Ukjent innhold i mottaksmappen. Undersøk mappen før nytt forsøk.')
    # Atomic creation: another writer cannot reserve the same attempt number.
    # Legacy a3 files remain untouched directly under the UUID folder.
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent.mkdir(mode=0o700, exist_ok=True)
        if parent.is_symlink():
            raise ApiError('Mottaksmappen kan ikke være en symbolsk lenke.')
        target = None
        for n in range(1, 10000):
            candidate = parent / f'attempt-{n:03d}'
            try:
                candidate.mkdir(mode=0o700, exist_ok=False)
                target = candidate
                break
            except FileExistsError:
                continue
        if target is None:
            raise ApiError('Maksimalt antall nedlastingsforsøk er nådd.')
    except OSError:
        raise ApiError('Kan ikke opprette egen forsøksmappe; eksisterende filer er beholdt.') from None
    try:
        _write_verification(target, shipment, 'DOWNLOADING', [], 'Nedlasting startet; ingen kvittering sendt.')
        encrypted = _download(transport, base + '/svarinn/v2/forsendelser/' + shipment, authorization)
        if not encrypted or len(encrypted) > MAX_DELIVERY:
            raise ApiError('Tom eller for stor kryptert levering.')
        (target / 'forsendelse.cms').write_bytes(encrypted)
        (target / 'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
        _write_verification(target, shipment, 'DOWNLOADED', [], 'Pakken er lagret; behandling ikke fullfort.')
    except Exception as exc:
        # Preserve attempt evidence and mark failure, never touch an older attempt.
        try:
            _write_verification(target, shipment, 'INSPECTION_REQUIRED', [], 'Nedlasting eller lokal lagring feilet.')
        except OSError:
            pass
        if isinstance(exc, ApiError):
            raise
        raise ApiError('Nedlasting/lagring feilet. Ingen kvittering sendt.') from None

    verified = []
    warnings = []
    try:
        plain = _decrypt(encrypted, Path(private_key_file), Path(public_certificate_file), target)
        plain_path = target / 'forsendelse.zip'  # Name is provisional until format is identified.
        if plain.startswith(b'%PDF-'):
            plain_path.rename(target / 'forsendelse.pdf')
            if len(expected) != 1:
                raise ApiError('Dekryptert PDF, men KS oppgir flere filer. Originalen beholdes.')
            name, (digest, size) = next(iter(expected.items()))
            if hashlib.sha256(plain).hexdigest() != digest:
                raise ApiError('SHA-256 stemmer ikke med KS-metadata.')
            if len(plain) != size:
                warnings.append({'filnavn': name, 'forventet': size, 'faktisk': len(plain), 'avvik': len(plain) - size})
            docs = target / 'documents'
            docs.mkdir(mode=0o700)
            (docs / name).write_bytes(plain)
            verified.append({'filnavn': name, 'sha256': digest, 'bytes': len(plain), 'status': 'HASH_OK', 'expectedBytes': size})
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
                    if total_unpacked > MAX_DELIVERY or member.file_size > MAX_DELIVERY:
                        raise ApiError('Filstorrelse avviker fra KS-metadata.')
                    with archive.open(member) as stream:
                        data = stream.read(member.file_size + 1)
                    if len(data) != member.file_size or hashlib.sha256(data).hexdigest() != digest:
                        raise ApiError('SHA-256 stemmer ikke med KS-metadata.')
                    if len(data) != size:
                        warnings.append({'filnavn': name, 'forventet': size, 'faktisk': len(data), 'avvik': len(data) - size})
                    (docs / name).write_bytes(data)
                    verified.append({'filnavn': name, 'sha256': digest, 'bytes': len(data), 'status': 'HASH_OK', 'expectedBytes': size})
        else:
            plain_path.rename(target / 'forsendelse.decrypted.bin')
            raise ApiError('Dekryptert innhold er verken ZIP eller PDF. Pakken er beholdt for inspeksjon.')
        _write_verification(target, shipment, 'VERIFIED_WITH_WARNINGS' if warnings else 'VERIFIED', verified,
                            'SHA-256 stemmer; KS-storrelse avviker.' if warnings else '', warnings=warnings)
        return {'id': shipment, 'path': str(target), 'files': len(verified), 'warnings': warnings}
    except (ApiError, zipfile.BadZipFile, RuntimeError, OSError, ValueError) as exc:
        # On error, keep encrypted CMS and any decrypted container, but never
        # publish a partly verified documents directory as a valid receipt.
        shutil.rmtree(target / 'documents', ignore_errors=True)
        message = str(exc) if isinstance(exc, ApiError) else 'Behandling av nedlastet pakke feilet.'
        try:
            _write_verification(target, shipment, 'INSPECTION_REQUIRED', [], message)
        except OSError:
            raise ApiError('Nedlastet pakke er lagret, men kontrollrapporten kunne ikke oppdateres. Sjekk mottaksmappen.') from None
        raise ApiError(message + ' Originalpakken er beholdt i ' + str(target) + '. Ingen kvittering sendt.') from None


def _write_verification(folder: Path, shipment: str, status: str, files: list, note: str = '',
                        warnings: list | None = None) -> None:
    """Only app-owned diagnostics; no server error bodies or credential content."""
    report = {'forsendelseId': shipment, 'status': status, 'acknowledged': False,
              'updatedUtc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'files': files, 'warnings': warnings or [], 'note': note}
    temporary = folder / 'verification.json.tmp'
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(folder / 'verification.json')


def recheck_saved_receipt(folder: Path, *, expected_id: str) -> dict:
    """Offline integrity recheck of a previously saved a3 CMS/ZIP receipt.

    No HTTP, decryption, or acknowledgement. Never changes original CMS/ZIP.
    """
    shipment = uuid_text(expected_id, 'Forsendelses-ID')
    if (folder.name != shipment and not (folder.name.startswith('attempt-') and folder.parent.name == shipment)) or not folder.is_dir() or folder.is_symlink():
        raise ApiError('Lokal mottaksmappe finnes ikke.')
    try:
        metadata = json.loads((folder / 'metadata.json').read_text(encoding='utf-8'))
        if uuid_text(metadata.get('id'), 'Forsendelses-ID') != shipment:
            raise ApiError('Metadata har en annen forsendelses-ID.')
        fields = metadata.get('filer')
        if not isinstance(fields, list) or not fields or len(fields) > MAX_FILES:
            raise ApiError('Ugyldig filliste i lagrede metadata.')
        expected = {}
        for field in fields:
            name = _safe_name(field.get('filnavn'))
            sha = field.get('hash')
            size = field.get('storrelse')
            if (name in expected or not isinstance(sha, str) or len(sha) != 64 or
                any(c not in '0123456789abcdefABCDEF' for c in sha) or
                type(size) is not int or size < 0 or size > MAX_DELIVERY):
                raise ApiError('Ugyldig filmetadata for lokal kontroll.')
            expected[name] = (sha.lower(), size)
        zip_path = folder / 'forsendelse.zip'
        if not zip_path.is_file() or zip_path.stat().st_size > MAX_DELIVERY:
            raise ApiError('Lagret dekryptert ZIP mangler. Original CMS beholdes.')
        actual = []
        warnings = []
        buffer = {}
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.infolist()
            if len(members) != len(expected):
                raise ApiError('Antall ZIP-dokumenter avviker fra metadata.')
            total = 0
            for member in members:
                name = _safe_name(member.filename)
                if name not in expected or name in buffer or member.is_dir() or member.flag_bits & 1:
                    raise ApiError('Uventet ZIP-oppforing.')
                total += member.file_size
                if total > MAX_DELIVERY:
                    raise ApiError('Mottaket overstiger maksimal tillatt størrelse.')
                with archive.open(member) as src:
                    raw = src.read(member.file_size + 1)
                digest, expected_size = expected[name]
                if len(raw) != member.file_size or hashlib.sha256(raw).hexdigest() != digest:
                    raise ApiError('SHA-256-integritet feilet. Ingen dokumenter overskrives.')
                if len(raw) != expected_size:
                    warnings.append({'filnavn': name, 'forventet': expected_size, 'faktisk': len(raw),
                                     'avvik': len(raw) - expected_size})
                actual.append({'filnavn': name, 'sha256': digest, 'bytes': len(raw),
                               'expectedBytes': expected_size, 'status': 'HASH_OK'})
                buffer[name] = raw
        documents = folder / 'documents'
        if documents.is_symlink():
            raise ApiError('Dokumentmappen er en symbolsk lenke. Kontrollen er stoppet.')
        if documents.exists() and any(documents.iterdir()):
            # Read-only verification: a completed receipt can be checked again.
            if {item.name for item in documents.iterdir()} != set(buffer):
                raise ApiError('Dokumentmappen avviker fra ZIP. Ingen filer endres.')
            for name, data in buffer.items():
                actual_file = documents / name
                if not actual_file.is_file() or actual_file.is_symlink() or actual_file.read_bytes() != data:
                    raise ApiError('Eksisterende dokument avviker fra ZIP. Ingen filer endres.')
        else:
            documents.mkdir(mode=0o700, exist_ok=True)
            for name, data in buffer.items():
                with (documents / name).open('xb') as file:
                    file.write(data)
        status = 'VERIFIED_WITH_WARNINGS' if warnings else 'VERIFIED'
        _write_verification(folder, shipment, status, actual,
                            'SHA-256 stemmer; KS-storrelse avviker.' if warnings else '', warnings=warnings)
        return {'id': shipment, 'path': str(folder), 'files': len(actual), 'warnings': warnings}
    except ApiError:
        raise
    except (OSError, ValueError, TypeError, zipfile.BadZipFile, RuntimeError):
        raise ApiError('Lokal kontroll kunne ikke fullfores. Original CMS og ZIP beholdes.') from None
