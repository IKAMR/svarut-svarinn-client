# Kodekart

| Fil/område | Ansvar |
| --- | --- |
| `run.py`, `__main__.py` | Oppstart, argumenter, instanslås, GUI/lokal kontroll |
| `__init__.py` | Autoritativ versjon |
| `core/paths.py` | Per-bruker datamappe og avgrensning mot repoet |
| `core/storage.py` | Begrenset JSON-lesing, atomisk skriving, OS-lås |
| `core/config.py` | Oppsettskjema og endringskonflikt |
| `core/readiness.py` | Lokal utfyllingskontroll og testadresse-policy |
| `core/activity.py` | Faste, dataminimerte aktivitetshendelser |
| `core/services.py` | Felles app-tjenester og sperret KS-grense |
| `ui/app.py` | Ett hovedvindu, faner, felt og handlinger |
| `ui/widgets.py` | Rullbart skjema, fokus og tabeller |
| `tools/check_runtime.py` | Python/Tk-kontroll uten brukeroppsett |
| `tools/run_tests.py` | Tester og versjonert Markdown-rapport |
| `tests/` | Kjerne-, GUI- og repositorykontroller |

Pakkestier i tabellen er relative til `svarut_svarinn_client/` med unntak av
rotfiler, `tools/` og `tests/`. Oppsett og logger ligger ikke i denne strukturen.
