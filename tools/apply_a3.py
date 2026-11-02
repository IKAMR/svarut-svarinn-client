"""Apply v0.1.0-a3 delta to a CLEAN v0.1.0-a2 checkout. No Git actions."""
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
changes = {}


def edit(path, old, new):
    current = changes.get(path)
    if current is None:
        current = (repo / path).read_text(encoding='utf-8')
    if current.count(old) != 1:
        raise RuntimeError(f'Expected a2 anchor not found exactly once: {path}: {old[:75]!r}')
    changes[path] = current.replace(old, new, 1)

api = 'svarut_svarinn_client/core/ks_api.py'
net = 'svarut_svarinn_client/core/network.py'
ui = 'svarut_svarinn_client/ui/api_views.py'
app = 'svarut_svarinn_client/ui/app.py'
edit('svarut_svarinn_client/__init__.py', '__version__ = "0.1.0-a2"', '__version__ = "0.1.0-a3"')
edit(api, 'from .outbox import OutboxStore', 'from .inbox import receive_delivery\nfrom .outbox import OutboxStore')
edit(api, "'files': len(item['filer']), 'reference': display_text(item.get('eksternRef'), 100)})", "'files': len(item['filer']), 'reference': display_text(item.get('eksternRef'), 100),\n                         'metadata': item})")
edit(api, '    def receive(self) -> None:\n        raise ApiError("Dokumentnedlasting og dekryptering er ikke implementert. Bruk Hent forsendelsesliste.")', '''    def receive(self, setup: Setup, secrets: SessionSecrets, metadata: dict) -> dict:
        config = self._setup(setup).svarinn
        base = test_base(config.api_base_url)
        user = text_field(config.service_username, 'SvarInn service-brukernavn', 2048)
        if ':' in user or not secrets.svarinn_password:
            raise ApiError('SvarInn servicepassord mangler for denne okten.')
        if len(secrets.svarinn_password) > 4096 or any(ord(c) < 32 for c in secrets.svarinn_password):
            raise ApiError('Ugyldig servicepassord.')
        credential = base64.b64encode((user + ':' + secrets.svarinn_password).encode()).decode('ascii')
        result = receive_delivery(self.transport, base_url=base,
            authorization='Basic ' + credential, metadata=metadata,
            private_key_file=config.private_key_file,
            public_certificate_file=config.public_certificate_file,
            data_root=self.paths.root)
        self._log('svarinn_download_verified')
        return result''')
edit(api, "        self.transport = transport or HttpsTransport()", "        self.paths = paths\n        self.transport = transport or HttpsTransport()")
edit(net, "    if method == 'GET' and parts.path == '/api/svarinn/v2/forsendelser':\n        return", "    if method == 'GET' and parts.path == '/api/svarinn/v2/forsendelser':\n        return\n    if method == 'GET' and re.fullmatch(r'/api/svarinn/v2/forsendelser/[a-f0-9-]{36}', parts.path):\n        uuid_text(parts.path.rsplit('/', 1)[-1], 'Forsendelses-ID')\n        return")
edit(net, '    @staticmethod\n    def _read(response) -> bytes:', '''    def request_bytes(self, method: str, url: str, *, headers=None, max_bytes: int):
        validate_target(method, url)
        if method != 'GET' or not url.startswith(TEST_API_BASE + '/svarinn/v2/forsendelser/'):
            raise ApiError('Binaer nedlasting er bare tillatt fra SvarInn V2 i testmiljo.')
        if not 0 < max_bytes <= 200 * 1024 * 1024:
            raise ApiError('Ugyldig maksimal nedlastingsstorrelse.')
        request_headers = {'User-Agent': 'SvarUtSvarInnClient', 'Accept': '*/*', **(headers or {})}
        if any(not isinstance(v, str) or any(ord(c) < 32 or ord(c) == 127 for c in v)
               for v in request_headers.values()):
            raise ApiError('Ugyldig HTTP-header.')
        try:
            request = Request(url, headers=request_headers, method='GET')
            with self._opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                if response.geturl() != url:
                    raise ApiError('Uventet omdirigering under nedlasting.')
                if response.status != 200:
                    raise http_error(response.status, b'')
                chunks, count = [], 0
                started = time.monotonic()
                while True:
                    chunk = response.read(min(65536, max_bytes + 1 - count))
                    count += len(chunk)
                    if count > max_bytes or time.monotonic() - started > 180:
                        raise ApiError('Nedlastingen overskred tillatt storrelse eller tid.')
                    if not chunk:
                        return b''.join(chunks)
                    chunks.append(chunk)
        except HTTPError as exc:
            try:
                raw = exc.read(65536)
            except OSError:
                raw = b''
            finally:
                exc.close()
            raise http_error(exc.code, raw) from None
        except (TimeoutError, socket.timeout, ssl.SSLError, URLError, OSError, ValueError, HTTPException):
            raise ApiError('SvarInn-nedlasting feilet. Ingen autorisasjon eller raa respons logget.') from None

    @staticmethod
    def _read(response) -> bytes:''')
