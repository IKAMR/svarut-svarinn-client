# Lokal konfigurasjon

## Plassering og levetid

Standard på Windows er `%LOCALAPPDATA%/SvarUtSvarInnClient`. Mappen og tomt
oppsett opprettes ved første start og gjenbrukes ved senere kjøring.
Oppgradering av kildekode skal ikke slette brukerdata.

```text
SvarUtSvarInnClient/
    setup.json
    ui-state.json
    runtime.lock
    outbox.sqlite3
    logs/
        activity.jsonl
```

`--data-dir MAPPE` overstyrer `SVARUT_SVARINN_HOME`, som overstyrer standarden.
CLI-relative stier tolkes fra arbeidsmappen; `start.bat` bruker repository-roten.
Under repoet tillates bare `.local/` eller `local-data/`, som er ignorert.
Standard er utenfor repoet. Utviklingsfallback på andre plattformer er
`~/.local/share/svarut-svarinn-client`, uten løfte om produksjonsstøtte.

## setup.json, skjema 2

| Felt | Innhold |
| --- | --- |
| `schema_version` | Heltallet 2; skjema 1 kan fortsatt leses |
| `environment` | Bare `TEST` |
| `svarut.api_base_url` | Dokumentert SvarUt testbase |
| `svarut.account_id` | SvarUt konto-ID (UUID) |
| `svarut.integration_id` | Fiks integrasjons-ID (UUID) |
| `svarut.maskinporten_client_id` | Maskinporten klient-ID, ikke TestID |
| `svarut.maskinporten_base_url` | Maskinporten testbase/issuer |
| `svarut.maskinporten_key_id` | Registrert `kid`; tom ved sertifikatkjede via `x5c` |
| `svarut.signing_key_file` | Absolutt sti til privat RSA-nøkkel i PEM/P12/PFX/JWK |
| `svarut.signing_certificate_file` | Valgfri PEM/DER-sertifikatfil/-kjede; ikke nødvendig med `kid` eller sertifikater i P12/PFX |
| `svarinn.api_base_url` | Dokumentert SvarInn testbase |
| `svarinn.service_username` | Service-brukernavn, ikke portalbruker/mottakernavn |
| `svarinn.private_key_file` | Beholdt referanse for senere dekryptering; ikke nødvendig for listen |
| `svarinn.public_certificate_file` | Beholdt referanse for senere mottaksoppsett; ikke lest ved listing |

Alle tjenestefeltene er strenger og starter tomme. Knappen **Fyll tomme
testadresser** fyller bare offentlige URL-er, aldri konto- eller brukerdata,
og erstatter ikke utfylte verdier. Offentlige protokollregler og tillatte
testverter er programregler, ikke kundespesifikk konfigurasjon.

Skjema 1 utvides med tre tomme Maskinporten-felt i minnet. Originalfilen
endres ikke ved lesing eller start. Neste eksplisitte **Lagre oppsett** skriver
skjema 2 og beholder alle eksisterende kontofelt og nøkkelreferanser.

Delvis oppsett kan lagres; lokal kontroll viser mangler/formatfeil uten
nettverk. API-handlinger validerer sitt eget nødvendige oppsett. SvarInn-listing
trenger ikke utfylt SvarUt eller mottaksnøkkel. Produksjon avvises både i
oppsettskjema og transport. Ukjente felt/versjoner, dupliserte JSON-nøkler
og ugyldige typer avvises; en skadet fil nullstilles aldri automatisk.

## Hemmeligheter, nøkkelfiler og økt

**Fiks-integrasjonspassord**, **nøkkel-/sertifikatpassord** og **SvarInn
servicepassord** er separate, maskerte øktfelt, ikke JSON-felt. De beholdes
bare i appens minne og må fylles inn på nytt etter omstart. **Tøm passord og
token** tømmer feltene og tokencachen; handlingen sperres under aktive kall.
Python-minne er ikke garantert sikkert nullstilt. Dette er ikke et varig
hemmelighetslager for terminalserverdrift.

Ved SvarUt-autentisering leses den valgte privatnøkkelen i minnet for RS256-
signering. RSA må være minst 2048 bit. Bruk enten registrert `kid` med
matchende nøkkel eller et matchende test-virksomhetssertifikat med nødvendig
kjede for `x5c`. PEM-nøkler, P12/PFX-pakker og enkeltstående private RSA-JWK-er
støttes; JWK-sett/EC-nøkler inngår ikke. KS/Maskinporten må godta den faktiske
registreringen/sertifikatkjeden. Ingen privatnøkkel kopieres eller lagres av appen.

## Journal og vindusdata

`outbox.sqlite3` lagrer sendehistorikk og siste hentede status, inkludert
mottaker, tittel og filnavn. Dette er ukrypterte metadata som skal beskyttes
lokalt. Dokumentbytes, passord og token lagres ikke. En appoppgradering eller
vanlig lukking sletter ikke journalen. Ikke slett den for å omgå en
uavklart sending. Den lokale duplikatsperren er beskrevet i [ARCHITECTURE.md](ARCHITECTURE.md).

`ui-state.json` lagrer bare vindusstørrelse. `runtime.lock` er OS-låsfilen;
ikke slett den under kjøring. Nettverksdelt datamappe og parallelle skrivere
utenfor appen er ikke støttet. Feil i aktivitetsloggen er adskilt fra den
obligatoriske journalføringen av en sending.

## Planlagt skille ved administrert flerbrukerdrift

Dagens `setup.json` er et lokalt enkeltbrukeroppsett. Å kopiere det til en
felles mappe gir ikke administrasjon, AD-autorisasjon eller tilgangskontroll.
Det er ingen automatisk overgang til terminalservermodus i dette incrementet.

Foreslått retning er atskilte ansvarsområder:

| Område | Forvaltning |
| --- | --- |
| Felles tjenesteoppsett og sonepolicy | Beskyttet lokalt oppsett utenfor repo; bare autorisert administrasjon via tjenesten |
| Brukertilgang | AD forvalter medlemskap; beskyttet installasjonsoppsett kobler gruppenes SID-er til sone og rolle, uten parallelt manuelt brukerregister |
| Hemmeligheter og forsendelsesdata | Tjenesteeid, tilgangsbeskyttet lagring; ikke felles, fritt redigerbar bruker-JSON |
| Personlige GUI-innstillinger | Egen Windows-profil; bare visning og preferanser, ingen rettighetsstyring |

Konkrete stier, grupper, brukere, kontoverdier og nøkler skal fortsatt ikke
hardkodes eller inkluderes i repoet. Appen/tjenesten skal opprette og gjenbruke
lokalt oppsett gjennom kontrollert etablering. Eksisterende data skal ikke
overskrives eller migreres stille. Se [SECURITY.md](SECURITY.md).

Planlagt sonepolicy skal skille mellom en tjeneste som er deaktivert for
installasjonen og en tillatt tjeneste som mangler oppsett. I intranett skal
SvarInn være deaktivert og sperret. I sikret sone skal ufullstendig
SvarInn-oppsett kunne vises til administrator som manglende konfigurasjon.
IT-drift fastsetter sonens tillatte funksjoner; vanlige brukere og
personlige oppsettfiler skal ikke kunne utvide disse.

Dette er planlagte kontrakter, ikke nye felt i `setup.json`, skjema 2.
Ingen AD-kobling, tjenesteaktivering eller flerbrukerautorisasjon er
implementert i dagens klient.
