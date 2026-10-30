# Kodekart

| Fil/område | Ansvar |
| --- | --- |
| `run.py`, `__main__.py` | Oppstart, argumenter, instanslås, GUI/lokal kontroll |
| `__init__.py` | Autoritativ versjon |
| `core/paths.py`, `core/storage.py` | Per-bruker datamappe, JSON, atomisk lagring og OS-lås |
| `core/config.py` | Strengt skjema 2, lesing av skjema 1, endringskonflikt |
| `core/readiness.py` | Lokal utfyllings-/filkontroll, aldri nettverk |
| `core/activity.py` | Faste dataminimerte hendelser |
| `core/services.py` | Felles applikasjonstjeneste for oppsett, logg og KS-operasjoner |
| `core/network.py` | HTTPS, testverts-/operasjonspolicy, grenser og skjermede feil |
| `core/auth.py` | Økthemmeligheter, RSA/RS256 JWT grant, Maskinporten og tokencache |
| `core/ks_api.py` | SvarInn-liste, Send V3 multipart, Status V3 og sendetilstand |
| `core/outbox.py` | Lokal SQLite-journal, referanser, duplikatsperre og restart |
| `ui/app.py` | Hovedvindu, Oppsett, øktpassord, lokal kontroll og aktivitet |
| `ui/api_views.py` | SvarUt/SvarInn-flater, snapshots, bekreftelser og resultater |
| `ui/tasks.py` | Én arbeidertråd, kø og tilbakelevering i GUI-tråden |
| `ui/widgets.py` | Rullbart skjema, fokus og tabeller |
| `tools/check_runtime.py` | Python/Tk/cryptography-kontroll |
| `tools/run_tests.py` | Nettverkssperrede tester og versjonert Markdown-rapport |
| `tests/` | Core-, API-kontrakt-, kryptografi-, feiltilfelle-, GUI- og repositorytester |

Pakkestier er relative til `svarut_svarinn_client/`, unntatt rotfiler,
`tools/` og `tests/`. Produksjonskode bruker aldri testtransporten. Ekte
legitimasjon, testorganisasjon eller mottakere skal ikke inn i kildefiler.
