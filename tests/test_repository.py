from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_required_entry_points_exist(self):
        for name in ['README.md', 'LICENCE', '.gitignore', 'install.bat', 'start.bat', 'test.bat', 'run.py']:
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

    def test_python_sources_compile(self):
        for directory in ['svarut_svarinn_client', 'tools', 'tests']:
            for path in (ROOT / directory).rglob('*.py'):
                with self.subTest(file=path.name):
                    compile(path.read_text(encoding='utf-8'), path.name, 'exec')

    def test_markdown_local_links_resolve(self):
        for path in [ROOT / 'README.md', *(ROOT / 'docs').rglob('*.md')]:
            content = path.read_text(encoding='utf-8')
            for target in re.findall(r'\]\(([^)]+)\)', content):
                if '://' in target or target.startswith('#'):
                    continue
                resolved = (path.parent / target.split('#')[0]).resolve()
                with self.subTest(document=path.name, target=target):
                    self.assertTrue(resolved.exists())

    def test_gitignore_blocks_private_material_but_not_sources(self):
        if not shutil.which('git'):
            self.skipTest('Git not installed; gitignore test not run')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            shutil.copyfile(ROOT / '.gitignore', path / '.gitignore')
            subprocess.run(['git', 'init', '-q', str(path)], check=True, capture_output=True)
            blocked = ['.local/setup.json', 'setup.json', 'ui-state.json', 'config.json',
                       'local-data/setup.json', '.env', '.env.test', 'keys/private.pem',
                       'test.pfx', 'credentials.test.json', 'received/letter.txt',
                       'logs/activity.jsonl', 'mail.pdf', 'mail.eml', 'delta.zip']
            for value in blocked:
                result = subprocess.run(['git', '-C', directory, 'check-ignore', '-q', value], capture_output=True)
                self.assertEqual(result.returncode, 0, value)
            for value in ['README.md', 'docs/KS-API.md', 'docs/test-results/result.md',
                          'svarut_svarinn_client/core/config.py', 'tests/test_core.py']:
                result = subprocess.run(['git', '-C', directory, 'check-ignore', '-q', value], capture_output=True)
                self.assertEqual(result.returncode, 1, value)

    def test_batch_files_are_ascii_without_bom(self):
        for path in ROOT.glob('*.bat'):
            data = path.read_bytes()
            self.assertTrue(data.isascii())
            self.assertFalse(data.startswith(b'\xef\xbb\xbf'))
