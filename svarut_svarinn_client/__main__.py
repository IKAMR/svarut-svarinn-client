"""Local GUI and offline setup inspection. This release performs no API calls."""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .core.paths import StorageError, resolve_paths
from .core.services import AppService
from .core.storage import InstanceLock


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Selvstendig SvarUt/SvarInn-klient - lokalt TEST-skall")
    parser.add_argument("--version", action="version", version=f"v{__version__}")
    parser.add_argument("--data-dir", metavar="MAPPE", help="Lokal datamappe; standard er brukerens programdata")
    parser.add_argument("--check-setup", action="store_true", help="Kontroller lokalt oppsett uten GUI eller nettverk")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        print("Python 3.11 eller nyere kreves.", file=sys.stderr)
        return 1
    try:
        paths = resolve_paths(args.data_dir)
        paths.prepare()
        with InstanceLock(paths.lock):
            service = AppService(paths)
            if args.check_setup:
                checks = service.inspect()
                for check in checks:
                    print(f"{check.area} | {check.label}: {check.state} - {check.detail}")
                print("Ingen API-kall utført. Denne versjonen er ikke produksjonsklar.")
                return 2 if any(c.state != "Registrert" for c in checks) else 0
            try:
                from .ui.app import App
            except ImportError:
                print("Tkinter mangler. Installer Python med Tcl/Tk-støtte.", file=sys.stderr)
                return 1
            service.activity.append("app_started")
            app = App(service)
            app.mainloop()
    except StorageError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        # No raw traceback/account content in ordinary console output.
        print("Klienten kunne ikke kjøre. Kontroller Python/Tk og lokal datamappe.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
