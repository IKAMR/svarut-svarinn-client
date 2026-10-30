from __future__ import annotations

import contextlib
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from svarut_svarinn_client.__main__ import main
from svarut_svarinn_client.core.activity import ActivityLog
from svarut_svarinn_client.core.config import ConfigStore, Setup
from svarut_svarinn_client.core.paths import AppPaths, REPOSITORY_ROOT, StorageError, resolve_paths
from svarut_svarinn_client.core.readiness import inspect_setup, valid_test_api_url
from svarut_svarinn_client.core.services import AppService
from svarut_svarinn_client.core.network import ApiError
from svarut_svarinn_client.core.storage import InstanceLock, atomic_json, read_json


class TempCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = AppPaths(self.root)
        self.store = ConfigStore(self.paths.setup)


class ConfigurationTests(TempCase):
    def test_first_start_creates_empty_setup(self):
        setup = self.store.load_or_create()
        self.assertTrue(self.paths.setup.is_file())
        self.assertEqual(setup.environment, 'TEST')
        for group in (setup.svarut, setup.svarinn):
            self.assertTrue(all(value == '' for value in asdict(group).values()))

    def test_values_persist_on_restart(self):
        setup = self.store.load_or_create()
        setup.svarut.account_id = str(uuid4())
        setup.svarinn.service_username = 'syntetisk-bruker'
        self.store.save(setup)
        self.assertEqual(ConfigStore(self.paths.setup).load_or_create(), setup)

    def test_identical_save_does_not_replace_file(self):
        setup = self.store.load_or_create()
        with patch('svarut_svarinn_client.core.config.atomic_json') as writer:
            self.assertFalse(self.store.save(setup))
            writer.assert_not_called()

    def test_unknown_secret_field_rejected_without_echo(self):
        value = Setup().to_dict()
        secret = str(uuid4())
        value['svarinn']['password'] = secret
        with self.assertRaises(StorageError) as found:
            Setup.from_dict(value)
        self.assertNotIn(secret, str(found.exception))

    def test_unknown_top_field_rejected(self):
        data = Setup().to_dict()
        data['unexpected'] = 'value'
        with self.assertRaises(StorageError):
            Setup.from_dict(data)

    def test_schema_and_production_rejected(self):
        for field, bad in [('schema_version', 99), ('schema_version', True),
                           ('schema_version', '1'), ('environment', 'PROD')]:
            with self.subTest(field=field, bad=bad):
                data = Setup().to_dict()
                data[field] = bad
                with self.assertRaises(StorageError):
                    Setup.from_dict(data)

    def test_invalid_field_types_rejected(self):
        for bad in [None, 123, {}, [], 'x' * 2049, 'value\nvalue']:
            with self.subTest(bad_type=type(bad).__name__):
                data = Setup().to_dict()
                data['svarut']['account_id'] = bad
                with self.assertRaises(StorageError):
                    Setup.from_dict(data)

    def test_corrupt_json_preserved(self):
        original = b'not valid json'
        self.paths.setup.write_bytes(original)
        with self.assertRaises(StorageError):
            self.store.load_or_create()
        self.assertEqual(self.paths.setup.read_bytes(), original)

    def test_duplicate_keys_rejected(self):
        self.paths.setup.write_text('{"environment":"TEST","environment":"PROD"}')
        with self.assertRaises(StorageError):
            read_json(self.paths.setup)

    def test_oversized_input_rejected(self):
        self.paths.setup.write_bytes(b' ' * (128 * 1024 + 1))
        with self.assertRaises(StorageError):
            read_json(self.paths.setup)

    def test_atomic_failure_preserves_previous_config(self):
        setup = self.store.load_or_create()
        original = self.paths.setup.read_bytes()
        setup.svarinn.service_username = 'syntetisk-endring'
        with patch('svarut_svarinn_client.core.storage.os.replace', side_effect=OSError('synthetic failure')):
            with self.assertRaises(StorageError):
                self.store.save(setup)
        self.assertEqual(self.paths.setup.read_bytes(), original)
        self.assertEqual(list(self.root.glob('.pending-*')), [])

    def test_external_modification_detected(self):
        setup = self.store.load_or_create()
        other = setup.to_dict()
        other['svarinn']['service_username'] = 'syntetisk-ekstern'
        atomic_json(self.paths.setup, other)
        with self.assertRaises(StorageError):
            self.store.save(setup)
        self.assertEqual(read_json(self.paths.setup), other)

    def test_utf8_and_whitespace_handling(self):
        setup = self.store.load_or_create()
        setup.svarinn.service_username = '  syntetisk-øving  '
        self.store.save(setup)
        loaded = ConfigStore(self.paths.setup).load_or_create()
        self.assertEqual(loaded.svarinn.service_username, 'syntetisk-øving')

    def test_posix_file_permissions(self):
        if os.name == 'nt':
            # Windows ACL validation is a separate practical security test.
            return
        self.store.load_or_create()
        self.assertEqual(self.paths.setup.stat().st_mode & 0o777, 0o600)


