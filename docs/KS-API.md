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

## Endepunkter som skal implementeres senere

OpenAPI-spesifikasjonene oppgir testbasen:

```text
https://test.svarut.ks.no/api
```

| Operasjon | Metode og sti under basen |
| --- | --- |
| Send til person | `POST /v3/kontoer/{kontoId}/forsendelser/person` |
| Send til organisasjon | `POST /v3/kontoer/{kontoId}/forsendelser/organisasjon` |
| Hent statuser | `POST /v3/kontoer/{kontoId}/forsendelser/status/sok` |
| List nye SvarInn-forsendelser | `GET /svarinn/v2/forsendelser` |
| Last ned forsendelsesfiler | `GET /svarinn/v2/forsendelser/{forsendelseId}` |
| Oppdater mottaksstatus | `PATCH /svarinn/v2/forsendelser/{forsendelseId}/status` |

Kilder: [Send V3](https://developers.fiks.ks.no/api/forsendelse-send-api-v3.json),
[Status V3](https://developers.fiks.ks.no/api/forsendelse-status-api-v3.json),
[SvarInn V2](https://developers.fiks.ks.no/api/svarinn-api-v2.json).
Send bruker metadata og dokumenter som multipart; dokumentrekkefølge og
filnavn må stemme. SvarInn-listen returnerer opptil 200 forsendelser.
Nedlasting er kryptert; dokumentmetadata angir SHA-256.

Forvaltningsportalene fra oppsettsveiledningen/e-posten er ikke API-base-URL-er.
Ikke utled en ny API-base ved å legge `/api` til portaladressen.
Endepunktene ovenfor er kartlagt, men **ingen av dem kalles i a1**.

## Autentisering og åpne tekniske punkter

SvarUt krever Maskinporten-token og en autorisert Fiks-integrasjon med
`IntegrasjonId` og `IntegrasjonPassord`. Scope er `ks:fiks`.
Ny offentlig integrasjonsdokumentasjon beskriver både virksomhetssertifikat
og egen asymmetrisk nøkkel for Maskinporten. Den private e-posten ba om
virksomhetssertifikat. Velg og verifiser konkret oppsett før implementering;
ikke bland portal-TestID med maskinidentitet.
Kilde: [Fiks-integrasjoner](https://developers.fiks.ks.no/felles/integrasjoner/index.html).

SvarInn V2 er fortsatt dokumentert med Basic Auth/service-passord og eget
krypteringsnøkkelpar. KS-eksemplet lager et offentlig PEM/X.509-sertifikat
og privat RSA-nøkkel. Ikke anta at et vilkårlig rått PEM-public-key-format er
uten videre utbyttbart med sertifikatet som portalen forventer.
Kilde: [SvarInn REST](https://developers.fiks.ks.no/tjenester/svarut/svarinn-rest/index.html).

Eksakt krypteringsinnpakning/algoritme og Python-dekryptering skal avklares
mot referanseimplementasjon eller KS, og verifiseres med en ekte testforsendelse.
Nøkkelstørrelse alene beskriver ikke filformatet. Ingen egen kryptoprotokoll
eller antatt dekrypteringskode er lagt inn i a1.
