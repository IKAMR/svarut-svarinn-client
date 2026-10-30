# KS: kontrollert API-grunnlag

Kontrolldato: **23.10.2026**. Dette er dokumentasjonskontroll, ikke en test av
IKAMRs tilganger. Kilderegister: [SOURCES.md](SOURCES.md).

## Versjonsvalg

| Funksjon | Versjon hos KS | Prosjektets retning |
| --- | --- | --- |
| SvarUt Send | V3 stabil; V2 erstattet | Send V3 |
| Forsendelsesstatus | V3 stabil; V2 erstattet | Status V3 |
| Hendelser, ekstern referanse, metadata | Separate V2-API-er | Bruk ved faktisk behov |
| SvarInn | V2 stabil; V1 deprecated | SvarInn V2 |

Kilde: [KS versjonsoversikt](https://developers.fiks.ks.no/tjenester/svarut/api-versjoner/index.html).
Det er altså ikke ett felles versjonsnummer for hele løsningen.
SvarUt-konfigurasjonsveilederens overskrift «REST v2» betyr ikke at vi skal
velge det erstattede Send V2-endepunktet.

## Avviklingsfrister og motstridende tekst

Toppvarselet på KS' utviklersider oppgir **SOAP: 01.01.2027** og
**REST v1: 31.07.2027**. Samtidig har en rad i versjonstabellen fortsatt
31.12.2026 for REST v1. Nyheten datert 13.01.2026 omtaler 31.12.2026 som
tentativ felles frist og V3 som kommende. Den private e-postens signatur
bruker også den tentative fristen.

Dette er et dokumentert kildeavvik. Bekreft gjeldende frist for et konkret
eldre API med KS. Datoene beskriver KS sine API-er, ikke klientens
leveringsplan. Klientens planlagte API-grunnlag er Send V3, Status V3 og
SvarInn V2; eldre API-varianter inngår ikke.

Kilder: [utviklersiden](https://developers.fiks.ks.no/tjenester/svarut/),
[versjonstabellen](https://developers.fiks.ks.no/tjenester/svarut/api-versjoner/index.html),
[tidlig avviklingsvarsel](https://ksdigital.no/2026/01/13/avvikling-av-soap-og-rest-v-1-api-for-svarut/).


## Implementerte testoperasjoner

Testbase: `https://test.svarut.ks.no/api`.

| Operasjon | Metode og sti under basen | Status |
| --- | --- | --- |
| Send til organisasjon | `POST /v3/kontoer/{kontoId}/forsendelser/organisasjon` | Implementert for én PDF / kun digital levering |
| Hent status | `POST /v3/kontoer/{kontoId}/forsendelser/status/sok` | Implementert for én ID per oppslag |
| List SvarInn-forsendelser | `GET /svarinn/v2/forsendelser` | Implementert, inntil 200 metadataobjekter |
| Send til person | `POST /v3/kontoer/{kontoId}/forsendelser/person` | Ikke implementert |
| Last ned filer | `GET /svarinn/v2/forsendelser/{forsendelseId}` | Ikke implementert; transporten sperrer |
| Kvitter mottak | `PATCH /svarinn/v2/forsendelser/{forsendelseId}/status` | Ikke implementert; transporten sperrer |

Implementert betyr at kode og simulerte kontrakttester finnes. Faktisk
konto-/tjenestetilgang og levering skal fortsatt verifiseres i KS-test.
Forvaltningsportalene er ikke API-base; ikke legg `/api` til portaladressen.

**Send:** multipart med JSON-delen `forsendelse` først, deretter dokumentet.
Metadata bruker `mottaker.digitalId` (organisasjonsnummer), `mottaker.navn`,
`tittel`, `dokumenter` med filnavn/MIME-type, `kunDigitalLevering: true` og
`avgivendeSystem`. `eksternReferanse` og `korrelasjonsid` settes til en lokal
UUID; valgfri `forsendelsestype` styrer ruting. Dokumentets multipart-filnavn
skal stemme med metadata. HTTP 200 med `id` betyr akseptert, ikke levert.

**Status:** JSON-body er `{"id":["<forsendelses-ID>"]}`. Svaret leses fra
`statuser` med `id`, `status` og `sisteStatusEndring`. Nye ekstra felt ignoreres.

**SvarInn:** Basic Auth med mottakersystemets service-legitimasjon. Tom liste
er et gyldig, vellykket svar. Visningen leser `id`, `tittel`, `dato`, `filer`
og `eksternRef`. Den følger ingen nedlastingslenke og kvitterer ingenting.

Kilder: [Send V3](https://developers.fiks.ks.no/api/forsendelse-send-api-v3.json),
[Status V3](https://developers.fiks.ks.no/api/forsendelse-status-api-v3.json),
[SvarInn V2](https://developers.fiks.ks.no/api/svarinn-api-v2.json).

## Maskinporten og Fiks

SvarUt bruker `Authorization: Bearer <token>`, `IntegrasjonId` og
`IntegrasjonPassord`. Scope er `ks:fiks`; integrasjonen må autoriseres til
kontoen. Kilde: [Fiks-integrasjoner](https://developers.fiks.ks.no/felles/integrasjoner/).

Token hentes med `POST https://test.maskinporten.no/token` og formfeltene
`grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer` og `assertion`.
Klienten signerer RS256 med privat RSA-nøkkel fra `cryptography`. Headeren
bruker enten registrert `kid` eller matchende `x5c`-sertifikatkjede.
JWT-claims: `aud=https://test.maskinporten.no/` (ikke token-URL), `iss` lik
klient-ID, `scope=ks:fiks`, `iat`, `exp=iat+120` og ny `jti` per grant.

Token behandles som en ugjennomsiktig verdi og caches bare i minnet, med
utløp og kobling til oppsett/nøkkel. **Test Maskinporten** tvinger ny henting.
Testknappen bekrefter ikke kontotilgang i Fiks. Første SvarUt-kall tester
den og kan fortsatt avvises. Det er ingen automatisk gjentakelse av sending.
Kilder: [JWT grant](https://docs.digdir.no/docs/Maskinporten/maskinporten_protocol_jwtgrant),
[token-endepunkt](https://docs.digdir.no/docs/Maskinporten/maskinporten_protocol_token).

## Senere dokumentmottak

SvarInn bruker eget mottaksnøkkelpar for krypterte filer. Listekallet trenger
ikke privatnøkkelen. SHA-256 oppgis per dokument, men krypteringsinnpakning og
Python-dekryptering skal verifiseres før de implementeres. Ikke anta at RSA-
nøkkelstørrelsen alene beskriver filformatet. Kilde:
[SvarInn REST](https://developers.fiks.ks.no/tjenester/svarut/svarinn-rest/index.html).
