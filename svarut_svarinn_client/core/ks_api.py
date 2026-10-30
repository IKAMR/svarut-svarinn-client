"""The initial test operations. No SvarInn download/acknowledgement path exists."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import threading
from uuid import uuid4

from .auth import MaskinportenClient, SessionSecrets
from .config import Setup
from .network import ApiError, HttpsTransport, test_base, uuid_text
from .outbox import OutboxStore
from .paths import AppPaths, StorageError

MAX_PDF_BYTES = 20 * 1024 * 1024  # Client test limit, NOT the KS service limit.


def text_field(value: str, label: str, maximum: int, *, optional: bool = False) -> str:
    if not isinstance(value, str):
        raise ApiError(label + ' har ugyldig type.')
    result = value.strip()
    if (not result and not optional) or len(result) > maximum or any(ord(c) < 32 or ord(c) == 127 for c in result):
        raise ApiError(f"{label}: fyll inn gyldig tekst, maks {maximum} tegn.")
    return result


@dataclass(frozen=True, repr=False)
class SendDraft:
    organization_number: str
    recipient_name: str
    title: str
    pdf_file: str
    shipment_type: str = ''
    test_data_confirmed: bool = False


@dataclass(frozen=True, repr=False)
class PreparedSend:
    metadata: dict = field(repr=False)
    pdf: bytes = field(repr=False)
    filename: str
    sha256: str
    fingerprint: str
    reference: str


def prepare_send(draft: SendDraft, *, account_id: str, api_base: str) -> PreparedSend:
    if draft.test_data_confirmed is not True:
        raise ApiError("Bekreft at mottaker og dokument bare er ufølsomme testdata.")
    org = text_field(draft.organization_number, 'Testorganisasjonsnummer', 9)
    if not re.fullmatch('[0-9]{9}', org):
        raise ApiError("Testorganisasjonsnummer må ha ni sifre. Bruk mottaker fra Tenor.")
    name = text_field(draft.recipient_name, 'Mottakernavn', 100)
    title = text_field(draft.title, 'Tittel', 1000)
    route = text_field(draft.shipment_type, 'Forsendelsestype', 100, optional=True)
    try:
        path = Path(draft.pdf_file).expanduser()
        if not draft.pdf_file or not path.is_absolute() or not path.is_file() or path.suffix.lower() != '.pdf':
            raise ValueError
        filename = text_field(path.name, 'Filnavn', 226)
        if any(c in filename for c in '*:"\\/<>|?'):
            raise ValueError
        with path.open('rb') as stream:
            pdf = stream.read(MAX_PDF_BYTES + 1)
        if not pdf.startswith(b'%PDF-') or len(pdf) > MAX_PDF_BYTES:
            raise ValueError
    except (OSError, ValueError):
        raise ApiError("Velg en PDF-fil med gyldig filnavn og størrelse inntil 20 MiB. Kun enkel filsignatur kontrolleres lokalt.") from None
    digest = hashlib.sha256(pdf).hexdigest()
    metadata = {'tittel': title, 'mottaker': {'navn': name, 'digitalId': org},
                'dokumenter': [{'filnavn': filename, 'mimeType': 'application/pdf'}],
                'avgivendeSystem': 'SvarUtSvarInnClient', 'kunDigitalLevering': True}
    if route:
        metadata['forsendelsestype'] = route
    fingerprint = hashlib.sha256(json.dumps([account_id, api_base, metadata, digest], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    reference = str(uuid4())
    metadata['eksternReferanse'] = reference
    metadata['korrelasjonsid'] = reference
    return PreparedSend(metadata, pdf, filename, digest, fingerprint, reference)


def multipart(prepared: PreparedSend) -> tuple[str, bytes]:
    boundary = 'svarut-' + uuid4().hex
    head = (f'--{boundary}\r\nContent-Disposition: form-data; name="forsendelse"\r\n'
            'Content-Type: application/json; charset=utf-8\r\n\r\n').encode('ascii')
    document_head = (f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="dokumenter"; filename="{prepared.filename}"\r\n'
                     'Content-Type: application/pdf\r\n\r\n').encode('utf-8')
    body = head + json.dumps(prepared.metadata, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    body += document_head + prepared.pdf + f'\r\n--{boundary}--\r\n'.encode('ascii')
    return 'multipart/form-data; boundary=' + boundary, body


def display_text(value, maximum: int = 1000) -> str:
    # Unknown metadata fields are ignored, not rejected. Control characters are
    # not rendered in a GUI table; values are never used as URLs or filenames.
    if not isinstance(value, str):
        return ''
    return ''.join(c if ord(c) >= 32 and ord(c) != 127 else ' ' for c in value)[:maximum]


class TestOperations:
    __test__ = False

    def __init__(self, paths: AppPaths, *, transport=None, auth=None, activity=None):
        self.transport = transport or HttpsTransport()
        self.auth = auth or MaskinportenClient(self.transport)
        self.outbox = OutboxStore(paths.root / 'outbox.sqlite3')
        self.outbox.recover()
        self.activity = activity
        self._send_lock = threading.Lock()

    def _log(self, event: str) -> None:
        if self.activity:
            try:
                self.activity.append(event)
            except StorageError:
                # Never misreport an accepted send as failed because a separate
                # diagnostic log is unavailable; the send journal is mandatory.
                pass

    @staticmethod
    def _setup(setup: Setup) -> Setup:
        return Setup.from_dict(setup.to_dict())

    def clear_secrets(self) -> None:
        self.auth.clear()

    def authenticate(self, setup: Setup, secrets: SessionSecrets) -> str:
        setup = self._setup(setup)
        self.auth.token(setup.svarut, secrets, fresh=True)
        self._log('maskinporten_ok')
        return "Maskinporten-token hentet. Fiks-kontotilgang er ikke bekreftet før et SvarUt-kall lykkes."

    def list_incoming(self, setup: Setup, secrets: SessionSecrets) -> list[dict]:
        config = self._setup(setup).svarinn
        base = test_base(config.api_base_url)
        user = text_field(config.service_username, 'SvarInn service-brukernavn', 2048)
        if ':' in user or not secrets.svarinn_password:
            raise ApiError("Fyll inn gyldig SvarInn service-brukernavn og servicepassord for denne økten.")
        # The password is never trimmed: whitespace may be significant.
        if len(secrets.svarinn_password) > 4096 or any(ord(c) < 32 for c in secrets.svarinn_password):
            raise ApiError("Servicepassordet har ugyldig format.")
        credential = base64.b64encode((user + ':' + secrets.svarinn_password).encode('utf-8')).decode('ascii')
        response = self.transport.request('GET', base + '/svarinn/v2/forsendelser',
                                          headers={'Authorization': 'Basic ' + credential})
        if not isinstance(response, list) or len(response) > 200:
            raise ApiError("Uventet format på SvarInn-listen; forventet liste med inntil 200 forsendelser.")
        rows = []
        for item in response:
            if not isinstance(item, dict) or not isinstance(item.get('filer'), list):
                raise ApiError("Ufullstendige metadata i SvarInn-listen.")
            rows.append({'id': uuid_text(item.get('id'), 'Forsendelses-ID fra KS'),
                         'title': display_text(item.get('tittel')), 'date': display_text(item.get('dato'), 100),
                         'files': len(item['filer']), 'reference': display_text(item.get('eksternRef'), 100)})
        self._log('svarinn_list_ok')
        return rows

    def _svarut_headers(self, setup: Setup, secrets: SessionSecrets) -> tuple[str, str, dict]:
        config = setup.svarut
        base = test_base(config.api_base_url)
        account = uuid_text(config.account_id, 'SvarUt konto-ID')
        integration = uuid_text(config.integration_id, 'Fiks integrasjons-ID')
        password = secrets.integration_password
        if not password or len(password) > 4096 or any(ord(c) < 32 or ord(c) > 126 for c in password):
            raise ApiError("Fyll inn gyldig Fiks-integrasjonspassord for denne økten.")
        token = self.auth.token(config, secrets)
        return base, account, {'Authorization': 'Bearer ' + token,
                               'IntegrasjonId': integration, 'IntegrasjonPassord': password}

    def send(self, setup: Setup, secrets: SessionSecrets, draft: SendDraft) -> dict:
        if not self._send_lock.acquire(blocking=False):
            raise ApiError("En sending pågår allerede.")
        try:
            setup = self._setup(setup)
            # Validate before authentication or an irreversible remote action.
            base = test_base(setup.svarut.api_base_url)
            account = uuid_text(setup.svarut.account_id, 'SvarUt konto-ID')
            prepared = prepare_send(draft, account_id=account, api_base=base)
            base, account, headers = self._svarut_headers(setup, secrets)
            content_type, body = multipart(prepared)
            self.outbox.begin(reference=prepared.reference, fingerprint=prepared.fingerprint,
                 account_id=account, api_base=base, recipient=prepared.metadata['mottaker']['digitalId'],
                 recipient_name=prepared.metadata['mottaker']['navn'], title=prepared.metadata['tittel'],
                 filename=prepared.filename, sha256=prepared.sha256)
            self._log('send_started')
            try:
                response = self.transport.request('POST', base + f'/v3/kontoer/{account}/forsendelser/organisasjon',
                                                  headers={**headers, 'Content-Type': content_type}, body=body)
                if not isinstance(response, dict):
                    raise ApiError("Uventet svar etter sending.")
                remote_id = uuid_text(response.get('id'), 'Returnert forsendelses-ID')
            except Exception as exc:
                # A crash, timeout, 5xx, malformed success or disconnected response
                # is NOT evidence that KS did not accept the document.
                code = exc.status if isinstance(exc, ApiError) else None
                state = 'REJECTED' if code in (400, 401, 403, 404, 405, 413, 415, 422) else 'UNKNOWN'
                try:
                    self.outbox.outcome(prepared.reference, state, http_status=code)
                except StorageError:
                    raise ApiError("Sendeutfallet kunne ikke lagres. Ikke send på nytt; avstem referanse " + prepared.reference + " i KS testforvaltning.") from None
                self._log('send_rejected' if state == 'REJECTED' else 'send_unknown')
                detail = str(exc) if isinstance(exc, ApiError) else "Uventet feil under sending. Råfeilen er skjermet."
                if state == 'UNKNOWN':
                    detail += " Utfallet er UKJENT. Ikke send på nytt; søk etter ekstern referanse " + prepared.reference + " i KS testforvaltning."
                raise ApiError(detail, status=code) from None
            try:
                self.outbox.outcome(prepared.reference, 'ACCEPTED', remote_id=remote_id, http_status=200)
            except StorageError:
                raise ApiError("KS har akseptert forsendelsen, men lokal lagring feilet. IKKE send på nytt. Noter forsendelses-ID: " + remote_id + "; ekstern referanse: " + prepared.reference) from None
            self._log('send_accepted')
            return {'id': remote_id, 'reference': prepared.reference}
        finally:
            self._send_lock.release()

    def status(self, setup: Setup, secrets: SessionSecrets, remote_id: str) -> dict | None:
        setup = self._setup(setup)
        target = uuid_text(remote_id, 'Forsendelses-ID')
        base, account, headers = self._svarut_headers(setup, secrets)
        response = self.transport.request('POST', base + f'/v3/kontoer/{account}/forsendelser/status/sok',
             headers={**headers, 'Content-Type': 'application/json'},
             body=json.dumps({'id': [target]}).encode('utf-8'))
        if not isinstance(response, dict) or not isinstance(response.get('statuser'), list):
            raise ApiError("Uventet svarformat fra Status V3.")
        matches = []
        for item in response['statuser']:
            if not isinstance(item, dict):
                raise ApiError("Ufullstendig forsendelsesstatus.")
            item_id = uuid_text(item.get('id'), 'Status-ID')
            if item_id != target:
                raise ApiError("KS returnerte status for en annen forsendelse enn forespurt.")
            status = item.get('status')
            changed = item.get('sisteStatusEndring')
            if not isinstance(status, str) or not re.fullmatch('[A-Z][A-Z0-9_]{0,99}', status) or not isinstance(changed, str):
                raise ApiError("Ufullstendig forsendelsesstatus.")
            matches.append({'id': item_id, 'status': status, 'changed': display_text(changed, 100)})
        if len(matches) > 1:
            raise ApiError("Flere statuser enn forventet for samme forsendelse.")
        if matches:
            value = matches[0]
            self.outbox.status(account, target, value['status'], value['changed'])
        self._log('status_ok')
        return matches[0] if matches else None

    def receive(self) -> None:
        raise ApiError("Dokumentnedlasting og dekryptering er ikke implementert. Bruk Hent forsendelsesliste.")

    def acknowledge(self) -> None:
        raise ApiError("Kvittering er sperret. Ingen mottakskvittering sendes i denne versjonen.")