edit(ui, 'import tkinter as tk', 'import os\nimport tkinter as tk')
edit(ui, "        self.incoming_rows = []", "        self.incoming_rows = []\n        self.incoming_by_tree_id = {}",)
edit(ui, "'SvarInn - innkommende metadata'", "'SvarInn - innkommende forsendelser'")
edit(ui, "'Inntil 200 forsendelser. Ingen nedlasting eller kvittering.'", "'Velg en forsendelse og trykk Last ned og kontroller. CMS dekrypteres lokalt og SHA-256 kontrolleres. INGEN kvittering sendes.'")
edit(ui, "        ttk.Button(actions, text='Gå til Oppsett'", "        self._button(actions, 'Last ned og kontroller valgt', self.download_selected, row=0, column=1)\n        ttk.Button(actions, text='Gå til Oppsett'")
edit(ui, "command=lambda: self.app.notebook.select(self.app.pages['Oppsett'])).grid(row=0, column=1)", "command=lambda: self.app.notebook.select(self.app.pages['Oppsett'])).grid(row=0, column=2)")
edit(ui, "        self.incoming_rows = []\n        self.incoming.delete(*self.incoming.get_children())", "        self.incoming_rows = []\n        self.incoming_by_tree_id.clear()\n        self.incoming.delete(*self.incoming.get_children())")
edit(ui, "                self.incoming.insert('', 'end', values=(row['id'], row['title'], row['date'], row['files'], row['reference']))", "                item_id = self.incoming.insert('', 'end', values=(row['id'], row['title'], row['date'], row['files'], row['reference']))\n                self.incoming_by_tree_id[item_id] = row")
edit(ui, "f'Tilkobling bekreftet. {len(rows)} forsendelser vist. Ingen nedlasting eller kvittering.')", "f'Tilkobling bekreftet. {len(rows)} forsendelser vist. Velg en rad for kontrollert nedlasting.')")
edit(ui, '    def refresh_history(self):', '''    def download_selected(self):
        selection = self.incoming.selection()
        if len(selection) != 1 or selection[0] not in self.incoming_by_tree_id:
            self.receive_result.set('Velg en forsendelse i listen forst.')
            return
        snapshot = self.snapshot()
        if snapshot is None or self.task.busy:
            return
        selected = self.incoming_by_tree_id[selection[0]]
        if not messagebox.askyesno('Last ned fra KS test?',
                'Last ned og dekrypter valgt forsendelse lokalt?\\n\\n' + selected['id'] +
                '\\n\\nIngen mottakskvittering sendes.', parent=self.app):
            return
        def success(value):
            self.receive_result.set('Kontrollert mottak: ' + value['id'] +
                '\\nAntall SHA-256-kontrollerte filer: ' + str(value['files']) +
                '\\nLagringsmappe: ' + value['path'] + '\\nIngen kvittering sendt til KS.')
        self._run('Nedlasting og integritetskontroll',
                  lambda: self.gateway.receive(*snapshot, selected['metadata']), success, self.receive_result)

    def refresh_history(self):''')
edit(app, 'Ingen dokumentnedlasting eller kvittering. Kun enkeltbrukertest.', 'Kontrollert nedlasting av SvarInn-dokumenter. Ingen mottakskvittering. Kun enkeltbrukertest.')

# Verify all anchors before making ANY change to recipient repository.
newfile = repo / 'svarut_svarinn_client/core/inbox.py'
if newfile.exists():
    raise RuntimeError('inbox.py exists already; refusing to overwrite')
for path, contents in changes.items():
    compile(contents, path, 'exec') if path.endswith('.py') else None
compile((root / 'svarut_svarinn_client/core/inbox.py').read_text(encoding='utf-8'), 'inbox.py', 'exec')
for path, contents in changes.items():
    (repo / path).write_text(contents, encoding='utf-8')
shutil.copy2(root / 'svarut_svarinn_client/core/inbox.py', newfile)
print('a3 applied:', ', '.join(changes), 'plus inbox.py')
print('Run test.bat. No Git commit or push performed.')
