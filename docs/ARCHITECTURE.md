# Arkitektur

## Implementert i a1

```text
run.py / python -m svarut_svarinn_client
    |-- GUI (Tkinter/ttk)
    |-- --check-setup (lokal kontroll)
          |
          v
       AppService
          |-- ConfigStore -> lokal setup.json
          |-- inspect_setup -> lokale kontrollpunkter
          |-- ActivityLog -> lokale, faste hendelseskoder
          `-- KsGateway -> sperrede operasjoner, ingen nettverkskode
```

GUI-et viser og redigerer data. Kjernen eier oppsettskjema, lagring,
validering og aktivitet. Ingen modul i core importerer GUI.
CLI og GUI bruker samme AppService og oppsettkontroller.

En prosesslås hindrer to klientinstanser med samme datamappe. Operativsystemet
frigir låsen ved prosessavslutning. Oppsett skrives via midlertidig fil,
flush/fsync og atomisk erstatning. Endring utenfor appen oppdages med en
fingerprint og overskrives ikke bevisst. Dette er enkeltbrukerlagring,
ikke en flerbruker-/nettverksdatabase.

Aktivitetsloggen er en enkel, lokal feilsøkingslogg. Den er **ikke** et
manipulasjonssikret revisjonsarkiv eller en implementert forsendelsesjournal.

## Planlagt, ikke implementert

Autentisering, HTTP-transport, SvarUt og SvarInn skal fortsatt ligge utenfor
GUI. Nettverksarbeid må kjøres utenfor GUI-tråden og rapportere tilbake
via trådsikker kø; Tk-widgets oppdateres bare i GUI-tråden.

Utgående sending trenger en varig transaksjonsjournal som skiller
`klargjort`, `sender`, `utfall ukjent`, `akseptert` og etterfølgende KS-status.
Ingen automatisk omsending etter tidsavbrudd uten avstemming.

Inngående behandling trenger at nedlasting, dekryptering, hashkontroll,
varig lokal lagring og kvittering er atskilte, gjenopptakbare trinn.
Hentet er ikke kvittert. MOTTATT i mottaks-API-et er heller ikke det samme
som journalført i et eksternt system.

Varig forsendelsesjournal og hemmelighetslager er ikke implementert.
Krav til databehandling, feilhåndtering og drift er beskrevet i
[GO-NOGO.md](GO-NOGO.md).

## Terminalserver og soner: krav og foreslått løsning

**Krav, ikke implementert:** flerbrukerdrift på terminalserver i sikret sone,
administratorstyrt oppsett og personlige Windows-brukere med tilgang
gjennom sonebestemte AD-sikkerhetsgrupper. Det skal ikke innføres et
parallelt manuelt appbrukerregister. Intranett skal kunne sende dokumenter som er
godkjent for den sonen. SvarInn-mottak skal bare skje i sikret sone; eventuell
utførsel skal følge virksomhetens eksisterende sluser. Et adresseregister
skal vurderes senere.

Foreslått komponentdeling er GUI per Windows-bruker og en separat
bakgrunnstjeneste per sone. Tjenesten eier felles oppsett, rettighetskontroll,
hemmeligheter, forsendelsesjournal og KS-kall. Den må autentisere hvem som
kaller og autorisere hver operasjon og hver tilgang til data. En verdi som
GUI-et sender som brukernavn, er ikke bevis på identitet.

Windows-identitet og AD-grupper er valgt som tilgangsprinsipp. Faktiske
gruppenavn og SID-er skal ligge i beskyttet installasjonsoppsett, ikke i Git.
Konkret transport, fysisk plassering og tjenestedrift er fortsatt forslag,
ikke valgt eller implementert.
Lokale Windows named pipes med eksplisitte tilgangsregler er en kandidat når
GUI og tjeneste kjører på samme server. Flere terminalservere krever en
avklart felles tjeneste og en autentisert forbindelse innen samme sone.

Mottak bør kjøres av tjenesten, uavhengig av åpne GUI-er. Bare én aktiv
mottaksarbeider per mottakersystem, eller koordinert låsing, skal behandle og
kvittere samme forsendelse. Brukernes GUI-er skal ikke konkurrere om KS-køen.
Ingen delt JSON-fil eller SQLite-fil på nettverksdisk innføres som
flerbrukerløsning; valgt lagring eies av tjenesten.

Foreslått retning er samme kodebase med forskjellig administrert sonepolicy.
SvarInn skal skjules for vanlige intranettbrukere og sperres i tjenesten;
fravær av mottaksoppsett alene skal ikke være sikkerhetsgrensen. Sonevalg
skal ikke være en personlig bryter som gir flere rettigheter. Sonene skal ha
separat runtime-lagring og legitimasjon, uten automatisk felles innboks eller
adresseregister. Dette innebærer ingen avhengighet til et sak-/arkivsystem.
Se [SECURITY.md](SECURITY.md), [CONFIGURATION.md](CONFIGURATION.md) og
[ROADMAP.md](ROADMAP.md).
