# GUI-kontrakt

## Oppbygning

Klienten bruker Tkinter/ttk og har ett hovedvindu. Oppsett, lokale kontroller
og aktivitetslogg er implementert; SvarUt- og SvarInn-operasjonene er sperret
i a1. GUI-et viser og redigerer data gjennom det felles tjenestelaget.

Ett hovedvindu med fem faner:

| Fane | Faktisk innhold i a1 |
| --- | --- |
| Oversikt | Lokale kontrollpunkter og eksplisitt ikke-produksjonsklar status |
| Oppsett | Tomme kontofelt, lokale filreferanser, lagring og kontroll |
| SvarUt | Planlagt flyt og sperrede knapper |
| SvarInn | Planlagt flyt og sperrede knapper |
| Aktivitetslogg | Faste, lokale hendelser uten kontoverdier |

Miljø og programversjon er synlige i hovedvinduet. `Registrert` betyr bare
at et felt passerer den lokale kontrollen. Det betyr ikke at KS har godtatt
identiteten, rettighetene eller nøkkelen.

Oversiktens statusfelt beskriver faktisk funksjon og begrensninger, ikke
prosjektfrister eller beslutningsløpet. Det viser at lokalt oppsett, kontroll
og aktivitetslogg finnes, mens KS-tilkobling, sending og mottak ikke er
implementert. Programversjonen beholdes i vinduets tekniske identifikasjon.

## Vinduer og navigasjon

Standardtekst er 11 punkt; overskrifter bruker samme størrelse med fet skrift.
Vinduet kan endre størrelse og startstørrelsen begrenses til skjermen.
Bare størrelse gjenbrukes, ikke en mulig utilgjengelig posisjon på en frakoblet skjerm.

Oppsett har egen vertikal rulling. Lagre/kontroll-knappene ligger utenfor
rulleområdet. Musehjul behandles bare over relevant skjema, og Tab-fokus
ruller feltet inn i synlig område. Tabeller har begge rulleretninger.
Ingen fast bunnflate skal skyve siste inputfelt utenfor tilgjengelig skjerm.

## Lagring og feilhåndtering

Fanebytte bevarer ulagrede felt. Lagre eller Ctrl+S skriver oppsettet.
Lukking med endringer gir Lagre / Forkast / Avbryt. Feilet lagring skal
ikke fjerne ulagrede felt eller gi falsk bekreftelse. Lik verdi er ingen ny
endring og produserer ikke en ny lagringshendelse.

Lokal kontroll lagrer ikke oppsettet og gjør ingen nettverkskall.
En nettverksfeil skal senere kunne vises separat fra lokalt ugyldig oppsett.
Ingen knapper skal simulere en vellykket sending eller mottakskvittering.

## Planlagt rolle- og sonetilpasning

Dette er ikke implementert i dagens femfaners skall. Senere skal GUI-et vise
bare funksjoner som både installasjonens sonepolicy og brukerens AD-baserte
rettigheter tillater. Tjenesten skal håndheve samme begrensning utenom GUI-et.

SvarInn skal ikke vises for vanlige brukere i intranett. En tjeneste som er
deaktivert for installasjonen, skal skilles fra en aktivert tjeneste som
mangler konfigurasjon; sistnevnte skal være synlig som oppsettmangel for
administrator. Personlige valg skal ikke aktivere en funksjon som sonepolicy
sperrer. Administrasjonsflater skal avgrenses fra dokumentbehandling.
