"""a4-fix2: configurable window title and durable data-root selection."""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from svarut_svarinn_client.core.config import Setup
from svarut_svarinn_client.core.data_root import (default_root, preferred_root,
    save_preferred_root, reset_preferred_root)
from svarut_svarinn_client.core.paths import StorageError, resolve_paths


class A4Fix2Tests(unittest.TestCase):
    def test_previous_a4_display_is_upgraded(self):
        old = Setup().to_dict()
        old['display'] = {'title': 'Klient'}
        newer = Setup.from_dict(old)
        self.assertEqual(newer.display.title, 'Klient')
        self.assertEqual(newer.display.window_suffix, 'TEST')
        newer.display.window_suffix = ''
        self.assertEqual(Setup.from_dict(newer.to_dict()).display.window_suffix, '')

    def test_root_switch_and_reset_without_migration(self):
        with TemporaryDirectory() as tmp:
            temp = Path(tmp)
            standard, selected, chosen = temp / 'standard', temp / 'selected', temp / 'user-choice.json'
            standard.mkdir();selected.mkdir()
            (standard / 'setup.json').write_text('old')
            with patch('svarut_svarinn_client.core.data_root.default_root', return_value=standard), \
                 patch('svarut_svarinn_client.core.data_root.preference_file', return_value=chosen), \
                 patch.dict('os.environ', {'SVARUT_SVARINN_HOME': ''}):
                self.assertEqual(preferred_root(), standard)
                save_preferred_root(selected)
                self.assertEqual(resolve_paths().root, selected.resolve())
                self.assertTrue((standard / 'setup.json').exists())
                self.assertFalse((selected / 'setup.json').exists())
                self.assertEqual(resolve_paths(str(standard)).root, standard.resolve())
                self.assertEqual(save_preferred_root(standard), standard.resolve())
                self.assertFalse(chosen.exists())
                self.assertEqual(resolve_paths().root, standard)

    def test_refuse_relative_root(self):
        with self.assertRaises(StorageError):
            save_preferred_root('received')

if __name__ == '__main__': unittest.main()
