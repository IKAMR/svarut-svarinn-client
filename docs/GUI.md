# GUI-kontrakt

## Oppbygning

Klienten bruker Tkinter/ttk, ett hovedvindu og fem faner. Ingen API-kall
utføres automatisk ved oppstart, fanebytte eller lokal oppsettkontroll.

| Fane | Innhold |
| --- | --- |
| Oversikt | Lokal oppsettkontroll, TEST og funksjonsbegrensninger |
| Oppsett | Lokale konto-/nøkkelreferanser, lagring, offentlige testadresser og maskerte øktpassord |
| SvarUt | Maskinporten-test, én PDF til testorganisasjon, statusoppslag og lokal utgående journal |
| SvarInn | Hent metadata-liste; vis ID, tittel, dato, filantall og ekstern referanse |
| Aktivitetslogg | Faste, lokale hendelser uten kontoverdier eller dokumentinnhold |

**Registrert** er bare lokal formatkontroll. **Maskinporten-token hentet**
er ikke bekreftet Fiks-kontotilgang. **Akseptert av KS** er ikke levert.
En autentisert tom SvarInn-liste er bekreftet tilkobling uten ventende
forsendelser, ikke bevis på fungerende dokumentmottak. Etter mislykket
listehenting vises ikke tidligere rader som om de var et nytt resultat.

Statusfelt beskriver faktisk funksjon, ikke prosjektfrister eller lovet
produksjonsdato. Miljø og programversjon vises som teknisk kontekst.

## Vinduer og navigasjon

Standardtekst er 11 punkt; overskrifter bruker samme størrelse med fet skrift.
Vinduet kan endre størrelse og begrenses til skjermen. Bare størrelse gjenbrukes,
ikke en mulig utilgjengelig posisjon på en frakoblet skjerm.

Oppsett og SvarUt har vertikal rulling. Lagre/kontroll ligger utenfor
oppsettrullingen. Musehjul gjelder relevant skjema, Tab-fokus ruller feltet
inn i synlig område, og tabeller har begge rulleretninger. SvarInn-tabellen
beholder plass og rulling i et lite vindu.

## Handlinger og lagring

Fanebytte bevarer ulagrede oppsettfelt. Lagre eller Ctrl+S skriver oppsettet.
Lukking med endringer gir Lagre / Forkast / Avbryt. Feilet lagring beholder
feltene og gir ingen falsk bekreftelse. Uendret oppsett produserer ingen ny
lagringshendelse. Passordfeltene inngår ikke i oppsettslagringen.

API-handlinger krever lagret oppsett og kjøres i en arbeidertråd. Nytt kall,
lagring, tømming av passord og normal lukking er sperret mens kallet pågår.
Vindusflytting, fanebytte og rulling skal fortsatt fungere. Feil vises uten
rå HTTP-respons, Authorization-header eller token.

Sending krever bekreftelse på ufølsomme testdata og en egen sendebekreftelse.
Ved retur vises faktisk KS-ID; ingen demonstrasjons-ID eller simulert suksess
brukes i appen. Velg journalrad for å fylle statusfeltet. Ny bevisst test
med samme dokument/mottaker må ha ny tittel; ukjent utfall skal avstemmes
først, ikke omgås. SvarInn har ingen knapp for nedlasting eller kvittering.

Se [TEST-SETUP.md](TEST-SETUP.md) for konkret testrekkefølge.

## Planlagt rolle- og sonetilpasning

Dette er ikke implementert i dagens testklient. Senere skal GUI-et vise
bare funksjoner som både installasjonens sonepolicy og brukerens AD-baserte
rettigheter tillater. Tjenesten skal håndheve samme begrensning utenom GUI-et.

SvarInn skal ikke vises for vanlige brukere i intranett. En tjeneste som er
deaktivert for installasjonen, skal skilles fra en aktivert tjeneste som
mangler konfigurasjon; sistnevnte skal være synlig som oppsettmangel for
administrator. Personlige valg skal ikke aktivere en funksjon som sonepolicy
sperrer. Administrasjonsflater skal avgrenses fra dokumentbehandling.
