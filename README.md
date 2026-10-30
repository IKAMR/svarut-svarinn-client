# SvarUt/SvarInn Client

Python-klient for sending av dokumenter og visning av innkommende forsendelser
via de offisielle API-ene til KS SvarUt og SvarInn.

## Status

Klienten har grafisk brukergrensesnitt, lokalt oppsett og aktivitetslogg.
I KS sitt testmiljø kan den hente SvarInn-forsendelseslisten, autentisere mot
Maskinporten, sende én PDF til en testorganisasjon og hente forsendelsesstatus.
Utgående forsøk og forsendelses-ID-er lagres i en lokal journal.

API-koden er testet med simulerte svar; faktisk tilgang og levering må
verifiseres mot testmiljøet. Dokumentnedlasting, dekryptering, mottakskvittering,
AD-tilgang og flerbrukerdrift er ikke implementert. Produksjon er sperret.

## Oppstart på Windows

Python 3.11 eller nyere med Tcl/Tk. `install.bat` oppretter/gjenbruker `.venv`
og installerer avhengighetene fra `requirements.txt`.

```bat
install.bat
test.bat
start.bat
```

Start med [oppsett og første API-test](docs/TEST-SETUP.md).
Bruk bare ufølsomme testdata og testmottakere.

## Lokale data

Oppsett, vindusvalg, aktivitetslogg og utgående journal lagres under
`%LOCALAPPDATA%\SvarUtSvarInnClient`, utenfor repoet, og gjenbrukes ved omstart.
Kontofelt fylles inn lokalt. Passord og token beholdes bare i minnet for
økten; oppsettet lagrer filreferanser, ikke privat nøkkelinnhold.

Oppsett, nøkler, mottakeropplysninger, dokumenter og logger skal ikke i Git.

## Dokumentasjon

[Brukergrensesnitt](docs/GUI.md) · [Konfigurasjon](docs/CONFIGURATION.md) ·
[KS-API-er](docs/KS-API.md) · [Sikkerhet](docs/SECURITY.md) ·
[Dokumentoversikt](docs/README.md).

## Lisens

GNU General Public License v3. Se [LICENCE](LICENCE).
