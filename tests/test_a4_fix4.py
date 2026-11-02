"""Repeat-download contract; synthetic fixtures only, no KS connectivity."""
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4
import zipfile

from svarut_svarinn_client.core.inbox import receipt_info, receipt_folder, receive_delivery
from svarut_svarinn_client.core.network import ApiError, TEST_API_BASE


class RepeatReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.shipment = str(uuid4())
        self.document = b'synthetic document for local testing only'
        self.metadata = {'id': self.shipment, 'filer': [{'filnavn': 'test.txt',
            'hash': hashlib.sha256(self.document).hexdigest(), 'storrelse': len(self.document)}]}

    def download(self, *, allow_existing=False, failing=False):
        document = self.document
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('test.txt', document)
        def decrypt(_cms, _key, _cert, target):
            (target / 'forsendelse.zip').write_bytes(archive.getvalue())
            return archive.getvalue()
        with patch('svarut_svarinn_client.core.inbox._download', return_value=b'synthetic-cms'), \
             patch('svarut_svarinn_client.core.inbox._decrypt', side_effect=ApiError('Synthetic failure') if failing else decrypt):
            return receive_delivery(None, base_url=TEST_API_BASE, authorization='Basic synthetic',
                 metadata=self.metadata, private_key_file='unused', public_certificate_file='unused',
                 data_root=self.root, allow_existing=allow_existing)

    def test_first_and_second_attempt_do_not_overwrite(self):
        first = self.download()
        self.assertTrue(first['path'].endswith('attempt-001'))
        before = (Path(first['path']) / 'forsendelse.cms').read_bytes()
        with self.assertRaises(ApiError):
            self.download()
        self.assertEqual(len(receipt_info(self.root/'received',self.shipment)['attempts']),1)
        second = self.download(allow_existing=True)
        self.assertTrue(second['path'].endswith('attempt-002'))
        self.assertEqual((Path(first['path'])/'forsendelse.cms').read_bytes(), before)
        self.assertEqual(receipt_folder(self.root/'received',self.shipment),Path(second['path']))

    def test_failed_attempt_is_preserved_before_retry(self):
        with self.assertRaises(ApiError):
            self.download(failing=True)
        first = self.root/'received'/self.shipment/'attempt-001'
        self.assertEqual((first/'forsendelse.cms').read_bytes(), b'synthetic-cms')
        self.assertEqual(json.loads((first/'verification.json').read_text())['status'],'INSPECTION_REQUIRED')
        self.download(allow_existing=True)
        self.assertTrue((self.root/'received'/self.shipment/'attempt-002'/'documents'/'test.txt').is_file())
        self.assertTrue((first/'forsendelse.cms').is_file())

    def test_legacy_receipt_remains_untouched(self):
        folder=self.root/'received'/self.shipment
        folder.mkdir(parents=True)
        (folder/'metadata.json').write_text('legacy untouched')
        with self.assertRaises(ApiError):
            self.download()
        self.download(allow_existing=True)
        self.assertEqual((folder/'metadata.json').read_text(),'legacy untouched')
        self.assertTrue((folder/'attempt-001'/'forsendelse.cms').exists())

    def test_recheck_existing_verified_receipt_is_read_only(self):
        from svarut_svarinn_client.core.inbox import recheck_saved_receipt
        result = self.download()
        folder = Path(result['path'])
        original = (folder/'documents'/'test.txt').read_bytes()
        checked = recheck_saved_receipt(folder, expected_id=self.shipment)
        self.assertEqual(checked['files'], 1)
        self.assertEqual((folder/'documents'/'test.txt').read_bytes(), original)

    def test_unknown_empty_directory_requires_intervention(self):
        (self.root/'received'/self.shipment).mkdir(parents=True)
        with self.assertRaises(ApiError):
            self.download(allow_existing=True)


if __name__ == '__main__':
    unittest.main()
