"""Run offline tests and write a shareable, versioned Markdown report."""
from __future__ import annotations

import io
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from svarut_svarinn_client import __version__


def main() -> int:
    buffer = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)
    text = buffer.getvalue()
    replacements = {str(ROOT): "<REPO>", str(Path.home()): "<HOME>", tempfile.gettempdir(): "<TEMP>"}
    for original, placeholder in sorted(replacements.items(), key=lambda item: -len(item[0])):
        text = text.replace(original, placeholder)
    print(text)
    status = "BESTATT" if result.wasSuccessful() and not result.skipped else "BESTATT MED HOPP" if result.wasSuccessful() else "FEILET"
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = (f"# Testresultat v{__version__}\n\n"
              f"Tid (UTC): {stamp}\n\n"
              f"Miljo: {platform.system()}, Python {platform.python_version()}\n\n"
              f"Resultat: **{status}**. {result.testsRun} tester; "
              f"{len(result.failures)} feil, {len(result.errors)} unntak, {len(result.skipped)} hopp.\n\n"
              "Testene bruker bare syntetiske verdier og midlertidige mapper. "
              "Ingen KS-kall, ekte legitimasjon eller produksjonstest. "
              "GUI-testene er automatiserte kontroller, ikke manuell Windows-aksept.\n\n"
              "```text\n" + text + "```\n")
    output = ROOT / "docs" / "test-results" / f"v{__version__}.md"
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    except OSError:
        print("Test report could not be saved.", file=sys.stderr)
        return 1
    print(f"Report: docs/test-results/v{__version__}.md")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
