# Arkitektur

## Implementert klient

```text
run.py / python -m svarut_svarinn_client
    |-- GUI (Tkinter/ttk) -> BackgroundTask -> TestOperations
    |-- --check-setup (bare lokal kontroll)
          |
       AppService
          |-- ConfigStore -> lokal setup.json
          |-- inspect_setup -> lokale kontrollpunkter
          |-- ActivityLog -> faste hendelseskoder
          `-- TestOperations
                |-- MaskinportenClient -> RS256 JWT grant / token i minnet
                |-- HttpsTransport -> testvert, TLS, ingen redirects/retry
                `-- OutboxStore -> lokal SQLite-journal
```

GUI-et viser/redigerer data; core eier validering, autentisering, API-kontrakter
og lagring. Ingen core-modul importerer Tk. Nettverksarbeid kjøres i én
arbeidertråd, og en trådsikker kø leverer resultat til GUI-tråden. Bare
GUI-tråden leser/oppdaterer widgets. Oppsett og øktpassord kopieres før
handlingen starter; lagring, ny API-handling og normal lukking sperres mens
arbeidet pågår. Dette er en enkeltbruker-testklient, ikke Windows-tjenesten
som er foreslått nedenfor.

En OS-lås hindrer to appinstanser med samme datamappe. Oppsett skrives atomisk,
og endringer utenfor appen oppdages. Skjema 1 leses uten å endre originalen;
skjema 2 skrives ved eksplisitt lagring. SQLite-journalen er lokal, ikke en
flerbruker-/nettverksdatabase. Se [CONFIGURATION.md](CONFIGURATION.md).

## Utgående journal og ukjent utfall

En sendehandling validerer testdata og PDF, henter token og lagrer `SENDING`
i journalen før dokumentet sendes. Journalen lagrer referanse, konto, mottaker,
tittel, filnavn, SHA-256 og senere KS-ID/status, men ikke dokumentinnhold eller
hemmeligheter. Ved HTTP 200 med gyldig ID lagres `ACCEPTED`; dette betyr
akseptert av KS, ikke levert til mottaker.

Dokumentert avvisning i utvalgte 4xx-svar gir `REJECTED`. Tidsavbrudd, 5xx,
uventet svar og andre uavklarte utfall gir `UNKNOWN`. Ved omstart går
uferdige `SENDING`-rader til `UNKNOWN`. Ingen sending gjentas automatisk.
Identiske, tidligere aksepterte eller uavklarte forsøk sperres lokalt med et
fingeravtrykk av konto, metadata og dokumenthash. Dette er ikke en garanti
for idempotens hos KS; automatisk avstemming er ikke implementert.

Journalfeil før POST stopper sendingen. Lagringsfeil etter KS-aksept viser
returnert ID og lokal referanse uten å omsende. Feil i den separate, enkle
aktivitetsloggen skal ikke omskrive et allerede lagret sendeutfall til feil.
Verken journalen eller aktivitetsloggen er manipulasjonssikrede revisjonsarkiv.

## Mottak og videre lagring

SvarInn henter bare en metadata-liste og viser utvalgte felt i minnet.
Nedlastingslenker følges ikke. Nedlasting, dekryptering, hashkontroll, varig
mottakslagring og kvittering gjenstår som separate, gjenopptakbare trinn.
Hentet liste er ikke dokumentmottak eller kvittert mottak.

Produksjonskrav beskrives i [GO-NOGO.md](GO-NOGO.md). Enkeltbrukertest med
øktpassord er ikke en implementasjon av flerbrukerarkitekturen nedenfor.

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
