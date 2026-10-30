# Krav til funksjon, sikkerhet og drift

## Omfang og status

Kravene gjelder klientens sending, mottak, databehandling og feilhåndtering.
De brukes til å vurdere om funksjonene er tilstrekkelig verifisert for
produksjonsbruk. Dokumentet fastsetter ingen leverings- eller produksjonsdato.

**Klienten har avgrensede testoperasjoner, ikke produksjonsgodkjenning.**
Fungerende portaltilgang, utfylte felt eller beståtte enhetstester er ikke
verifikasjon av API-funksjonene.

## Funksjons- og kvalitetskrav

| ID | Kriterium for Go | Nødvendig bevis | Status |
| --- | --- | --- | --- |
| G01 | Brukerflyten fungerer på valgt Windows-klient og terminalserver, også med liten skjerm/høy DPI | Praktisk test av start, oppsett, sending, mottak og feilhåndtering | Brukeren har bekreftet test.bat og appstart; full brukerflyt og terminalserver gjenstår |
| G02 | Begge autentiseringsløp fungerer med riktige kontorettigheter | Vellykkede kall og negative tester av token, passord og nøkkel | API-kode og simulerte tester finnes; faktiske kontokall gjenstår |
| G03 | Nødvendige mottakertyper og leveringskanaler er verifisert | Sending til testperson og testorganisasjon, hoveddokument/vedlegg, status og kontroll av faktisk levering | Én PDF til testorganisasjon og status implementert; faktisk levering og øvrige mottakertyper gjenstår |
| G04 | SvarInn gir komplette, identiske og varig lagrede dokumenter/metadata | Ekte rundtur, dekryptering, SHA-256, store filer og flere forsendelser | Bare metadata-liste implementert; komplette dokumenter/kvittering gjenstår |
| G05 | Ingen tap/dobbeltbehandling ved feil og restart | Avbrudd under sending, ukjent sendeutfall, nedlasting, lagring og kvittering; kontrollerte gjenopptak | Lokal sendejournal, ukjent utfall og duplikatsperre testet med simulert transport; ekte avbrudd og mottaksflyt gjenstår |
| G06 | Hemmeligheter og dokumenter er forsvarlig beskyttet | ACL, hemmelighetslager, TLS, nøkkelbytte, skjermede logger, sikker fil-/ZIP-håndtering | Testverts-/TLS-policy, øktpassord og sanerte feil finnes; Windows-ACL, varig hemmelighetslager og mottakssikkerhet gjenstår |
| G07 | Aktivitet kan avstemmes og dokumenteres operativt | Varig forsendelsesjournal med referanser, status, feil og manuell oppfølging uten overflødig innhold | Lokal SQLite-sendejournal og faste logghendelser finnes; ikke manipulasjonssikret eller autorisert per bruker |
| G08 | Drift og gjenoppretting er gjennomførbare | Eier, backup med gjenopprettingstest, overvåking, sertifikatvarsling og brukerstøtte | Ikke verifisert |
| G09 | KS-forutsetninger og overgangen til produksjon er avklart | Produksjonstilgang, systemregistrering og eksplisitt godkjent, avgrenset produksjonsprøve | Avtalemulighet bekreftet privat; resten gjenstår |
| G10 | Bare verifiserte Windows-brukere med riktig AD-gruppetilgang får tiltenkte rettigheter | Test to samtidige brukere, manglende eller feil sonegruppe, avgrensning av admin-/brukerrolle, direkte tjenestekall, innsyn i andres data og tilbakekalling i aktive sesjoner | Ikke implementert |
| G11 | Sonegrensen kan ikke oppheves gjennom brukeroppsett | Test at intranett avvises ved SvarInn-kall og tilgang til sikret sones status, dokumenter, logger og nøkler; test at svar rutes til sikret mottak | Ikke implementert |

G03 skal tilpasses faktisk obligatorisk bruk før endelig Go/NoGo. NHN,
signering og andre spesialfunksjoner er ikke automatisk del av første omfang.
Ingen påkrevd kanal kan utelates bare fordi en enklere testorganisasjon virker.

## Kritiske feiltester

Usikkert sendesvar må gi «utfall ukjent», ikke automatisk ny sending.
Avstemming via referanse/status må testes før retry. Lokal referanse er ikke
uten videre en dokumentert servergaranti for idempotens.

For mottak skal testene avbryte før/etter varig lagring og før/etter kvittering.
En vellykket kvittering skal aldri bety at eneste kopi er en temporær fil.
Hashfeil, disk full, ugyldig nøkkel, path traversal og feil svarformat skal
stoppe behandling uten å kvittere mottatt.

Test at gjentatt polling, parallelle starter, en kø større enn én side,
nettutfall og restart ikke gir stille tap eller uendelig dobbelbehandling.
Dette er prosjektets krav, ikke en påstand om implementert funksjonalitet.

## Godkjenning for produksjonsbruk

Go krever dokumentert oppfyllelse av obligatoriske kriterier, akseptert
rest-risiko hos ansvarlig eier og en avklart reserveprosedyre.
NoGo dersom tap/duplikat/kvitteringsrisiko, tilgang, sikker lagring eller drift
ikke er løst. En begrenset pilot er ikke automatisk en full produksjonsgodkjenning.

Tekniske, anonymiserte testresultater kan versjoneres. Kontospesifikk evidens,
produksjonsverdier og virksomhetens fulle beslutningsunderlag beholdes lokalt
eller i godkjent intern dokumentasjon, uten avhengighet i kildekoden.
