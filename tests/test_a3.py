"""Isolated SvarInn V2 receive tests: synthetic files, no network or KS credentials."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError
import json
from uuid import uuid4
import zipfile

from svarut_svarinn_client.core.inbox import receive_delivery
from svarut_svarinn_client.core.network import ApiError, TEST_API_BASE


class _Response:
    status = 200
    def __init__(self, url: str, content: bytes):
        self.url, self.stream = url, io.BytesIO(content)
    def geturl(self):
        return self.url
    def read(self, size):
        return self.stream.read(size)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key, self.cert = self.root / 'privatekey.pem', self.root / 'public.pem'
        try:
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                '-keyout', str(self.key), '-out', str(self.cert), '-days', '1',
                '-subj', '/CN=Synthetic'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=True, timeout=30)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            self.skipTest('OpenSSL not available for crypto integration test')
        self.content = b'Unclassified synthetic document for local test only.'
        with io.BytesIO() as stream:
            with zipfile.ZipFile(stream, 'w') as archive:
                archive.writestr('document.txt', self.content)
            self.zipbytes = stream.getvalue()
        plain, encrypted = self.root / 'raw.zip', self.root / 'delivery.cms'
        plain.write_bytes(self.zipbytes)
        subprocess.run(['openssl', 'cms', '-encrypt', '-binary', '-outform', 'DER',
            '-in', str(plain), '-out', str(encrypted), str(self.cert)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=30)
        self.encrypted = encrypted.read_bytes()
        self.id = str(uuid4())
        self.url = TEST_API_BASE + '/svarinn/v2/forsendelser/' + self.id
        self.metadata = {'id': self.id, 'filer': [{'filnavn': 'document.txt',
            'hash': hashlib.sha256(self.content).hexdigest(), 'storrelse': len(self.content)}]}
        response = _Response(self.url, self.encrypted)
        opener = Mock()
        opener.open.return_value = response
        self.transport = Mock(_opener=opener)

    def receive(self, metadata=None):
        return receive_delivery(self.transport, base_url=TEST_API_BASE,
            authorization='Basic SYNTHETIC', metadata=metadata or self.metadata,
            private_key_file=str(self.key), public_certificate_file=str(self.cert),
            data_root=self.root)

    def test_verify_and_keep_local_files_without_ack(self):
        result = self.receive()
        folder = Path(result['path'])
        self.assertEqual((folder / 'documents' / 'document.txt').read_bytes(), self.content)
        self.assertTrue((folder / 'metadata.json').is_file())
        self.assertTrue((folder / 'verification.json').is_file())
        self.assertTrue((folder / 'forsendelse.cms').is_file())
        self.assertTrue((folder / 'forsendelse.zip').is_file())
        self.assertEqual(self.transport._opener.open.call_count, 1)
        self.assertEqual(result['files'], 1)
        with self.assertRaises(ApiError):
            self.receive()

    def test_hash_mismatch_does_not_create_receipt(self):
        import copy
        metadata = copy.deepcopy(self.metadata)
        metadata['filer'][0]['hash'] = '0' * 64
        with self.assertRaises(ApiError):
            self.receive(metadata)
        folder = self.root / 'received' / self.id
        self.assertTrue((folder / 'forsendelse.cms').is_file())
        self.assertTrue((folder / 'forsendelse.zip').is_file())
        self.assertFalse((folder / 'documents').exists())
        self.assertEqual(json.loads((folder / 'verification.json').read_text())['status'], 'INSPECTION_REQUIRED')

    def test_decrypted_unknown_format_is_retained_for_inspection(self):
        # The CMS is valid, but the plaintext does not contain a ZIP or PDF.
        plain = self.root / 'unknown.bin'
        encrypted = self.root / 'unknown.cms'
        plain.write_bytes(b'UNKNOWN TEST FORMAT')
        subprocess.run(['openssl', 'cms', '-encrypt', '-binary', '-outform', 'DER',
            '-in', str(plain), '-out', str(encrypted), str(self.cert)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=30)
        self.transport._opener.open.return_value = _Response(self.url, encrypted.read_bytes())
        with self.assertRaisesRegex(ApiError, 'beholdt for inspeksjon'):
            self.receive()
        folder = self.root / 'received' / self.id
        self.assertEqual((folder / 'forsendelse.decrypted.bin').read_bytes(), plain.read_bytes())
        self.assertEqual((folder / 'forsendelse.cms').read_bytes(), encrypted.read_bytes())
        self.assertFalse((folder / 'documents').exists())
        self.assertEqual(json.loads((folder / 'verification.json').read_text())['acknowledged'], False)

    def test_download_http_400_gives_safe_diagnostic_without_leaking_server_values(self):
        import copy
        body = json.dumps({'feilmelding': 'Kunne ikke kryptere med sertifikat',
                           'privateValue': 'SENSITIVE-SYNTHETIC'}).encode('utf-8')
        self.transport._opener.open.side_effect = HTTPError(self.url, 400, 'Bad Request', {}, io.BytesIO(body))
        with self.assertRaises(ApiError) as raised:
            self.receive()
        self.assertEqual(raised.exception.status, 400)
        self.assertIn('kryptering', str(raised.exception))
        self.assertIn('Fase: nedlasting', str(raised.exception))
        self.assertNotIn('SENSITIVE-SYNTHETIC', str(raised.exception))
        self.assertFalse((self.root / 'received' / self.id).exists())

    def test_download_uses_generic_accept_for_openapi_wildcard(self):
        self.receive()
        request = self.transport._opener.open.call_args.args[0]
        self.assertEqual(request.get_header('Accept'), '*/*')

    def test_reject_path_traversal_without_network(self):
        import copy
        metadata = copy.deepcopy(self.metadata)
        metadata['filer'][0]['filnavn'] = '../outside.txt'
        with self.assertRaises(ApiError):
            self.receive(metadata)
        self.transport._opener.open.assert_not_called()


if __name__ == '__main__':
    unittest.main()
