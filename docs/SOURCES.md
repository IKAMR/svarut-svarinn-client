# Kilder og repositoryrelasjoner

Kontrollert 23.10.2026. Offentlig dokumentasjon beskriver API-kontrakten,
ikke status for den lokale kontoen. Kontospesifikke verdier beholdes utenfor Git.

## KS Digital

| Kilde | Brukt til |
| --- | --- |
| [SvarUt utvikleroversikt](https://developers.fiks.ks.no/tjenester/svarut/) | Oppdatert toppvarsel om SOAP og REST v1 |
| [Konfigurasjon av SvarInn](https://ksdigital.no/tjenestene/svarut-tjenesten/svarinn/konfigurasjon-av-svarinn/) | Mottakersystem, service-tilgang og ruting |
| [Konfigurasjon av SvarUt](https://ksdigital.no/tjenestene/svarut-tjenesten/svarut-konfigurasjon/) | Konto og Fiks-integrasjon; overskriften REST v2 er ikke hele versjonsbildet |
| [API-versjoner](https://developers.fiks.ks.no/tjenester/svarut/api-versjoner/index.html) | Send V3, Status V3, øvrige del-API-er og SvarInn V2 |
| [SvarUt REST](https://developers.fiks.ks.no/tjenester/svarut/rest/index.html) | Tilgang og oppdeling av sendeoperasjoner |
| [SvarInn REST](https://developers.fiks.ks.no/tjenester/svarut/svarinn-rest/index.html) | Basic Auth, kryptering og tilgjengelighet frem til kvittering |
| [Send V3 OpenAPI](https://developers.fiks.ks.no/api/forsendelse-send-api-v3.json) | Testbase, sendestier, multipart |
| [Status V3 OpenAPI](https://developers.fiks.ks.no/api/forsendelse-status-api-v3.json) | Statusoppslag og modell |
| [SvarInn V2 OpenAPI](https://developers.fiks.ks.no/api/svarinn-api-v2.json) | Liste/nedlasting/kvittering, SHA-256 |
| [Fiks-integrasjoner](https://developers.fiks.ks.no/felles/integrasjoner/index.html) | Maskinporten, ks:fiks, headerne og to mulige nøkkeltyper |
| [Testmiljø](https://developers.fiks.ks.no/tjenester/svarut/testmiljo/index.html) | Tenor-data og testmottak |
| [Avviklingsnyhet 13.01.2026](https://ksdigital.no/2026/01/13/avvikling-av-soap-og-rest-v-1-api-for-svarut/) | Historisk tentativ dato; avviker fra senere toppvarsel |

Se [KS-API.md](KS-API.md) for motstridende frister og forskjellen mellom
portal og API. Dokumentasjonskontroll er ikke verifikasjon av kontotilgang.

## Digdir og kryptografibibliotek

| Kilde | Brukt til |
| --- | --- |
| [Maskinporten JWT grant](https://docs.digdir.no/docs/Maskinporten/maskinporten_protocol_jwtgrant) | RS256, kid/x5c, issuer/audience, scope, iat/exp/jti |
| [Maskinporten token-endepunkt](https://docs.digdir.no/docs/Maskinporten/maskinporten_protocol_token) | Form-body og tokensvar |
| [API-konsumentguide](https://docs.digdir.no/docs/Maskinporten/maskinporten_guide_apikonsument) | Registrering og nøkkelvalg |
| [cryptography: serialisering](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/serialization/) | PEM, RSA og PKCS#12 med bibliotekets nøkkelhåndtering |

## Privat underlag, ikke versjonert

KS support sin e-post datert 14.09.2026 er lest fra brukerens vedlagte PDF.
Den bekrefter opprettet testmiljø/mottak og avtalemulighet for egen klient,
med ønske om systemregistrering før produksjon. Skjermbildet i e-posten
viser Tenor-søk med daglig-leder-rolle; det er ikke API-legitimasjon.

Originalen, kopier, personnavn, e-postadresser, TestID, testorganisasjon og
mottakernavn er bevisst ikke tatt inn i repository-pakken.

## Relaterte repositoryer

| Repository | Rolle |
| --- | --- |
| [svarut-svarinn-client](https://github.com/IKAMR/svarut-svarinn-client) | Klientens kildekode og dokumentasjon |
| [incremental-ai-development-method](https://github.com/IKAMR/incremental-ai-development-method) | Samarbeidsmetode og ZIP-/Git-kontrakt |
| [AI-WORKFLOW](https://github.com/IKAMR/incremental-ai-development-method/blob/main/AI-WORKFLOW.md) | Arbeidskontrakt for AI-assistert utvikling |
| [data-workflow-manager](https://github.com/IKAMR/data-workflow-manager) | Referanse for prinsipper, ikke kjøreavhengighet |
| [DWM DEVELOPMENT](https://github.com/IKAMR/data-workflow-manager/blob/main/docs/DEVELOPMENT.md) | GUI, persistens, install/test/start og dokumentansvar |
| [DWM ARCHITECTURE](https://github.com/IKAMR/data-workflow-manager/blob/main/docs/ARCHITECTURE.md) | Felles kjernelag og tynne grensesnitt |

Prosjektets egne valg beskrives i [DEVELOPMENT.md](DEVELOPMENT.md) og
[ARCHITECTURE.md](ARCHITECTURE.md).
