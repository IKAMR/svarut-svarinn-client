# Oppsett og første API-test

Dette er en enkeltbrukertest mot KS-test, ikke produksjon eller administrert
terminalserverdrift. Alle konto-/nøkkelverdier fylles inn lokalt. TestID for
portalinnlogging er ikke API-legitimasjon og skal ikke legges i kildekoden.

## Eksisterende testtilgang

KS support sin private e-post bekrefter at testorganisasjon og et SvarInn-
mottakersystem allerede er opprettet. Den bekrefter ikke at alle service-
passord, Fiks-integrasjon, kontorettigheter og Maskinporten-oppsett er ferdige.
Bruk det eksisterende testoppsettet; ingen verdier fra e-posten gjengis her.

Forvaltning skjer i [Fiks test](https://forvaltning.fiks.test.ks.no/) og
[SvarInn testforvaltning](https://svarut.fiks.test.ks.no/mottaker#/).
Portaladresser skal ikke brukes som API-base. Veiledere:
[SvarUt](https://ksdigital.no/tjenestene/svarut-tjenesten/svarut-konfigurasjon/) og
[SvarInn](https://ksdigital.no/tjenestene/svarut-tjenesten/svarinn/konfigurasjon-av-svarinn/).

## Start og gjenbruk av oppsett

Pakk deltaen over repoet. Kjør `install.bat` igjen for kryptografibiblioteket,
deretter `test.bat` og `start.bat`. Eksisterende `setup.json` leses og
kontoverdiene beholdes. Nytt skjema skrives ved **Lagre oppsett**.

I **Oppsett** trykker du **Fyll tomme testadresser**. Bare offentlige adresser
fylles; utfylte felt erstattes ikke. Kontrollert testbase er
`https://test.svarut.ks.no/api` for begge KS-tjenestene og
`https://test.maskinporten.no/` for Maskinporten.

## Første test: SvarInn-liste

1. Finn mottakersystemets **service-brukernavn og servicepassord** i
   SvarInn-testforvaltning. Dette er ikke mottakets visningsnavn eller TestID.
2. Fyll SvarInn API-base og service-brukernavn i **Oppsett**, og lagre.
3. Fyll **SvarInn servicepassord** i det maskerte øktfeltet. Det lagres ikke.
4. Velg **SvarInn → Hent forsendelsesliste**.

**Tilkobling bekreftet. Ingen ventende forsendelser** betyr at det autentiserte
API-kallet lyktes, men listen var tom. Med innhold vises ID, tittel, dato,
antall filer og ekstern referanse. Maks 200 returneres per kall; dette er
ikke et fullstendig historikkarkiv. Ingen dokumenter lastes ned eller kvitteres.

Maskinporten, SvarUt-kontofelt og privat mottaksnøkkel trengs ikke for dette
listekallet. Nøkkelparet må etableres for den senere nedlastingstesten.
Kilde: [SvarInn V2](https://developers.fiks.ks.no/api/svarinn-api-v2.json) og
[autentisering](https://developers.fiks.ks.no/tjenester/svarut/svarinn-rest/index.html).

## SvarUt: autentisering og sending

Følgende må være etablert hos KS/Maskinporten: test-avsenderkonto, en
Fiks-integrasjon med tilgang til kontoen, integrasjonspassord og en
Maskinporten-klient med scope `ks:fiks`. Nøkkelen må tilhøre registreringen.
Et portal-TestID og et testmottak alene gir ikke SvarUt-API-tilgang.
Kilde: [Fiks-integrasjoner](https://developers.fiks.ks.no/felles/integrasjoner/).

Fyll API-base, konto-ID, integrasjons-ID, Maskinporten klient-ID og testbase.
Velg privat RSA-signering med én av disse variantene:

| Variant | Lokalt oppsett |
| --- | --- |
| Forhåndsregistrert asymmetrisk nøkkel/sertifikat | Privat PEM/P12/PFX/JWK-fil og registrert **kid** |
| Test-virksomhetssertifikat via `x5c` | P12/PFX med privatnøkkel/sertifikatkjede, eller privat PEM og matchende PEM/DER-sertifikatfil/-kjede; **kid** er tomt |

Det er RSA/RS256 som er implementert. En tilfeldig selvsignert testnøkkel
som brukes i enhetstestene gir ikke tilgang hos Maskinporten. Korrekt
registrering/sertifikatkjede må godtas der. Det separate feltet
**PEM-/DER-sertifikatkjede** er ikke det samme som SvarInn-mottakssertifikatet.
Se [JWT grant](https://docs.digdir.no/docs/Maskinporten/maskinporten_protocol_jwtgrant).

Lagre oppsettet, fyll **Fiks integrasjonspassord** og eventuelt
**Nøkkelpassord (om kryptert)** i øktfeltene. Velg **SvarUt → Test Maskinporten**.
Suksess bekrefter tokenhenting, ikke at Fiks-integrasjonen kan bruke kontoen.

For sending:

1. Velg én ufølsom PDF, testorganisasjonsnummer, mottakernavn og tittel.
   Bruk ny tittel for hver bevisst nye test. Klientens filgrense er 20 MiB;
   dette er ikke KS sin generelle grense eller en full PDF-validering.
2. Sett **Forsendelsestype** bare når testmottakets ruting krever det.
   Testorganisasjonen må være koblet til mottakersystemet for å sees i SvarInn.
3. Bekreft testdata, trykk **Send testforsendelse** og bekreft sendingen.
   Appen bruker kun digital levering, uten print.
4. Ved aksept lagres og vises KS sin forsendelses-ID. Velg **Hent status**.
   Akseptert av KS er ikke det samme som levert; status hentes manuelt.
5. Hent SvarInn-listen igjen. Sammenlign forsendelses-ID med sendingen.

Dette tester sending, status og mottaksmetadata. En komplett dokumentrundtur
med nedlasting, dekryptering, SHA-256-sammenligning og kvittering gjenstår.
Bruk testpersoner/-organisasjoner fra Tenor og aldri sensitive dokumenter:
[KS testmiljø](https://developers.fiks.ks.no/tjenester/svarut/testmiljo/index.html).

## Feil, omstart og trygg deling

**Ukjent utfall** etter sending betyr at KS kan ha akseptert forsendelsen.
Ikke send på nytt eller slett journalen. Avstem ekstern referanse/ID i KS
sin testforvaltning. Automatisk avstemming og omsending er ikke implementert.
Tydelig avviste forsøk kan prøves manuelt etter at feilen er rettet.

401/403 peker mot legitimasjon/rettigheter. Kontroller riktig testmiljø,
servicepassord eller Fiks-kontotilgang. Ved TLS-feil undersøkes klokke,
sertifikattillit og eventuell virksomhetsproxy; ikke deaktiver TLS-kontrollen.
En ny **Test Maskinporten** henter et nytt token. Omstart tømmer øktpassordene,
men beholder oppsett og journal. Utfylte kontoer legges ikke inn på nytt.

Del bare redigerte testresultater og appens skjermede feilkoder, ikke passord,
token, nøkler, oppsettfiler, journalen eller rå HTTP-responser. Eventuelle
KS-feil-ID-er kan brukes i en godkjent supporthenvendelse. Teknisk dialog
med KS foregår i `#fiks-integrasjon`.