class PathsAndLockTests(TempCase):
    def test_environment_override_and_cli_precedence(self):
        # Keep raw inputs: Windows temp paths may use 8.3 aliases. The public
        # result is resolved, so compare it with a resolved expected path.
        with patch.dict(os.environ, {'SVARUT_SVARINN_HOME': str(self.root / 'one')}):
            self.assertEqual(resolve_paths().root, (self.root / 'one').resolve())
            self.assertEqual(resolve_paths(str(self.root / 'two')).root,
                             (self.root / 'two').resolve())

    def test_environment_and_cli_paths_are_normalized(self):
        # Exercise normalization on every platform without requiring Windows
        # short-name support or permission to create symbolic links.
        parent = self.root / 'existing-parent'
        parent.mkdir()
        environment_path = parent / '..' / 'one'
        cli_path = parent / '..' / 'two'
        with patch.dict(os.environ, {'SVARUT_SVARINN_HOME': str(environment_path)}):
            self.assertEqual(resolve_paths().root, (self.root / 'one').resolve())
            self.assertEqual(resolve_paths(str(cli_path)).root,
                             (self.root / 'two').resolve())
        # Resolving setup locations must not create runtime directories.
        self.assertFalse((self.root / 'one').exists())
        self.assertFalse((self.root / 'two').exists())

    def test_repo_root_and_nonignored_subfolder_rejected(self):
        for directory in [REPOSITORY_ROOT, REPOSITORY_ROOT / 'setup-unsafe']:
            with self.assertRaises(StorageError):
                resolve_paths(str(directory))

    def test_explicit_ignored_local_area_allowed(self):
        self.assertEqual(resolve_paths(str(REPOSITORY_ROOT / '.local')).root,
                         (REPOSITORY_ROOT / '.local').resolve())

    def test_lock_excludes_second_handle_and_releases(self):
        first, second = InstanceLock(self.paths.lock), InstanceLock(self.paths.lock)
        first.acquire()
        try:
            with self.assertRaises(StorageError):
                second.acquire()
        finally:
            first.close()
        with second:
            self.assertTrue(self.paths.lock.exists())

    def test_lock_release_on_exception(self):
        with self.assertRaises(RuntimeError):
            with InstanceLock(self.paths.lock):
                raise RuntimeError('synthetic')
        with InstanceLock(self.paths.lock):
            pass


class ReadinessTests(TempCase):
    def test_empty_setup_is_not_ready(self):
        checks = inspect_setup(Setup())
        self.assertTrue(any(c.state == 'Mangler' for c in checks))
        self.assertTrue(any(c.label == 'Nedlasting og kvittering' and c.state == 'Ikke implementert' for c in checks))

    def test_documented_test_endpoint_allowed(self):
        for url in ['https://test.svarut.ks.no/api', 'https://test.svarut.ks.no/api/']:
            self.assertTrue(valid_test_api_url(url))

    def test_production_and_confusable_endpoints_rejected(self):
        for url in ['', 'http://test.svarut.ks.no/api', 'https://svarut.ks.no/api',
                    'https://test.svarut.ks.no.evil.invalid/api',
                    'https://test.svarut.ks.no@evil.invalid/api',
                    'https://user:pass@test.svarut.ks.no/api',
                    'https://test.svarut.ks.no/api?token=x',
                    'https://test.svarut.ks.no/api#part',
                    'https://test.svarut.ks.no:443/api',
                    'https://test.svarut.ks.no:bad/api',
                    'https://test.svarut.ks.no/other',
                    'https://forvaltning.fiks.test.ks.no/',
                    'https://svarut.fiks.test.ks.no/mottaker#/',
                    'https://[bad/api']:
            with self.subTest(url=url):
                self.assertFalse(valid_test_api_url(url))

    def test_uuid_format_checked_without_echoing_value(self):
        setup = Setup()
        private_value = 'syntetisk-ugyldig-id'
        setup.svarut.account_id = private_value
        checks = inspect_setup(setup)
        self.assertEqual(checks[1].state, 'Ugyldig')
        self.assertNotIn(private_value, repr(checks))
        setup.svarut.account_id = str(uuid4())
        self.assertEqual(inspect_setup(setup)[1].state, 'Registrert')

    def test_file_check_does_not_read_key_contents(self):
        path = self.root / 'synthetic-key-reference.txt'
        path.write_text('not-a-key')
        setup = Setup()
        setup.svarinn.private_key_file = str(path)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('No key reads during local readiness inspection')):
            checks = inspect_setup(setup)
        self.assertEqual(next(c for c in checks if c.label == 'Privat PEM-nøkkel').state, 'Registrert')
        self.assertIn('ikke', next(c for c in checks if c.label == 'Privat PEM-nøkkel').detail)

    def test_directories_and_relative_file_paths_not_valid_keys(self):
        for path in [str(self.root), 'relative-key.pem', str(self.root / 'missing.pem')]:
            setup = Setup()
            setup.svarinn.private_key_file = path
            self.assertEqual(next(c for c in inspect_setup(setup) if c.label == 'Privat PEM-nøkkel').state, 'Ugyldig')

    def test_fully_populated_fields_still_not_production_ready(self):
        keyfile = self.root / 'synthetic-reference.txt'
        keyfile.write_text('not-a-key')
        setup = Setup()
        setup.svarut.api_base_url = setup.svarinn.api_base_url = 'https://test.svarut.ks.no/api'
        setup.svarut.account_id = str(uuid4())
        setup.svarut.integration_id = str(uuid4())
        setup.svarut.maskinporten_client_id = str(uuid4())
        setup.svarut.signing_key_file = str(keyfile)
        setup.svarinn.service_username = 'syntetisk'
        setup.svarinn.private_key_file = setup.svarinn.public_certificate_file = str(keyfile)
        checks = inspect_setup(setup)
        self.assertTrue(any(c.state != 'Registrert' for c in checks))
        self.assertTrue(any(c.label == 'Nedlasting og kvittering' and c.state == 'Ikke implementert' for c in checks))


