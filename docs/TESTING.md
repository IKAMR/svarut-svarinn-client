# Testing

## Automatiserte tester

Windows: `install.bat`, deretter `test.bat`. Testinngangen bruker lokal `.venv`
og skriver `docs/test-results/v<versjon>.md`. Den bruker midlertidige mapper,
genererte testnøkler og simulerte API-svar, aldri brukerens oppsett. Utgående
socket-tilkoblinger er eksplisitt sperret under testkjøringen.

```text
python tools/run_tests.py
```

På en Linux-testmaskin med Xvfb: `xvfb-run -a python tools/run_tests.py`.
Dette tester ikke Windows-batchfiler, Windows-ACL eller faktisk terminalserver.
GUI-test uten skjerm kan bli hoppet over; det skal ikke omtales som bestått
praktisk GUI-test. Miljø og bibliotekversjon står i rapporten.

Dekningen omfatter eksisterende oppsett/lagring/lås/rulling, migrering fra
skjema 1, RS256-signatur og JWT-claims, PEM/P12/JWK, token-cache, eksakt
multipart og statuskontrakt, Basic Auth uten Maskinporten, TOM/utfylt SvarInn-
liste, TLS/URL-/redirect-sperrer, begrensede/sanerte svar, sendejournal før
POST, ukjent utfall, avvisning, duplikatsperre og gjenopptak ved omstart.
GUI-testene kontrollerer arbeidertråd, sperring under kall, testbekreftelse,
passord som ikke lagres, vedvarende ID og små vinduer.

Det automatiserte resultatet dokumenterer kodekontrakter, **ikke** ekte
KS-tilgang, kontoautorisasjon eller levering. Feil skal rettes i riktig lag,
ikke skjules ved å svekke gyldige tester.

## Praktisk Windows- og KS-test

| Steg | Forventet resultat |
| --- | --- |
| Kjør install.bat og test.bat | Python/Tk og kryptografibibliotek godkjent; rapport uten uforklarte hopp |
| Start med start.bat | TEST synlig, eksisterende oppsett beholdt, ingen automatisk nettverkshandling |
| Lagre eksisterende oppsett | Skjema oppgradert uten tap av kontoverdier; passord ikke i JSON |
| Reduser vindu; bruk Tab, rulling og fanebytte | Oppsett/SvarUt nås fullt, tabeller ruller |
| Gjør ulagret endring og forsøk API-kall | Lagring kreves før kallet; gammel konto brukes ikke i skjul |
| Følg SvarInn-testen i TEST-SETUP | Faktisk tom/utfylt liste skilles fra avvist autentisering |
| Test Maskinporten | Tokenhenting lykkes/feiler synlig, tokenet vises ikke |
| Send ufølsom test-PDF til testorganisasjon | Returnert ID og lokal referanse vises og lagres |
| Hent status og SvarInn-liste | Faktisk KS-status og eventuelt samme mottaks-ID |
| Lukk/start klienten | Journal/oppsett beholdt, passord må fylles på nytt |
| Test feilpassord og feil konto | Ingen falsk suksess, ingen råhemmeligheter i loggen |
| Kontroller git status/staged diff | Ingen oppsett, nøkler, journal, logger eller dokumenter |

Konkret feltoppsett: [TEST-SETUP.md](TEST-SETUP.md). Avbrudd under sending
skal bare testes kontrollert med testdata; ukjent utfall må avstemmes før
ny sending. AD, sonepolicy, dokumentnedlasting og kvittering er ikke aktivert.

## CLI og exit-koder

```text
python run.py --version
python run.py --check-setup
python run.py --data-dir .local --check-setup
```

CLI-kontrollen er fortsatt lokal, uten autentisering eller API-kall.
0: normal avslutning/versjonsvisning. 1: oppstarts-/lagringsfeil.
2: kontrollen finner mangler eller ikke implementerte kontrollpunkter
(også argparse bruker 2 ved syntaksfeil). Et fylt oppsett er ikke et
produksjons- eller tilgangsbevis.

Rapporter under `test-results/` kan versjoneres etter gjennomlesning.
Kontospesifikke praktiske resultater beholdes lokalt eller anonymiseres etter
reglene i [manual-test-results/README.md](manual-test-results/README.md).
