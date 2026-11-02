"""Supplementary a4 setup controls, integrated with existing a3 GUI."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from types import MethodType

from ..core.config import LocalFolders, DisplaySetup, folder_path
from ..core.data_root import default_root, save_preferred_root, reset_preferred_root, preferred_root

CAPTIONS = (
    ('received', 'Mottatte forsendelser (aktiv)'),
    ('outgoing', 'Utgaaende arbeidsomraade (reservert)'),
    ('temp', 'Midlertidige filer (reservert)'),
    ('logs', 'Aktivitetslogger (aktiv)'),
    ('export', 'Eksport (reservert)'),
)


def install(app) -> None:
    """Extend the saved Setup without changing the existing password/KS GUI."""
    form = app.form
    body = form.body
    box = ttk.LabelFrame(body, text='Programnavn og kataloger', padding=12)
    box.pack(fill='x', pady=(0, 16))
    box.columnconfigure(1, weight=1)
    ttk.Label(box, text='Apptittel').grid(row=0, column=0, sticky='w', padx=8, pady=5)
    title = tk.StringVar(app, app.service.setup.display.title)
    ttk.Entry(box, textvariable=title).grid(row=0, column=1, sticky='ew', pady=5)
    ttk.Label(box, text='Tillegg i vindustittel').grid(row=1, column=0, sticky='w', padx=8, pady=5)
    suffix = tk.StringVar(app, app.service.setup.display.window_suffix)
    ttk.Entry(box, textvariable=suffix).grid(row=1, column=1, sticky='ew', pady=5)
    ttk.Label(box, text='Miljoe (API-sikkerhet)').grid(row=2, column=0, sticky='w', padx=8, pady=5)
    ttk.Label(box, text=app.service.setup.environment + ' (laast; produksjon er sperret)').grid(row=2, column=1, sticky='w', pady=5)
    ttk.Label(box, text='Programdatarot (aktiv)').grid(row=3, column=0, sticky='w', padx=8, pady=5)
    active = ttk.Label(box, text=str(app.service.paths.root), wraplength=620)
    active.grid(row=3, column=1, columnspan=2, sticky='w', pady=5)
    ttk.Label(box, text='Programdatarot (neste oppstart)').grid(row=4, column=0, sticky='w', padx=8, pady=5)
    chosen_root = tk.StringVar(app, str(preferred_root()))
    ttk.Entry(box, textvariable=chosen_root).grid(row=4, column=1, sticky='ew', pady=5)
    root_actions = ttk.Frame(box)
    root_actions.grid(row=4, column=2, sticky='w')
    def pick_root():
        chosen = filedialog.askdirectory(parent=app, title='Velg eksisterende programdatarot', initialdir=str(app.service.paths.root))
        if chosen:
            chosen_root.set(chosen)
    def choose_default():
        chosen_root.set(str(default_root()))
    def choose_current():
        chosen_root.set(str(app.service.paths.root))
    def apply_root():
        requested = chosen_root.get().strip()
        if not messagebox.askyesno('Bytt programdatarot ved neste oppstart?',
                'Dette endrer hvilken datamappe appen aapner NESTE gang. '
                'Oppsett og dokumenter flyttes IKKE. En tom mappe faar nytt standardoppsett. '
                'Vil du fortsette?', parent=app):
            return
        try:
            selected = save_preferred_root(requested)
        except Exception as exc:
            messagebox.showerror('Programdatarot', str(exc), parent=app)
            return
        chosen_root.set(str(selected))
        app.status.set('Programdatarot for neste oppstart er lagret. Avslutt og start appen paa nytt.')
        messagebox.showinfo('Programdatarot valgt', 'Neste oppstart bruker valgt mappe. Ingen data ble flyttet.', parent=app)
    ttk.Button(root_actions, text='Velg mappe', command=pick_root).pack(side='left', padx=2)
    ttk.Button(root_actions, text='Standard', command=choose_default).pack(side='left', padx=2)
    ttk.Button(root_actions, text='Aktiv', command=choose_current).pack(side='left', padx=2)
    ttk.Button(box, text='Bruk valgt rot ved neste oppstart', command=apply_root).grid(row=5, column=1, sticky='w', pady=5)
    ttk.Label(box, text='Standard: ' + str(default_root()) + '\n'
        'Velg mappe, Standard eller Aktiv, og bekreft byttet. Ingen data flyttes.\n'
        'Relative kataloger under tolkes mot den aktive roten, aldri mot Git-repoet.\n'
        'Oppstart med --data-dir eller SVARUT_SVARINN_HOME overstyrer dette valget.').grid(
            row=6, column=0, columnspan=3, sticky='w', pady=8)
    values = {}
    for index, (key, label) in enumerate(CAPTIONS, start=7):
        ttk.Label(box, text=label).grid(row=index, column=0, sticky='w', padx=8, pady=5)
        val = tk.StringVar(app, getattr(app.service.setup.folders, key))
        values[key] = val
        entry = ttk.Entry(box, textvariable=val)
        entry.grid(row=index, column=1, sticky='ew', pady=5)
        entry.bind('<FocusIn>', lambda _e, w=entry: form.show_widget(w))
        def browse(v=val):
            chosen = filedialog.askdirectory(parent=app, title='Velg katalog')
            if chosen:
                v.set(chosen)
        ttk.Button(box, text='Velg mappe', command=browse).grid(row=index, column=2, padx=8)
    app.a4_folder_values = values
    app.a4_title_value = title
    original_candidate = app.candidate
    original_save = app.save_setup
    original_is_dirty = app.is_dirty
    original_refresh = app.refresh_checks

    def candidate(self):
        old = original_candidate()
        return replace(old, schema_version=3, folders=LocalFolders(**{k: v.get().strip() for k, v in values.items()}),
                       display=DisplaySetup(title=title.get().strip(), window_suffix=suffix.get().strip()))

    def is_dirty(self):
        current = candidate(self)
        saved = replace(self.service.setup, schema_version=3)
        return current.to_dict() != saved.to_dict()

    def update_caption():
        title_text = app.service.setup.display.title
        from .. import __version__
        suffix_text = app.service.setup.display.window_suffix
        app.title(f'{title_text} - v{__version__}' + (f' - {suffix_text}' if suffix_text else ''))
        # Existing header is a plain ttk.Label; modify without replacing its layout.
        for top in app.grid_slaves(row=0, column=0):
            for child in top.winfo_children():
                if isinstance(child, ttk.Label):
                    label = str(child.cget('text'))
                    if ' | v' in label:
                        child.configure(text=f'{title_text}  |  v{__version__}')
                    elif label.startswith('TEST  |'):
                        child.configure(text=app.service.setup.environment + '  |  KS testmiljoe')

    def save(self):
        valid = candidate(self)
        # Check folders before app.save_setup persists anything.
        try:
            for k, _ in CAPTIONS:
                folder_path(self.service.paths.root, getattr(valid.folders, k))
        except Exception as exc:
            from tkinter import messagebox
            messagebox.showerror('Katalogoppsett', str(exc), parent=self)
            return False
        result = original_save()
        if result:
            update_caption()
        return result

    app.candidate = MethodType(candidate, app)
    app.is_dirty = MethodType(is_dirty, app)
    app.save_setup = MethodType(save, app)
    # Current app's Save button was constructed with original bound method.
    # Rebind its command so the new title is reflected immediately.
    for child in app.pages['Oppsett'].winfo_children():
        for button in child.winfo_children():
            if isinstance(button, ttk.Button) and str(button.cget('text')) == 'Lagre oppsett':
                button.configure(command=app.save_setup)
    for var in (title, suffix, *values.values()):
        var.trace_add('write', lambda *_: app._dirty_changed())
    update_caption()
    # Update stale a2 wording on overview (a3 already has a download action).
    overview = app.pages['Oversikt']
    pending = [overview]
    while pending:
        item = pending.pop()
        pending.extend(item.winfo_children())
        if isinstance(item, ttk.Label):
            label = str(item.cget('text'))
            if 'Ingen dokumentnedlasting eller kvittering.' in label:
                item.configure(text=label.replace('Ingen dokumentnedlasting eller kvittering.',
                    'Kontrollert nedlasting og lokal dekryptering er tilgjengelig i SvarInn. Ingen kvittering.'))
    # The existing readiness table still has a2 language; replace only its misleading row.
    def refresh(self, candidate=None):
        original_refresh(candidate)
        for rowid in self.check_table.get_children():
            cells = list(self.check_table.item(rowid, 'values'))
            if len(cells) == 4 and cells[0] == 'SvarInn' and cells[1] == 'Nedlasting og kvittering':
                cells[1:] = ['Nedlasting (uten kvittering)', 'Klar for test',
                    'Nedlasting, dekryptering og SHA-256 er implementert. Kvittering er sperret.']
                self.check_table.item(rowid, values=cells)
    app.refresh_checks = MethodType(refresh, app)
    refresh(app)