class ActivityAndServiceTests(TempCase):
    def test_unknown_event_cannot_log_free_text(self):
        log = ActivityLog(self.paths.activity)
        with self.assertRaises(ValueError):
            log.append('an arbitrary secret')
        self.assertFalse(self.paths.activity.exists())

    def test_configuration_values_never_in_activity_log(self):
        service = AppService(self.paths)
        value = str(uuid4())
        setup = Setup()
        setup.svarut.account_id = value
        setup.svarinn.service_username = 'syntetisk-bruker'
        service.save(setup)
        raw = self.paths.activity.read_text()
        self.assertNotIn(value, raw)
        self.assertNotIn('syntetisk-bruker', raw)
        self.assertNotIn(str(self.root), raw)
        self.assertEqual(len(service.activity.recent()), 1)

    def test_malformed_log_lines_do_not_break_display(self):
        log = ActivityLog(self.paths.activity)
        log.append('app_started')
        with self.paths.activity.open('a') as f:
            f.write('not-json\n[]\n{"event": [], "time":"x"}\n')
            f.write(json.dumps({'event': 'app_started', 'time': 'private-value'}) + '\n')
            f.write(json.dumps({'event': 'private-value', 'time': '2026-01-01T00:00:00+00:00'}) + '\n')
        self.assertEqual(len(log.recent()), 1)
        self.assertNotIn('private-value', repr(log.recent()))

    def test_recent_log_limit(self):
        log = ActivityLog(self.paths.activity)
        for _ in range(5):
            log.append('setup_checked')
        self.assertEqual(len(log.recent(2)), 2)

    def test_unchanged_save_does_not_log(self):
        service = AppService(self.paths)
        result = service.save(Setup())
        self.assertFalse(result.changed)
        self.assertEqual(service.activity.recent(), [])

    def test_log_failure_does_not_hide_successful_setup_save(self):
        service = AppService(self.paths)
        setup = Setup()
        setup.svarinn.service_username = 'syntetisk'
        with patch.object(service.activity, 'append', side_effect=StorageError('synthetic')):
            result = service.save(setup)
        self.assertTrue(result.changed)
        self.assertTrue(result.warning)
        self.assertEqual(ConfigStore(self.paths.setup).load_or_create(), setup)
        self.assertEqual(service.setup, setup)

    def test_unimplemented_download_and_acknowledgement_remain_blocked(self):
        gateway = AppService(self.paths).gateway
        for operation in [gateway.receive, gateway.acknowledge]:
            with self.assertRaises(ApiError):
                operation()


class CliTests(TempCase):
    def test_offline_check_returns_incomplete(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(['--data-dir', str(self.root), '--check-setup'])
        self.assertEqual(result, 2)
        self.assertIn('Ingen API-kall', output.getvalue())

    def test_corrupt_setup_returns_error_without_data(self):
        private = 'synthetic-private-text'
        self.paths.setup.write_text(private)
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            result = main(['--data-dir', str(self.root), '--check-setup'])
        self.assertEqual(result, 1)
        self.assertNotIn(private, error.getvalue())
