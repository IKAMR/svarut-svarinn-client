"""New, deliberately small desktop shell; not a copy of the DWM GUI."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk
from typing import Any

from .. import __version__
from ..core.config import Setup, SvarInnSetup, SvarUtSetup
from ..core.paths import StorageError
from ..core.services import AppService
from ..core.storage import atomic_json, read_json
from .api_views import ApiViews
from ..core.network import TEST_API_BASE, TEST_MASKINPORTEN_BASE
from .widgets import ScrollableForm, fit_columns, table

TITLE = "SvarUt/SvarInn Client"


class App(tk.Tk):
    def __init__(self, service: AppService):
        super().__init__()
        self.withdraw()
        self.service = service
        self.fields: dict[str, tk.StringVar] = {}
        self.entries: dict[str, ttk.Entry] = {}
        self.network_buttons: list[ttk.Button] = []
        self.session_fields = {name: tk.StringVar(self) for name in
            ("integration_password", "signing_key_password", "svarinn_password")}
        self._closing = False
        self.title(f"{TITLE} - v{__version__} - TEST")
        self._style()
        self._geometry()
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.status = tk.StringVar(value="TEST | Ingen automatisk sending eller kvittering.")
        self.dirty_status = tk.StringVar(value="Oppsett lagret lokalt")
        self._build()
        self._load_fields()
        self.refresh_checks()
        self.refresh_activity()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Control-s>", self._save_shortcut)
        self.deiconify()

    def _style(self) -> None:
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            font.nametofont(name).configure(size=11)
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(".", font=font.nametofont("TkDefaultFont"))
        style.configure("Heading.TLabel", font=(font.nametofont("TkDefaultFont").actual("family"), 11, "bold"))
        style.configure("TFrame", background="#f4f5f7")
        style.configure("TLabel", background="#f4f5f7", foreground="#202630")
        style.configure("TLabelframe", background="#f4f5f7")
        style.configure("TLabelframe.Label", background="#f4f5f7", foreground="#202630")
        style.configure("TNotebook", background="#f4f5f7")
        style.configure("TNotebook.Tab", background="#e4e7eb")
        style.map("TNotebook.Tab", background=[("selected", "#f4f5f7")])
        style.configure("TButton", padding=(10, 6))
        style.configure("TNotebook.Tab", padding=(14, 8))
        style.configure("Treeview", rowheight=30)
        style.configure("Treeview.Heading", padding=5)

    def _geometry(self) -> None:
        available_w = max(320, self.winfo_screenwidth() - 80)
        available_h = max(300, self.winfo_screenheight() - 100)
        width, height = min(1080, available_w), min(760, available_h)
        if self.service.paths.ui_state.exists():
            try:
                state = read_json(self.service.paths.ui_state)
                if set(state) == {"width", "height"} and all(type(n) is int for n in state.values()):
                    width = min(available_w, max(640, state["width"]))
                    height = min(available_h, max(420, state["height"]))
            except StorageError:
                # Window size is disposable, account configuration is not.
                pass
        self.minsize(min(640, available_w), min(420, available_h))
        self.geometry(f"{width}x{height}+{max(0, (self.winfo_screenwidth()-width)//2)}+{max(0, (self.winfo_screenheight()-height)//2)}")

    def _build(self) -> None:
        top = ttk.Frame(self, padding=(16, 12))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text=f"{TITLE}  |  v{__version__}", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(top, text="TEST  |  KS testmiljø").grid(row=0, column=1, sticky="e", padx=(12, 0))
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=12)
        self.pages: dict[str, ttk.Frame] = {}
        for label in ("Oversikt", "Oppsett", "SvarUt", "SvarInn", "Aktivitetslogg"):
            page = ttk.Frame(self.notebook)
            self.pages[label] = page
            self.notebook.add(page, text=label)
        self._overview()
        self._settings()
        self.api_ui = ApiViews(self)
        self._activity()
        footer = ttk.Label(self, textvariable=self.status, padding=(16, 10), wraplength=900)
        footer.grid(row=2, column=0, sticky="ew")
        self.bind("<Configure>", lambda e: footer.configure(wraplength=max(240, e.width-40)) if e.widget is self else None, add="+")

    def _overview(self) -> None:
        page = self.pages["Oversikt"]
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)
        info = ttk.Frame(page, padding=(16, 8))
        info.grid(row=0, column=0, sticky="ew")
        info.columnconfigure(0, weight=1)
        ttk.Label(info, text="Status", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        label = ttk.Label(info, text="Testsending og status (SvarUt), forsendelsesliste (SvarInn).\nIngen dokumentnedlasting eller kvittering. Kun enkeltbrukertest.", justify="left", wraplength=850)
        label.grid(row=1, column=0, sticky="ew", pady=(5, 6))
        info.bind("<Configure>", lambda e: label.configure(wraplength=max(240, e.width-32)))
        actions = ttk.Frame(info)
        actions.grid(row=2, column=0, sticky="w")
        ttk.Button(actions, text="Åpne oppsett", command=lambda: self.notebook.select(self.pages["Oppsett"])).pack(side="left")
        ttk.Button(actions, text="Kontroller lokalt", command=self.check_local).pack(side="left", padx=8)
        self.check_caption = ttk.Label(info, text="Kontroll av lagret oppsett. Ingen nettverkskontroll.")
        self.check_caption.grid(row=3, column=0, sticky="w", pady=(6, 0))
        area = ttk.Frame(page, padding=(16, 0, 16, 8))
        area.grid(row=1, column=0, sticky="nsew")
        self.check_table = table(area, (("area", "Tjeneste", 90), ("field", "Kontrollpunkt", 230), ("status", "Status", 145), ("detail", "Forklaring", 460)))

    def _settings(self) -> None:
        page = self.pages["Oppsett"]
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)
        actions = ttk.Frame(page, padding=(16, 10))
        actions.grid(row=0, column=0, sticky="ew")
        ttk.Button(actions, text="Lagre oppsett", command=self.save_setup).pack(side="left")
        ttk.Button(actions, text="Kontroller lokalt", command=self.check_local).pack(side="left", padx=8)
        ttk.Label(actions, textvariable=self.dirty_status).pack(side="left", padx=4)
        self.form = ScrollableForm(page)
        self.form.grid(row=1, column=0, sticky="nsew")
        body = self.form.body
        self.form.text(body, "Oppsettet opprettes automatisk og gjenbrukes neste gang. Alle kontofelt starter tomme. Passord fylles i egne maskerte øktfelt og lagres ikke. Private nøkkelverdier skal aldri limes inn.").pack(fill="x", pady=(0, 8))
        self.form.text(body, "Lokal oppsettfil: " + str(self.service.paths.setup)).pack(fill="x", pady=(0, 12))
        self.form.text(body, "TEST er eneste tillatte miljø. Bruk Fyll tomme testadresser for de offentlige API-adressene. Portaladresser brukes ikke som API-base.").pack(fill="x", pady=(0, 12))
        ttk.Button(body, text="Fyll tomme testadresser", command=self.fill_test_addresses).pack(anchor="w", pady=(0, 12))
        groups = (
            ("SvarUt / Maskinporten", "svarut", (
                ("api_base_url", "API-base-URL", False),
                ("account_id", "SvarUt konto-ID", False),
                ("integration_id", "Fiks integrasjons-ID", False),
                ("maskinporten_client_id", "Maskinporten klient-ID", False),
                ("signing_key_file", "Privat nøkkel / P12 / PFX", True),
                ("maskinporten_base_url", "Maskinporten testbase", False),
                ("maskinporten_key_id", "Registrert kid (valgfri)", False),
                ("signing_certificate_file", "PEM-/DER-sertifikatkjede", True),
            )),
            ("SvarInn", "svarinn", (
                ("api_base_url", "API-base-URL", False),
                ("service_username", "Service-brukernavn", False),
                ("private_key_file", "Privat PEM-nøkkel", True),
                ("public_certificate_file", "Offentlig PEM-sertifikat", True),
            )),
        )
        for title, group, specs in groups:
            box = ttk.LabelFrame(body, text=title, padding=12)
            box.pack(fill="x", pady=(0, 14))
            box.columnconfigure(1, weight=1)
            for row, (name, label, file_choice) in enumerate(specs):
                key = f"{group}.{name}"
                variable = tk.StringVar(self)
                self.fields[key] = variable
                ttk.Label(box, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
                entry = ttk.Entry(box, textvariable=variable, width=26)
                entry.grid(row=row, column=1, sticky="ew", pady=6)
                self.entries[key] = entry
                entry.bind("<FocusIn>", lambda _e, w=entry: self.form.show_widget(w))
                variable.trace_add("write", lambda *_args: self._dirty_changed())
                if file_choice:
                    ttk.Button(box, text="Velg fil", command=lambda k=key: self.choose_file(k)).grid(row=row, column=2, padx=(8, 0))
        secrets = ttk.LabelFrame(body, text="Passord for denne økten - lagres ikke", padding=12)
        secrets.pack(fill="x", pady=(0, 14))
        secrets.columnconfigure(1, weight=1)
        for row, (key, caption) in enumerate((("integration_password", "Fiks integrasjonspassord"),
                ("signing_key_password", "Nøkkelpassord (om kryptert)"), ("svarinn_password", "SvarInn servicepassord"))):
            ttk.Label(secrets, text=caption).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
            entry = ttk.Entry(secrets, textvariable=self.session_fields[key], show="*")
            entry.grid(row=row, column=1, sticky="ew", pady=6)
            entry.bind("<FocusIn>", lambda _e, w=entry: self.form.show_widget(w))
        self.clear_session_button = ttk.Button(secrets, text="Tøm passord og token", command=self.clear_session)
        self.clear_session_button.grid(row=3, column=1, sticky="w", pady=8)
        self.form.text(body, "Her lagres bare referanser til nøkkel-/sertifikatfiler, ikke filinnhold. Filene kopieres ikke. Passord og Maskinporten-token beholdes bare i minnet til appen lukkes eller økten tømmes. P12/PFX kan inneholde sertifikatkjeden. For PEM velges kid eller tilhørende sertifikatkjede.").pack(fill="x", pady=(0, 12))
        self.form.text(body, "Portalinlogging med TestID er ikke API-autentisering. Ikke legg TestID, kontoopplysninger, e-poster, nøkler eller logger i Git.").pack(fill="x")

    def _activity(self) -> None:
        page = self.pages["Aktivitetslogg"]
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)
        top = ttk.Frame(page, padding=16)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        ttk.Button(top, text="Oppdater visning", command=self.refresh_activity).grid(row=0, column=0)
        explanation = ttk.Label(top, text="Lokale hendelser. Ingen kontoverdier eller dokumentinnhold.", wraplength=400)
        explanation.grid(row=0, column=1, sticky="ew", padx=12)
        top.bind("<Configure>", lambda e: explanation.configure(wraplength=max(160, e.width-200)))
        content = ttk.Frame(page, padding=(16, 0, 16, 16))
        content.grid(row=1, column=0, sticky="nsew")
        self.activity_table = table(content, (("time", "Tid (lokal tidssone)", 270), ("text", "Hendelse", 580)))

    def _load_fields(self) -> None:
        data = self.service.setup.to_dict()
        for key, variable in self.fields.items():
            group, field = key.split(".", 1)
            variable.set(data[group][field])
        self._dirty_changed()

    def candidate(self) -> Setup:
        groups: dict[str, dict[str, str]] = {"svarut": {}, "svarinn": {}}
        for key, variable in self.fields.items():
            group, field = key.split(".", 1)
            groups[group][field] = variable.get().strip()
        return Setup(svarut=SvarUtSetup(**groups["svarut"]), svarinn=SvarInnSetup(**groups["svarinn"]))

    def is_dirty(self) -> bool:
        return self.candidate().to_dict() != self.service.setup.to_dict()

    def _dirty_changed(self) -> None:
        if len(self.fields) == 12:
            self.dirty_status.set("Ulagrede endringer" if self.is_dirty() else "Oppsett lagret lokalt")

    def choose_file(self, key: str) -> None:
        chosen = filedialog.askopenfilename(parent=self, title="Velg lokal nøkkel-/sertifikatfil")
        if chosen:
            self.fields[key].set(chosen)

    def _save_shortcut(self, _event: tk.Event) -> str:
        self.save_setup()
        return "break"

    def save_setup(self) -> bool:
        if hasattr(self, 'api_ui') and self.api_ui.task.busy:
            messagebox.showinfo("API-kall pågår", "Lagre oppsett etter at API-kallet er avsluttet.", parent=self)
            return False
        try:
            result = self.service.save(self.candidate())
        except StorageError as exc:
            messagebox.showerror("Oppsett ikke lagret", str(exc), parent=self)
            return False
        self._dirty_changed()
        self.refresh_checks()
        self.refresh_activity()
        self.status.set(result.warning or ("Oppsett lagret lokalt. Ingen KS-tilgang er testet." if result.changed else "Ingen endringer. Oppsettet var allerede lagret."))
        return True

    def refresh_checks(self, candidate: Setup | None = None) -> None:
        for item in self.check_table.get_children():
            self.check_table.delete(item)
        for check in self.service.inspect(candidate):
            self.check_table.insert("", "end", values=(check.area, check.label, check.state, check.detail))
        fit_columns(self.check_table)
        self.check_caption.configure(text="Kontroll av ulagrede felt. Ingen nettverkskontroll." if candidate is not None and self.is_dirty() else "Kontroll av lagret oppsett. Ingen nettverkskontroll.")

    def check_local(self) -> None:
        try:
            candidate = Setup.from_dict(self.candidate().to_dict())
            self.refresh_checks(candidate)
            self.service.activity.append("setup_checked")
            self.refresh_activity()
        except StorageError as exc:
            messagebox.showerror("Lokal kontroll", str(exc), parent=self)
            return
        self.status.set("Lokal kontroll utført. Ingen autentisering eller API-kall er testet.")
        self.notebook.select(self.pages["Oversikt"])

    def refresh_activity(self) -> None:
        if not hasattr(self, "activity_table"):
            return
        try:
            rows = self.service.activity.recent()
        except StorageError as exc:
            self.status.set(str(exc))
            return
        for item in self.activity_table.get_children():
            self.activity_table.delete(item)
        for row in rows:
            self.activity_table.insert("", "end", values=row)
        fit_columns(self.activity_table)
        if rows:
            self.activity_table.yview_moveto(1.0)

    def report_callback_exception(self, exc: type, val: BaseException, tb: Any) -> None:
        # Do not expose exception values that might contain account data or paths.
        try:
            self.service.activity.append("ui_error")
        except StorageError:
            pass
        messagebox.showerror("Uventet feil", "Handlingen kunne ikke fullføres. Ingen feildetaljer med oppsettverdier er logget.", parent=self)

    def close(self) -> None:
        if self._closing:
            return
        if self.api_ui.task.busy:
            messagebox.showinfo("API-kall pågår", "La API-kallet fullføre før du lukker klienten. Sending avbrytes ikke fra GUI.", parent=self)
            return
        if self.is_dirty():
            answer = messagebox.askyesnocancel("Ulagrede endringer", "Lagre oppsettet før avslutning?", parent=self)
            if answer is None or (answer and not self.save_setup()):
                return
        try:
            atomic_json(self.service.paths.ui_state, {"width": self.winfo_width(), "height": self.winfo_height()})
            self.service.activity.append("app_closed")
        except StorageError:
            if not messagebox.askyesno("Lokal lagring feilet", "Vinduinnstillinger eller avslutningslogg kunne ikke lagres. Avslutte likevel?", parent=self):
                return
        self.clear_session(log=False)
        self._closing = True
        self.destroy()

    def fill_test_addresses(self) -> None:
        for key, value in (("svarut.api_base_url", TEST_API_BASE), ("svarinn.api_base_url", TEST_API_BASE),
                           ("svarut.maskinporten_base_url", TEST_MASKINPORTEN_BASE)):
            if not self.fields[key].get().strip():
                self.fields[key].set(value)

    def clear_session(self, *, log: bool = True) -> None:
        if hasattr(self, 'api_ui') and self.api_ui.task.busy:
            return
        for value in self.session_fields.values():
            value.set("")
        self.service.gateway.clear_secrets()
        if log:
            try:
                self.service.activity.append("session_cleared")
            except StorageError:
                pass
            self.status.set("Passord og tokenbuffer er tømt for denne økten.")
            self.refresh_activity()
