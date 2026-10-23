# Testing

## Automatisert test

Windows: `install.bat`, deretter `test.bat`. Testinngangen bruker lokal `.venv`
og skriver `docs/test-results/v<versjon>.md`. Den starter ikke normal klient
og leser ikke det virkelige brukeroppsettet. Det gjøres ingen KS-kall.

For utvikling kan samme testinngang kjøres som:

```text
python tools/run_tests.py
```

På en Linux-testmaskin med Xvfb: `xvfb-run -a python tools/run_tests.py`.
Dette verifiserer ikke Windows `.bat`, Windows-ACL, Windows-låsing eller
praktisk DPI-/skjermoppførsel. GUI-tester uten display kan bli hoppet over på
Linux; et slikt resultat markeres, ikke omtales som full GUI-test.

Testene dekker førstegangsoppsett, gjenbruk, korrupt JSON, konflikter, atomisk
lagringsfeil, produksjonsmiljøsperre, testadresse-policy, faste logger,
instanslås, CLI, GUI-lagring/lukking/fanebytte, rulling, dokumentlenker og
.gitignore. Feil i tester skal rettes i riktig lag, ikke skjules ved å svekke
implementasjonen eller slette relevant dekning.

## Praktisk Windows-test av a1

| Steg | Forventet resultat |
| --- | --- |
| Kjør install.bat og test.bat | Python/Tk godkjent; testresultatet leses, eventuelle hopp forklares |
| Start med start.bat | Ett hovedvindu; riktig versjon og TEST; ingen ekte API-handlinger |
| Velg Oppsett | Tomme felter første gang; lokal datamappe utenfor repoet synlig |
| Registrer ufølsomme/syntetiske testverdier og lagre | Lagret status; faste logghendelser uten verdiene |
| Lukk og start på nytt | Samme oppsett gjenbrukes |
| Gjør ulagret endring, bytt fane, lukk med Avbryt | Endringen er fortsatt synlig |
| Reduser vindu; test Tab og musehjul til siste felt | Hele skjemaet nås; Lagre/kontroll er tilgjengelig |
| Kontroller lokalt | Mangler/ugyldig/registrert, aldri «KS-tilgang OK» |
| Forsøk ny klient med samme datamappe | Ny instans avvises; første instans fortsetter |
| Undersøk git status og staged diff | Ingen setup, nøkler, logger eller korrespondanse |

Ikke bruk a1 til ekte dokumenter. Ugyldige kontoverdier kan lagres for å
prøve skallet, men lokal kontroll vil markere formatfeil.

## CLI og exit-koder

```text
python run.py --version
python run.py --check-setup
python run.py --data-dir .local --check-setup
```

0: normal avslutning/versjonsvisning. 1: oppstarts-/lagringsfeil.
2: lokal kontroll viser mangler/ikke implementerte funksjoner (også argparse
bruker 2 ved syntaksfeil). `--check-setup` kan ikke godkjenne a1 for API-bruk
selv om alle felt er fylt ut.

Del aldri brukerens setup.json, e-post eller privatnøkler som feilrapport.
Den automatiske rapporten bruker bare syntetiske testdata og erstatter vanlige
lokale stier, men gjennomlesning før deling/commit er fortsatt nødvendig.
