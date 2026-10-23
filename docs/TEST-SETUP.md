# Oppsett for KS-test

## Skillet mellom bekreftet tilgang og fungerende klient

Den private e-posten fra KS support, datert 14.09.2026, bekrefter opprettet
testorganisasjon, administratoradgang, aktiverte tjenester og et opprettet
SvarInn-mottak. Den bekrefter også at egenutviklet produksjonsintegrasjon er
mulig innenfor gjeldende avtale, og at KS ønsker registrering i
leverandør-/systemkatalogen før produksjon. Dette er ikke dokumentasjon på
at avsenderkonto, Maskinporten, service-passord eller kryptering er ferdig
konfigurert eller testet.

Kontonavn, organisasjonsnummer, TestID, personopplysninger og selve e-posten
skal ikke versjoneres. Bruk originalen lokalt ved konfigurering. Denne siden
inneholder bare fremgangsmåte og ikke-følsomme statusavklaringer.

## SvarUt

Bruk testforvaltningen oppgitt av KS:
`https://forvaltning.fiks.test.ks.no/`.
Opprett eller kontroller avsenderkontoen. Under autentisering/integrasjoner
opprettes eller velges en Fiks-integrasjon, og den gis nødvendig tilgang til
kontoen. Registrer konto-ID, integrasjons-ID og Maskinporten klient-ID i
appens lokale Oppsett, ikke i kode eller Markdown.

Integrasjonspassord, nøkkelmateriale og eventuelle nøkkelpassord må lagres
sikkert lokalt. a1 samler **ikke** inn disse. Sikret hemmelighetshåndtering
må på plass før første autentiserte kall.

Kilder: [SvarUt-konfigurasjon](https://ksdigital.no/tjenestene/svarut-tjenesten/svarut-konfigurasjon/),
[Fiks-integrasjoner](https://developers.fiks.ks.no/felles/integrasjoner/index.html).
Sistnevnte skiller kontoorganisasjonen fra organisasjonen i Maskinporten-tokenet.
Avklar riktig autorisert organisasjon; ikke anta at et Tenor-organisasjonsnummer
automatisk er identiteten i virksomhetssertifikatet/tokenet.

## SvarInn

Bruk det allerede opprettede mottaket i testforvaltningen oppgitt av KS:
`https://svarut.fiks.test.ks.no/mottaker#/`.
Kontroller tilganger, tilknyttet testorganisasjon og eventuell
forsendelsestype. Et visningsnavn på mottaket er ikke automatisk det samme
som API-ets service-brukernavn.

Under Service finner/genererer dere service-legitimasjon og laster opp den
offentlige delen av nøkkelparet i forventet format. Den private delen
beholdes lokalt. a1 kan lagre brukernavn og filreferanser, ikke service-passord.
Ikke endre produksjonsruting under dette testarbeidet.

KS advarer mot å registrere produksjonsorganisasjoner før mottaket er klart,
fordi innkommende forsendelser da kan bli liggende i kø.
Kilde: [SvarInn-konfigurasjon](https://ksdigital.no/tjenestene/svarut-tjenesten/svarinn/konfigurasjon-av-svarinn/).

## Før rundtur-testen

Bruk Tenor-data, ikke reelle personopplysninger eller dokumenter. Kontroller
at testorganisasjonen rutes til riktig testmottak. Dokumenter lokal tilgang,
men del bare redigert testresultat uten TestID, kontoer, passord eller dokumentinnhold.
Kilde: [KS testmiljø](https://developers.fiks.ks.no/tjenester/svarut/testmiljo/index.html).

Ekte rundtur er et senere trinn: send, lagre forsendelses-ID, følg status,
hent samme forsendelse, dekrypter, sammenlign innhold/hash, lagre varig og
kvitter. Denne prosedyren kan ikke kjøres med a1.

Åpne spørsmål til `#fiks-integrasjon`: riktig Maskinporten-nøkkeloppsett,
krypteringsformat/referansetest for SvarInn, eventuelle nye API-baseadresser,
og hvordan egen klient registreres i leverandør-/systemkatalogen.
