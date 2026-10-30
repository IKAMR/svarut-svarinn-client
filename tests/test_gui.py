from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
from threading import Event
from uuid import uuid4
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

    def test_expected_pages_and_explicit_test_actions(self):
        self.assertEqual(list(self.app.pages), ['Oversikt', 'Oppsett', 'SvarUt', 'SvarInn', 'Aktivitetslogg'])
        self.assertIn('TEST', self.app.title())
        self.assertEqual(len(self.app.network_buttons), 4)
        self.assertTrue(all(not button.instate(['disabled']) for button in self.app.network_buttons))
        self.assertFalse(self.app.api_ui.task.busy)
        self.assertEqual(self.app.api_ui.incoming_rows, [])

    def test_overview_describes_status_without_project_deadlines(self):
        import tkinter as tk

        texts = []
        pending = [self.app.pages['Oversikt']]
        while pending:
            widget = pending.pop()
            pending.extend(widget.winfo_children())
            try:
                texts.append(str(widget.cget('text')))
            except tk.TclError:
                pass
        visible_text = '\n'.join(texts)
        # Status copy must not reintroduce a dated rollout promise or a
        # project-decision label. Do not lock tests to every sentence.
        self.assertNotRegex(visible_text, r'\b\d{2}\.\d{2}\.\d{4}\b')
        self.assertNotIn('go/nogo', visible_text.casefold())
        self.assertNotIn('mål:', visible_text.casefold())
        self.assertIn('Status', texts)

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


    def wait_for_api(self):
        deadline = time.monotonic() + 3
        while self.app.api_ui.task.busy and time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.01)
        self.app.update()
        self.assertFalse(self.app.api_ui.task.busy, 'API worker did not finish')

    def test_fill_test_addresses_changes_only_empty_public_addresses(self):
        self.app.fields['svarut.account_id'].set('synthetic-account')
        self.app.fill_test_addresses()
        self.assertEqual(self.app.fields['svarut.account_id'].get(), 'synthetic-account')
        self.assertEqual(self.app.fields['svarinn.api_base_url'].get(), 'https://test.svarut.ks.no/api')
        self.assertTrue(self.app.is_dirty())
        self.app.fields['svarut.api_base_url'].set('synthetic-existing-value')
        self.app.fill_test_addresses()
        self.assertEqual(self.app.fields['svarut.api_base_url'].get(), 'synthetic-existing-value')

    def test_session_passwords_not_written_with_setup_or_window_state(self):
        value='synthetic-session-password-must-not-be-saved'
        for var in self.app.session_fields.values():
            var.set(value)
        self.app.fields['svarinn.service_username'].set('synthetic-user')
        self.app.save_setup()
        self.app.close()
        for path in self.paths.root.rglob('*'):
            if path.is_file():
                self.assertNotIn(value.encode(),path.read_bytes())

    def test_clear_session_empties_fields_and_token_cache(self):
        for var in self.app.session_fields.values():
            var.set('synthetic-secret')
        with patch.object(self.service.gateway,'clear_secrets') as clear:
            self.app.clear_session()
            clear.assert_called_once()
        self.assertTrue(all(not v.get() for v in self.app.session_fields.values()))

    def test_incoming_empty_success_not_claimed_as_download(self):
        with patch.object(self.service.gateway,'list_incoming',return_value=[]) as call:
            self.app.api_ui.list_incoming()
            self.wait_for_api()
            call.assert_called_once()
        self.assertIn('Tilkobling bekreftet',self.app.api_ui.receive_result.get())
        self.assertIn('Ingen ventende',self.app.api_ui.receive_result.get())

    def test_incoming_failure_clears_previous_rows_and_is_not_empty_success(self):
        from svarut_svarinn_client.core.network import ApiError
        self.app.api_ui.incoming.insert('','end',values=('synthetic-old-id','stale title','','',''))
        with patch.object(self.service.gateway,'list_incoming',side_effect=ApiError('HTTP 401: synthetic')):
            self.app.api_ui.list_incoming()
            self.wait_for_api()
        self.assertEqual(self.app.api_ui.incoming.get_children(),())
        self.assertIn('401',self.app.api_ui.receive_result.get())
        self.assertNotIn('Tilkobling bekreftet',self.app.api_ui.receive_result.get())

    def test_incoming_list_renders_real_result_model(self):
        identifier=str(uuid4())
        rows=[{'id':identifier,'title':'Synthetic metadata','date':'Synthetic time','files':1,'reference':'Synthetic ref'}]
        with patch.object(self.service.gateway,'list_incoming',return_value=rows):
            self.app.api_ui.list_incoming()
            self.wait_for_api()
        values=self.app.api_ui.incoming.item(self.app.api_ui.incoming.get_children()[0])['values']
        self.assertIn(identifier,str(values))
        self.assertIn('1 forsendelser',self.app.api_ui.receive_result.get())

    def test_unsaved_setup_prevents_api_call(self):
        self.app.fields['svarinn.service_username'].set('synthetic-unsaved')
        with patch.object(self.service.gateway,'list_incoming') as call, \
             patch('svarut_svarinn_client.ui.api_views.messagebox.showinfo'):
            self.app.api_ui.list_incoming()
        call.assert_not_called()
        self.assertFalse(self.app.api_ui.task.busy)

    def test_busy_blocks_second_request_save_clear_and_close(self):
        release=Event()
        def work(*_):
            release.wait(2)
            return []
        try:
            with patch.object(self.service.gateway,'list_incoming',side_effect=work) as call:
                self.app.api_ui.list_incoming()
                self.app.update()
                self.assertTrue(self.app.api_ui.task.busy)
                self.assertTrue(all(button.instate(['disabled']) for button in self.app.network_buttons))
                self.app.api_ui.list_incoming()
                self.app.session_fields['svarinn_password'].set('synthetic-secret')
                self.app.clear_session()
                self.assertEqual(self.app.session_fields['svarinn_password'].get(),'synthetic-secret')
                with patch('svarut_svarinn_client.ui.app.messagebox.showinfo'):
                    self.assertFalse(self.app.save_setup())
                    self.app.close()
                self.assertTrue(self.app.winfo_exists())
                release.set()
                self.wait_for_api()
                call.assert_called_once()
        finally:
            release.set()
        self.assertTrue(all(not button.instate(['disabled']) for button in self.app.network_buttons))

    def test_sending_requires_checkbox_and_final_confirmation(self):
        with patch.object(self.service.gateway,'send') as call:
            self.app.api_ui.send()
            call.assert_not_called()
            self.app.api_ui.confirmed.set(True)
            with patch('svarut_svarinn_client.ui.api_views.messagebox.askyesno',return_value=False):
                self.app.api_ui.send()
            call.assert_not_called()

    def test_send_success_populates_status_id_and_resets_confirmation(self):
        identifier=str(uuid4())
        self.app.api_ui.confirmed.set(True)
        with patch.object(self.service.gateway,'send',return_value={'id':identifier,'reference':str(uuid4())}) as call, \
             patch('svarut_svarinn_client.ui.api_views.messagebox.askyesno',return_value=True):
            self.app.api_ui.send()
            self.wait_for_api()
            call.assert_called_once()
        self.assertEqual(self.app.api_ui.values['remote_id'].get(),identifier)
        self.assertFalse(self.app.api_ui.confirmed.get())
        self.assertIn('ikke bekreftet levert',self.app.api_ui.send_result.get())

    def test_small_window_exposes_end_of_send_form(self):
        self.app.geometry('640x420')
        self.app.notebook.select(self.app.pages['SvarUt'])
        self.app.update()
        form=self.app.api_ui.send_form
        form.show_widget(self.app.api_ui.history)
        self.app.update()
        self.assertGreater(form.canvas.yview()[0],0)

    def test_small_window_incoming_table_remains_usable(self):
        self.app.geometry('640x420')
        self.app.notebook.select(self.app.pages['SvarInn'])
        self.app.update()
        self.assertGreaterEqual(self.app.api_ui.incoming.winfo_height(),75)
