# Versjonshistorikk

## v0.1.0 - under utvikling

### Gjeldende utviklingstrinn: v0.1.0-a2

Reelle testoperasjoner i GUI: SvarInn V2-liste med Basic Auth,
Maskinporten RS256-tokenhenting, Send V3 for én PDF til testorganisasjon
og Status V3-oppslag. SvarUt lagrer lokal referanse og KS-ID i SQLite,
skiller akseptert/avvist/ukjent utfall og gjentar ikke sending automatisk.

Passord og token beholdes bare i minnet. Oppsett fra a1 gjenbrukes gjennom
lesestøtte for skjema 1; eksplisitt lagring skriver skjema 2. Offentlige
testadresser kan fylles fra GUI uten forhåndsutfylte kontoverdier.
Nettverksarbeid kjøres utenfor GUI-tråden, med sanerte feil og sperre mot
produksjon/redirects. `install.bat` installerer `cryptography`.

Automatiserte kontrakt-/feil-/GUI-tester bruker bare simulert transport og
genererte nøkler. Ingen faktisk KS-tilgang eller levering er verifisert som
del av denne leveransen. Windows- og KS-test utføres lokalt. Nedlasting,
dekryptering, kvittering, AD-tilgang og flerbrukertjeneste er ikke implementert.

### Tidligere utviklingstrinn: v0.1.0-a1

Python-GUI med fem faner, lokalt JSON-oppsett, gjenbruk ved omstart,
atomisk lagring, instanslås og faste aktivitetshendelser. Oppsettkontrollene
var lokale; ingen API-kall. Windows-inngangene `install.bat`, `test.bat` og
`start.bat` og dokumentasjonsstrukturen ble etablert.
