# Lokal konfigurasjon

## Plassering og levetid

Standard på Windows: `%LOCALAPPDATA%/SvarUtSvarInnClient`.
Programmet oppretter mappen og tomt oppsett ved første start, og gjenbruker
samme fil ved senere kjøring. Oppgradering av kildekode skal ikke slette den.

```text
SvarUtSvarInnClient/
    setup.json
    ui-state.json
    runtime.lock
    logs/
        activity.jsonl
```

`--data-dir MAPPE` overstyrer miljøvariabelen `SVARUT_SVARINN_HOME`, som
igjen overstyrer standardplasseringen. CLI-relative stier tolkes fra
arbeidsmappen; `start.bat` setter arbeidsmappen til repository-roten.

Valg under repoet godtas bare i `.local/` eller `local-data/`, som er ignorert.
Standard er likevel utenfor repoet. Andre plattformers utviklingsfallback er
`~/.local/share/svarut-svarinn-client`; dette er ikke en erklæring om
produksjonsstøtte for disse plattformene.

## setup.json, skjema 1

| Felt | Innhold |
| --- | --- |
| `schema_version` | Heltallet 1 |
| `environment` | Bare `TEST` |
| `svarut.api_base_url` | Brukerangitt API-base, tom fra start |
| `svarut.account_id` | SvarUt konto-ID |
| `svarut.integration_id` | Fiks integrasjons-ID |
| `svarut.maskinporten_client_id` | Maskinporten klient-ID, ikke TestID |
| `svarut.signing_key_file` | Absolutt sti til lokal nøkkel-/sertifikatfil |
| `svarinn.api_base_url` | Brukerangitt API-base, tom fra start |
| `svarinn.service_username` | Service-brukernavn, ikke portalbruker eller kontonavn |
| `svarinn.private_key_file` | Absolutt sti til privat PEM-nøkkel |
| `svarinn.public_certificate_file` | Absolutt sti til offentlig PEM-sertifikat |

Alle felt i de to tjenestegruppene er strenger og starter tomme. Det leveres
ingen utfylt setupfil eller eksempel med konto-/brukerdata. Offentlige
API-kontrakter, versjonsnumre og testvertens sikkerhetspolicy er tekniske
programregler, ikke kundespesifikk konfigurasjon.

Delvis utfylt oppsett kan lagres; lokal kontroll viser mangler eller ugyldige
verdier. Lagret oppsett er ikke en bekreftelse på at det kan autentisere.
Ikke-tomme URL-er kontrolleres mot den dokumenterte testadressen ved lokal
kontroll. Alle operasjoner er uansett sperret i a1, og miljø `PROD` avvises
ved lesing og lagring. Ikke utvid fremtidig transport uten selvstendig
miljø-/vertskontroll.

Ukjente felt, nye skjemaversjoner, dupliserte JSON-nøkler og ugyldige typer
avvises. En skadet fil nullstilles ikke automatisk. Oppsett som endres manuelt
mens appen kjører, overskrives ikke bevisst; lukk og start appen på nytt.

## Hemmeligheter og vindusdata

Ingen passord, token eller privat nøkkelinnhold inngår i skjemaet.
a1 leser heller ikke innholdet i refererte nøkkelfiler. Sikker lokal
hemmelighetslagring må implementeres før autentisering, ikke skjules i et
vilkårlig ekstra JSON-felt.

`ui-state.json` inneholder bare vindusbredde og -høyde. Filen er ikke
kontokonfigurasjon. `runtime.lock` er en OS-låsfil; ikke slett den mens en
klient bruker datamappen. Nettverksdelt datamappe og parallelle skrivere
utenfor appen er ikke støttet.

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

Dette er planlagte kontrakter, ikke nye felt i `setup.json`, skjema 1.
Ingen AD-kobling, tjenesteaktivering eller flerbrukerautorisasjon er
implementert i dagens klient.
