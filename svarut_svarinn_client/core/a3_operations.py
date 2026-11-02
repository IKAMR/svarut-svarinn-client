"""SvarInn V2 download operations. No remote acknowledgement is performed."""
from __future__ import annotations

import base64

from .auth import SessionSecrets
from .activity import EVENT_TEXT
from .config import Setup
from .inbox import receive_delivery
from .ks_api import TestOperations, display_text, text_field
from .network import ApiError, test_base, uuid_text


EVENT_TEXT.setdefault('svarinn_download_verified', 'SvarInn: nedlasting og SHA-256-kontroll fullfort. Ingen kvittering.')
EVENT_TEXT.setdefault('svarinn_download_warning', 'SvarInn: SHA-256 stemmer, men KS-metadata har storrelsesavvik. Ingen kvittering.')

class DownloadOperations(TestOperations):
    """Adds read-only SvarInn retrieval to the existing a2 operations."""

    @staticmethod
    def _basic_auth(config, secrets):
        user = text_field(config.service_username, 'SvarInn service-brukernavn', 2048)
        if ':' in user or not secrets.svarinn_password:
            raise ApiError('Fyll inn SvarInn service-brukernavn og servicepassord for denne okten.')
        password = secrets.svarinn_password
        if len(password) > 4096 or any(ord(c) < 32 for c in password):
            raise ApiError('Servicepassordet har ugyldig format.')
        return 'Basic ' + base64.b64encode((user + ':' + password).encode('utf-8')).decode('ascii')

    received_dir = None

    def list_incoming(self, setup: Setup, secrets: SessionSecrets) -> list[dict]:
        config = self._setup(setup).svarinn
        base = test_base(config.api_base_url)
        authorization = self._basic_auth(config, secrets)
        response = self.transport.request('GET', base + '/svarinn/v2/forsendelser',
                                          headers={'Authorization': authorization})
        if not isinstance(response, list) or len(response) > 200:
            raise ApiError('Uventet format paa SvarInn-listen.')
        rows = []
        for item in response:
            if not isinstance(item, dict) or not isinstance(item.get('filer'), list):
                raise ApiError('Ufullstendige metadata i SvarInn-listen.')
            rows.append({'id': uuid_text(item.get('id'), 'Forsendelses-ID fra KS'),
                         'title': display_text(item.get('tittel')),
                         'date': display_text(item.get('dato'), 100),
                         'files': len(item['filer']),
                         'reference': display_text(item.get('eksternRef'), 100),
                         'metadata': item})
        self._log('svarinn_list_ok')
        return rows

    def receive(self, setup: Setup | None = None, secrets: SessionSecrets | None = None, metadata: dict | None = None, *, allow_existing: bool = False) -> dict:
        if setup is None or secrets is None or metadata is None:
            raise ApiError("Velg en forsendelse og oppgi gyldig SvarInn-oppsett for nedlasting.")
        config = self._setup(setup).svarinn
        base = test_base(config.api_base_url)
        authorization = self._basic_auth(config, secrets)
        result = receive_delivery(self.transport, base_url=base,
                                  authorization=authorization, metadata=metadata,
                                  private_key_file=config.private_key_file,
                                  public_certificate_file=config.public_certificate_file,
                                  data_root=self.outbox.path.parent,
                                  received_dir=self.received_dir, allow_existing=allow_existing)
        self._log('svarinn_download_warning' if result.get('warnings') else 'svarinn_download_verified')
        return result

    def recheck(self, shipment: str, attempt: str | None = None) -> dict:
        from .inbox import recheck_saved_receipt, receipt_folder
        from pathlib import Path
        folder = receipt_folder((self.received_dir or self.outbox.path.parent / 'received'), shipment, attempt)
        return recheck_saved_receipt(folder, expected_id=shipment)
