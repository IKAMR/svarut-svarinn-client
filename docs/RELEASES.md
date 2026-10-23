# Versjonshistorikk

## v0.1.0 - under utvikling

### Gjeldende utviklingstrinn: v0.1.0-a1

Python-GUI med Oversikt, Oppsett, SvarUt, SvarInn og Aktivitetslogg.
Lokalt JSON-oppsett gjenbrukes ved restart, feilaktige filer nullstilles ikke,
og samme datamappe kan bare åpnes av én klientinstans. Aktivitetsloggen
inneholder faste hendelser uten kontoverdier. Oppsettkontrollene er lokale
og utfører ingen nettverkskall.

Windows-inngangene `install.bat`, `test.bat` og `start.bat` inngår.
Dokumentasjonen beskriver funksjoner, konfigurasjon, API-grunnlag, sikkerhet,
arkitektur og testing.

Autentisering, sending, mottak, dekryptering og kvittering er ikke implementert.
Ingen produksjonsgodkjenning eller reell KS-test er utført. Automatisert
Linux/Tk-test og praktisk Windows-test skal ikke omtales som samme evidens.
