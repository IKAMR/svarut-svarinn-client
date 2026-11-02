"""Offline a4 tests; no KS access and no credentials."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
import zipfile

from svarut_svarinn_client.core.config import ConfigStore, Setup, folder_path
from svarut_svarinn_client.core.inbox import recheck_saved_receipt
from svarut_svarinn_client.core.paths import StorageError

class A4Tests(unittest.TestCase):
    def test_schema_migration_and_configurable_title(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            old = Setup().to_dict()
            old['schema_version'] = 2
            old.pop('folders'); old.pop('display')
            file = root / 'setup.json'
            file.write_text(json.dumps(old))
            store = ConfigStore(file)
            migrated = store.load_or_create()
            self.assertEqual(migrated.schema_version, 2)
            migrated.schema_version = 3
            migrated.display.title = 'IKAMR testklient'
            migrated.folders.received = 'mottak'
            self.assertTrue(store.save(migrated))
            loaded = ConfigStore(file).load_or_create()
            self.assertEqual(loaded.display.title, 'IKAMR testklient')
            # Windows can report the same temp directory using an 8.3 alias
            # (TORBJO~1.AAS) or a long account name. Compare existing parent
            # directories by filesystem identity, not string representation.
            received = folder_path(root, loaded.folders.received)
            self.assertEqual(received.name, 'mottak')
            self.assertTrue(os.path.samefile(received.parent, root))
            with self.assertRaises(StorageError):
                folder_path(root, '../utenfor')

    def test_hash_ok_size_warning_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            shipment = str(uuid4())
            folder = root / shipment
            folder.mkdir()
            content = b'harmless synthetic data'
            digest = hashlib.sha256(content).hexdigest()
            (folder / 'metadata.json').write_text(json.dumps({'id': shipment, 'filer': [
                {'filnavn': 'synthetic.txt', 'hash': digest, 'storrelse': len(content) + 1480}]}))
            with zipfile.ZipFile(folder / 'forsendelse.zip', 'w') as archive:
                archive.writestr('synthetic.txt', content)
            result = recheck_saved_receipt(folder, expected_id=shipment)
            self.assertEqual(result['files'], 1)
            self.assertEqual(result['warnings'][0]['avvik'], -1480)
            self.assertEqual((folder / 'documents' / 'synthetic.txt').read_bytes(), content)
            status = json.loads((folder / 'verification.json').read_text())
            self.assertEqual(status['status'], 'VERIFIED_WITH_WARNINGS')
            self.assertFalse(status['acknowledged'])
            # Rechecking an unchanged receipt must succeed without replacing its documents.
            document = folder / 'documents' / 'synthetic.txt'
            before_bytes = document.read_bytes()
            before_mtime = document.stat().st_mtime_ns
            checked = recheck_saved_receipt(folder, expected_id=shipment)
            self.assertEqual(checked['files'], 1)
            self.assertEqual(checked['warnings'][0]['avvik'], -1480)
            self.assertEqual(document.read_bytes(), before_bytes)
            self.assertEqual(document.stat().st_mtime_ns, before_mtime)
            self.assertFalse(json.loads((folder / 'verification.json').read_text())['acknowledged'])
            # Changes to the extracted document must be detected without overwriting it.
            document.write_bytes(b'changed locally')
            with self.assertRaises(Exception):
                recheck_saved_receipt(folder, expected_id=shipment)
            self.assertEqual(document.read_bytes(), b'changed locally')

if __name__ == '__main__': unittest.main()
