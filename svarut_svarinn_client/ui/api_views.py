"""Test operations views; no HTTP, key loading or persistence in Tk callbacks."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..core.auth import SessionSecrets
from ..core.config import Setup
from ..core.ks_api import SendDraft
from ..core.network import ApiError
from ..core.paths import StorageError
from .tasks import BackgroundTask
from .widgets import ScrollableForm, table, fit_columns

STATE_TEXT = {'SENDING': 'Sender / ikke avklart', 'UNKNOWN': 'Ukjent utfall',
              'ACCEPTED': 'Akseptert av KS', 'REJECTED': 'Avvist av KS'}


class ApiViews:
    def __init__(self, app):
        self.app = app
        self.service = app.service
        self.gateway = self.service.gateway
        self.buttons = app.network_buttons
        self.values = {}
        self.incoming_rows = []
        self.outgoing_rows = {}
        self.task = BackgroundTask(app, self._busy_changed)
        self.send_result = tk.StringVar(app, 'Ingen testforsendelse sendt i denne økten.')
        self.receive_result = tk.StringVar(app, 'Ikke tilkoblet. Listen er ikke hentet.')
        self._outgoing()
        self._incoming()
        self.refresh_history()

    def _entry(self, form, box, row, key, label, *, browse=False):
        ttk.Label(box, text=label).grid(row=row, column=0, sticky='w', padx=(0, 8), pady=4)
        value = tk.StringVar(self.app)
        self.values[key] = value
        entry = ttk.Entry(box, textvariable=value)
        entry.grid(row=row, column=1, sticky='ew', pady=4)
        entry.bind('<FocusIn>', lambda _e: form.show_widget(entry))
        if browse:
            def choose():
                filename = filedialog.askopenfilename(parent=self.app, title='Velg ufølsom test-PDF', filetypes=[('PDF', '*.pdf')])
                if filename:
                    value.set(filename)
            ttk.Button(box, text='Velg PDF', command=choose).grid(row=row, column=2, padx=(8, 0))
        return entry

    def _button(self, parent, label, command, **grid):
        button = ttk.Button(parent, text=label, command=command)
        button.grid(padx=(0, 8), pady=4, sticky='w', **grid)
        self.buttons.append(button)
        return button

    def _outgoing(self):
        form = ScrollableForm(self.app.pages['SvarUt'])
        form.pack(fill='both', expand=True)
        self.send_form = form
        body = form.body
        form.text(body, 'SvarUt - send til testorganisasjon', style='Heading.TLabel').pack(fill='x', pady=(0, 8))
        form.text(body, 'Send én PDF (maks 20 MiB) via Send V3. Kun digital levering, uten print. Konto og nøkkeloppsett lagres i Oppsett; passord gjelder bare denne økten.').pack(fill='x', pady=(0, 8))
        box = ttk.Frame(body)
        box.pack(fill='x')
        box.columnconfigure(1, weight=1)
        fields = [('org', 'Testorganisasjonsnummer'), ('name', 'Mottakernavn'), ('title', 'Tittel'),
                  ('pdf', 'PDF-fil'), ('route', 'Forsendelsestype (valgfri)')]
        for row, (key, label) in enumerate(fields):
            self._entry(form, box, row, key, label, browse=key == 'pdf')
        form.text(body, 'Forsendelsestype må samsvare med mottakets ruting dersom mottakersystemet krever dette.').pack(fill='x', pady=4)
        self.confirmed = tk.BooleanVar(self.app, False)
        ttk.Checkbutton(body, text='Mottaker og PDF er ufølsomme testdata (Tenor/testmiljø).', variable=self.confirmed).pack(anchor='w', pady=6)
        actions = ttk.Frame(body)
        actions.pack(fill='x')
        self._button(actions, 'Test Maskinporten', self.authenticate, row=0, column=0)
        self._button(actions, 'Send testforsendelse', self.send, row=0, column=1)
        self.send_message = form.text(body, '', textvariable=self.send_result)
        self.send_message.pack(fill='x', pady=10)
        status_box = ttk.LabelFrame(body, text='Status V3', padding=8)
        status_box.pack(fill='x', pady=6)
        status_box.columnconfigure(1, weight=1)
        self._entry(form, status_box, 0, 'remote_id', 'Forsendelses-ID')
        self._button(status_box, 'Hent status', self.status, row=1, column=1)
        form.text(body, 'Utgående journal (siste 100). Velg en rad for statusoppslag. Akseptert betyr ikke levert. Ukjent utfall må avstemmes i KS testforvaltning; ingen automatisk omsending.').pack(fill='x', pady=(8, 4))
        area = ttk.Frame(body, height=240)
        area.pack(fill='x')
        area.pack_propagate(False)
        area.grid_propagate(False)
        self.history = table(area, (('created', 'Tid (UTC)', 170), ('state', 'Lokalt utfall', 160),
                         ('id', 'Forsendelses-ID', 300), ('ks', 'KS-status', 170), ('ref', 'Ekstern referanse', 300)))
        self.history.bind('<<TreeviewSelect>>', self._select_history)

    def _incoming(self):
        page = self.app.pages['SvarInn']
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
        header = ttk.Frame(page, padding=(16, 6))
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text='SvarInn - innkommende metadata', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        explanation = ttk.Label(header, text='Inntil 200 forsendelser. Ingen nedlasting eller kvittering.', wraplength=850, justify='left')
        explanation.grid(row=1, column=0, sticky='ew', pady=4)
        actions = ttk.Frame(header)
        actions.grid(row=2, column=0, sticky='w')
        self._button(actions, 'Hent forsendelsesliste', self.list_incoming, row=0, column=0)
        ttk.Button(actions, text='Gå til Oppsett', command=lambda: self.app.notebook.select(self.app.pages['Oppsett'])).grid(row=0, column=1)
        state = ttk.Label(header, textvariable=self.receive_result, wraplength=850, justify='left')
        state.grid(row=3, column=0, sticky='ew', pady=(4, 0))
        header.bind('<Configure>', lambda e: [w.configure(wraplength=max(220, e.width-32)) for w in (explanation, state)])
        area = ttk.Frame(page, padding=(16, 0, 16, 16))
        area.grid(row=1, column=0, sticky='nsew')
        self.incoming = table(area, (('id', 'Forsendelses-ID', 300), ('title', 'Tittel', 300),
                                     ('date', 'Dato', 190), ('files', 'Filer', 60), ('ref', 'Ekstern referanse', 300)))

    def snapshot(self):
        if self.app.is_dirty():
            messagebox.showinfo('Lagre Oppsett', 'Lagre oppsettet før et API-kall. Ulagrede kontoverdier brukes ikke.', parent=self.app)
            return None
        try:
            setup = Setup.from_dict(self.service.setup.to_dict())
        except StorageError as exc:
            messagebox.showerror('Oppsett', str(exc), parent=self.app)
            return None
        secrets = SessionSecrets(**{key: value.get() for key, value in self.app.session_fields.items()})
        return setup, secrets

    def _busy_changed(self, busy):
        for button in self.buttons:
            button.state(['disabled'] if busy else ['!disabled'])
        if hasattr(self.app, 'clear_session_button'):
            self.app.clear_session_button.state(['disabled'] if busy else ['!disabled'])
        if busy:
            self.app.status.set('TEST | API-kall pågår. Ikke lukk appen under sending.')

    def _run(self, label, work, success, target):
        if self.task.busy:
            return
        target.set(label + ' ...')
        def done(ok, value):
            if ok:
                success(value)
                self.app.status.set('TEST | ' + label + ' fullført.')
            else:
                target.set(value)
                self.app.status.set('TEST | Handlingen ble ikke fullført. Se resultatet i fanen.')
                try:
                    self.service.activity.append('api_error')
                except StorageError:
                    pass
            self.refresh_history()
            self.app.refresh_activity()
        try:
            self.task.start(work, done)
        except ApiError as exc:
            target.set(str(exc))

    def authenticate(self):
        snapshot = self.snapshot()
        if snapshot:
            self._run('Maskinporten-test', lambda: self.gateway.authenticate(*snapshot),
                      lambda value: self.send_result.set(value), self.send_result)

    def send(self):
        snapshot = self.snapshot()
        if snapshot is None or self.task.busy:
            return
        if not self.confirmed.get():
            self.send_result.set('Bekreft testdata før sending.')
            return
        values = {k: v.get().strip() for k, v in self.values.items()}
        draft = SendDraft(values['org'], values['name'], values['title'], values['pdf'], values['route'], True)
        # This is an irreversible request, even in the closed test environment.
        if not messagebox.askyesno('Send i KS-test?',
            'Send én PDF til testorganisasjonen?\n\n' + values['name'] + '\n' + values['org'] + '\n' + values['title'] +
            '\n\nKun digital levering. Ingen automatisk gjentakelse.', parent=self.app):
            return
        def success(result):
            self.values['remote_id'].set(result['id'])
            self.confirmed.set(False)
            self.send_result.set('Akseptert av KS (ikke bekreftet levert). Forsendelses-ID: ' + result['id'] +
                                 '\nEkstern referanse: ' + result['reference'] + '\nBruk Hent status og SvarInn-listen for å følge forsendelsen.')
        self._run('Sending av testforsendelse', lambda: self.gateway.send(*snapshot, draft), success, self.send_result)

    def status(self):
        snapshot = self.snapshot()
        if snapshot:
            remote_id = self.values['remote_id'].get().strip()
            # When a history row is selected, do not silently query it under a
            # newly selected account. Free ID lookup still uses saved account.
            selected = self.history.selection()
            if selected:
                row = self.outgoing_rows.get(selected[0], {})
                if row.get('remote_id') == remote_id and row.get('account_id') != snapshot[0].svarut.account_id.lower():
                    self.send_result.set('Denne journalraden tilhører en annen konto. Velg riktig konto i Oppsett.')
                    return
            def success(value):
                self.send_result.set(('Ingen status returnert for denne ID-en. Kontroller ID og konto; prøv et nytt manuelt oppslag senere.' if value is None else
                    'KS-status: ' + value['status'] + '\nSist endret: ' + value['changed'] + '\nForsendelses-ID: ' + value['id']))
            self._run('Statusoppslag', lambda: self.gateway.status(*snapshot, remote_id), success, self.send_result)

    def list_incoming(self):
        snapshot = self.snapshot()
        if snapshot is None or self.task.busy:
            return
        self.incoming_rows = []
        self.incoming.delete(*self.incoming.get_children())
        def success(rows):
            self.incoming_rows = rows
            for row in rows:
                self.incoming.insert('', 'end', values=(row['id'], row['title'], row['date'], row['files'], row['reference']))
            fit_columns(self.incoming)
            self.receive_result.set('Tilkobling bekreftet. Ingen ventende forsendelser.' if not rows else
                f'Tilkobling bekreftet. {len(rows)} forsendelser vist. Ingen nedlasting eller kvittering.')
        self._run('Henting av SvarInn-liste', lambda: self.gateway.list_incoming(*snapshot), success, self.receive_result)

    def refresh_history(self):
        try:
            rows = self.gateway.outbox.recent()
        except StorageError as exc:
            self.app.status.set(str(exc))
            return
        self.history.delete(*self.history.get_children())
        self.outgoing_rows.clear()
        for row in rows:
            key = self.history.insert('', 'end', values=(row['created'], STATE_TEXT.get(row['state'], row['state']),
                              row['remote_id'], row['ks_status'], row['reference']))
            self.outgoing_rows[key] = row
        fit_columns(self.history)

    def _select_history(self, _event=None):
        selected = self.history.selection()
        if selected and selected[0] in self.outgoing_rows:
            row = self.outgoing_rows[selected[0]]
            self.values['remote_id'].set(row['remote_id'])
            self.send_result.set(STATE_TEXT.get(row['state'], row['state']) + '\nEkstern referanse: ' + row['reference'] +
                ('\nForsendelses-ID: ' + row['remote_id'] if row['remote_id'] else '\nIngen forsendelses-ID lagret. Avstem i KS testforvaltning før eventuell ny sending.'))
