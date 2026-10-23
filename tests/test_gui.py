from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from svarut_svarinn_client.core.config import ConfigStore
from svarut_svarinn_client.core.paths import AppPaths, StorageError
from svarut_svarinn_client.core.services import AppService
from svarut_svarinn_client.core.storage import atomic_json, read_json


class GuiTests(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
        except ImportError:
            self.fail('Tkinter is required to test the GUI')
        try:
            from svarut_svarinn_client.ui.app import App
            probe = tk.Tk()
            probe.destroy()
        except tk.TclError:
            if os.name == 'nt':
                self.fail('GUI tests require Tcl/Tk and a desktop session on Windows')
            self.skipTest('No display/Tk; run under Xvfb for GUI tests')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.paths = AppPaths(Path(self.temp.name))
        self.service = AppService(self.paths)
        self.app = App(self.service)
        self.callbacks = []
        self.app.report_callback_exception = lambda *args: self.callbacks.append(args)
        self.app.update()

    def tearDown(self):
        if hasattr(self, 'app'):
            try:
                self.app.destroy()
            except Exception:
                pass
        if hasattr(self, 'callbacks'):
            self.assertEqual(self.callbacks, [])

    def test_expected_pages_and_disabled_network_actions(self):
        self.assertEqual(list(self.app.pages), ['Oversikt', 'Oppsett', 'SvarUt', 'SvarInn', 'Aktivitetslogg'])
        self.assertIn('TEST', self.app.title())
        self.assertEqual(len(self.app.network_buttons), 4)
        self.assertTrue(all(button.instate(['disabled']) for button in self.app.network_buttons))

    def test_empty_first_start(self):
        self.assertFalse(self.app.is_dirty())
        self.assertTrue(all(v.get() == '' for v in self.app.fields.values()))

    def test_save_persists_and_restart_reuses_values(self):
        self.app.fields['svarinn.service_username'].set('syntetisk-gui')
        self.assertTrue(self.app.is_dirty())
        self.assertTrue(self.app.save_setup())
        self.assertFalse(self.app.is_dirty())
        self.app.destroy()
        from svarut_svarinn_client.ui.app import App
        self.app = App(AppService(self.paths))
        self.app.report_callback_exception = lambda *args: self.callbacks.append(args)
        self.app.update()
        self.assertEqual(self.app.fields['svarinn.service_username'].get(), 'syntetisk-gui')
        self.assertFalse(self.app.is_dirty())

    def test_tab_switch_keeps_unsaved_input(self):
        self.app.fields['svarinn.service_username'].set('syntetisk-ulagret')
        for page in self.app.pages.values():
            self.app.notebook.select(page)
            self.app.update()
        self.assertEqual(self.app.fields['svarinn.service_username'].get(), 'syntetisk-ulagret')
        self.assertTrue(self.app.is_dirty())

    def test_small_window_setup_scrolls_to_last_entry(self):
        self.app.geometry('760x520')
        self.app.notebook.select(self.app.pages['Oppsett'])
        self.app.update()
        self.assertGreater(self.app.form.body.winfo_height(), self.app.form.canvas.winfo_height())
        self.app.form.show_widget(self.app.entries['svarinn.public_certificate_file'])
        self.app.update()
        self.assertGreater(self.app.form.canvas.yview()[0], 0)
        entry = self.app.entries['svarinn.public_certificate_file']
        canvas = self.app.form.canvas
        self.assertGreaterEqual(entry.winfo_rooty(), canvas.winfo_rooty())
        self.assertLessEqual(entry.winfo_rooty() + entry.winfo_height(), canvas.winfo_rooty() + canvas.winfo_height())

    def test_local_check_does_not_save_unsaved_values(self):
        before = self.paths.setup.read_bytes()
        self.app.fields['svarinn.service_username'].set('syntetisk-ulagret')
        self.app.check_local()
        self.assertEqual(self.paths.setup.read_bytes(), before)
        self.assertTrue(self.app.is_dirty())
        self.assertIn('Ingen', self.app.status.get())

    def test_failed_save_retains_dirty_fields(self):
        self.app.fields['svarinn.service_username'].set('syntetisk')
        with patch.object(self.service.store, 'save', side_effect=StorageError('synthetic')), \
             patch('svarut_svarinn_client.ui.app.messagebox.showerror'):
            self.assertFalse(self.app.save_setup())
        self.assertTrue(self.app.is_dirty())
        self.assertEqual(ConfigStore(self.paths.setup).load_or_create().svarinn.service_username, '')

    def test_cancel_close_retains_window_and_changes(self):
        self.app.fields['svarinn.service_username'].set('syntetisk')
        with patch('svarut_svarinn_client.ui.app.messagebox.askyesnocancel', return_value=None):
            self.app.close()
        self.assertTrue(self.app.winfo_exists())
        self.assertTrue(self.app.is_dirty())

    def test_discard_close_does_not_save_setup(self):
        self.app.fields['svarinn.service_username'].set('syntetisk')
        with patch('svarut_svarinn_client.ui.app.messagebox.askyesnocancel', return_value=False):
            self.app.close()
        self.assertEqual(ConfigStore(self.paths.setup).load_or_create().svarinn.service_username, '')

    def test_save_on_close(self):
        self.app.fields['svarinn.service_username'].set('syntetisk')
        with patch('svarut_svarinn_client.ui.app.messagebox.askyesnocancel', return_value=True):
            self.app.close()
        self.assertEqual(ConfigStore(self.paths.setup).load_or_create().svarinn.service_username, 'syntetisk')
        self.assertEqual(set(read_json(self.paths.ui_state)), {'width', 'height'})

    def test_existing_oversized_geometry_clamped(self):
        self.app.destroy()
        atomic_json(self.paths.ui_state, {'width': 9000, 'height': 9000})
        from svarut_svarinn_client.ui.app import App
        self.app = App(AppService(self.paths))
        self.app.report_callback_exception = lambda *args: self.callbacks.append(args)
        self.app.update()
        self.assertLessEqual(self.app.winfo_width(), self.app.winfo_screenwidth())
        self.assertLessEqual(self.app.winfo_height(), self.app.winfo_screenheight())

    def test_activity_visible_without_account_values(self):
        value = 'syntetisk-skal-ikke-logges'
        self.app.fields['svarinn.service_username'].set(value)
        self.app.save_setup()
        self.app.refresh_activity()
        content = str([self.app.activity_table.item(item)['values'] for item in self.app.activity_table.get_children()])
        self.assertNotIn(value, content)
        self.assertTrue(self.app.activity_table.get_children())

    def test_small_overview_retains_scrollable_table(self):
        self.app.geometry('640x420')
        self.app.notebook.select(self.app.pages['Oversikt'])
        self.app.update()
        self.assertGreaterEqual(self.app.check_table.winfo_height(), 75)
