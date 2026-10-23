# SvarUt/SvarInn Client

Selvstendig Python-klient under utvikling for sending og mottak av dokumenter
via de offisielle API-ene til KS SvarUt og SvarInn.

## Status

Klienten har et grafisk brukergrensesnitt med lokal konfigurasjon, kontroll
av oppsett og aktivitetslogg. Oppsettet lagres og gjenbrukes mellom oppstarter.

Tilkobling til KS, sending via SvarUt og mottak via SvarInn er ennå ikke
implementert. Appen gjør ingen API-kall og er ikke klar for produksjonsbruk.

## Oppstart på Windows

Python 3.11 eller nyere med Tcl/Tk. Brukergrensesnittet bruker Tkinter/ttk;
ingen tredjepartspakker er nødvendige.

```bat
install.bat
test.bat
start.bat
```

Se [testing](docs/TESTING.md) for testprosedyre og plattformstatus.

## Lokale data

Appen oppretter og gjenbruker `setup.json` under
`%LOCALAPPDATA%\SvarUtSvarInnClient` på Windows, utenfor repoet.
Kontofeltene starter tomme og fylles inn lokalt.

Passord og private nøkkelverdier lagres ikke av appen; nøkkelfeltene
inneholder bare referanser til lokale filer. Lokalt oppsett, nøkler,
dokumenter og logger skal ikke legges i Git.

## Dokumentasjon

[Brukergrensesnitt](docs/GUI.md) · [Konfigurasjon](docs/CONFIGURATION.md) ·
[KS-API-er](docs/KS-API.md) · [Sikkerhet](docs/SECURITY.md) ·
[Dokumentoversikt](docs/README.md).

## Lisens

GNU General Public License v3. Se [LICENCE](LICENCE).
