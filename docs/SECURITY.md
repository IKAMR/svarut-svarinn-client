# Sikkerhet

## Implementert avgrensning

Klienten er en enkeltbruker-testklient med bare eksplisitte brukerutløste kall.
Transporten tillater kun dokumenterte HTTPS-testverter og de fire aktiverte
operasjonene: Maskinporten-token, SvarInn-liste, organisasjonssending og status.
Produksjon, vilkårlige URL-er, redirects, dokumentnedlasting og kvittering er
sperret. TLS-verifikasjon kan ikke slås av. Ingen automatisk retry gjøres.

Svar har størrelses- og tidsgrenser. Rå HTTP-headere, responsmeldinger og unntak
vises/logges ikke; bare faste forklaringer, HTTP-status og tillatte feil-ID-er/
feilkoder. Oversized eller uleselige svar gir feil, ikke antatt suksess.

Kontoer, TestID, private korrespondanser og faktiske mottakerverdier finnes
ikke i repoet. Passord og token finnes bare i appens minne under testøkten.
Maskerte felt er ikke kryptert lagring, og Python-minne har ingen garanti for
sikker nullstilling. Testklienten skal kjøres av en betrodd operatør i en
beskyttet brukerprofil, bare med ufølsomme testdata. Den implementerer ikke
AD-kontroll, flerbrukerisolasjon eller produksjonens tjenesteeide nøkkellager.

## Lokale data og journal

Oppsett lagrer bare nøkkelfilstier. Valgt privatnøkkel leses ved signering,
men kopieres ikke. Journalen lagrer metadata, hash, lokal referanse og
KS-ID/status, ikke PDF-innhold, passord eller token. Aktivitetsloggen lagrer
bare faste hendelser, tid, versjon og miljø. Den er ikke et manipulasjonssikret
revisjonsspor. Journalfeil stopper sending før POST; loggfeil må ikke skjule
et journalført sendeutfall. Ukjent utfall omsendes ikke automatisk.

`.gitignore` hindrer ikke filtilgang og fjerner ikke tidligere publisert
innhold. Ikke bruk `git add -f` på runtime-data. Beskytt profil/datamappe,
nøkkelfiler og ukryptert metadatajournal med Windows-ACL. Disse rettighetene
settes eller verifiseres ikke automatisk av klienten. POSIX-filer opprettes
restriktivt; det erstatter ikke verifisert Windows-beskyttelse.

Ingen private nøkler, servicepassord, integrasjonspassord, token, TestID eller
lokale konto-/mottakerdata skal i repo, ZIP, delte skjermbilder eller rapporter.
Ved utilsiktet publisering: trekk tilbake/roter berørte hemmeligheter og
vurder historikken; sletting av siste filversjon alene er ikke tilstrekkelig.

## Krav før utvidet mottak og produksjon

Dekrypteringsformatet må verifiseres mot KS/referanseimplementasjon og en
faktisk testforsendelse. Senere nedlasting trenger filstørrelsesgrenser,
sikker filnavnhåndtering og vern mot ZIP path traversal/ZIP-bomber. Hashlikhet
alene gjør ikke en fil trygg. Kvittering krever kontrollert varig lagring og
gjenopprettbar tilstand.

Før flerbruker- eller produksjonsbruk må tilgangsbegrensning, tjenesteeid
hemmelighetslager, nøkkelbytte, backup/gjenoppretting, loggintegritet og
sikker oppgradering implementeres/verifiseres. Se [GO-NOGO.md](GO-NOGO.md).

## Flerbruker og sonedeling: krav og anbefalt retning

Dette avsnittet dokumenterer krav og en foreslått løsning, **ikke** sikkerhet
som finnes i testklienten. Dagens app har verken brukerregister, innlogging,
roller, sentral policy eller Windows-tjeneste.

### Identitet og rettigheter

Valgt tilgangsprinsipp er personlige Windows-kontoer og medlemskap i
administratorforvaltede AD-sikkerhetsgrupper. Gruppemedlemskap gir adgang til
appen; det skal ikke opprettes et parallelt manuelt brukerregister eller egne
app-passord. Faktiske gruppenavn, SID-er og kobling til sone/rolle lagres i
beskyttet installasjonsoppsett utenfor repoet. Medlemskap forvaltes i AD,
ikke gjennom en selvregistreringsfunksjon i appen.

Tjenesten skal verifisere Windows-identiteten og relevante gruppemedlemskap
for den autentiserte klientbrukeren. Innsendt brukernavn, miljøvariabelen
USERNAME eller en valgt profil er ikke autentisering. Manglende identitet,
ukjent gruppetilknytning eller feil i autorisasjonsgrunnlaget skal nekte
tilgang, ikke åpne appen. Første administrator etableres av IT-drift gjennom
AD og beskyttet oppsett, aldri ved at første appstarter blir administrator.

Grunnrollene er administrator og bruker, adskilt per sone. Foreslått skille
er at administrator forvalter tillatt oppsett, mens bruker utfører tillatte
forsendelseshandlinger. En administrator som også skal behandle post, må ha
brukerrettighet. Tilgang til konto, forsendelse, dokument, status og logg må
avgrenses separat; appadgang gir ikke automatisk innsyn i all post.
Appadministrator er ikke det samme som Windows-administrator eller
administrator i Fiks forvaltning.

Autorisasjon skal kontrolleres ved handlinger og datatilgang, ikke bare ved
GUI-start. Rutine og teknisk mekanisme for tilbakekalling i aktive
terminalsesjoner må velges og testes; en gruppeendring skal ikke beskrives
som umiddelbart virksom i en allerede åpen sesjon uten verifikasjon.
Personlige innstillinger og identitet i hendelsesloggen er ikke alternative
rettighetskilder.

### Tjenestegrense og lagring

Skjulte faner og deaktiverte knapper er ikke en sikkerhetsgrense. Tjenesten må
håndheve autorisasjon også ved direkte kall utenom GUI-et. KS-passord, private
nøkler og token skal ikke deles ut til GUI-prosessen eller brukernes profiler.
Tjenesten må kjøre med egen, minst mulig privilegert identitet; konkret
hemmelighetslager og Windows-ACL skal velges og verifiseres før administrert flerbruker- eller produksjonsbruk.

Vanlige brukere skal ikke kunne endre installert kode, felles oppsett,
rollekoblinger eller revisjonslogg. Både servicefiler og dokumentlagring skal
beskyttes med eksplisitte rettigheter; en mappe under ProgramData er ikke
beskyttet bare fordi den ligger der. En lokal serveradministrator ligger
utenfor denne avgrensningen og krever egne drifts- og revisjonsrutiner.

Logging skal knytte handling til verifisert bruker, sone, konto, tidspunkt og
forsendelses-ID uten dokumentinnhold eller hemmeligheter. Oppsettsendringer,
endringer i rollekoblinger, tilgangsavslag og mottakskvittering skal være
sporbare. Medlemskapsendringer dokumenteres gjennom AD-forvaltningens rutiner.
Personlige vindusinnstillinger kan fortsatt lagres per bruker, men må aldri
kunne overstyre sikkerhetspolicy eller gi rett til nye kontoer.

### Intranett og sikret sone

Anbefalingen er separate tjenesteinstanser, Fiks-integrasjoner, KS-nøkler og
SvarUt-avsenderkontoer per sone. Tilgangene hos KS skal være minst mulige.
To integrasjoner mot samme konto skal ikke antas å gi dataseparasjon;
avgrensning av status, metadata og dokumenter må testes eksplisitt.

Intranettinstansen skal bare tillate sending og nødvendig statusoppfølging
for den sonens egne forsendelser. Den skal ikke ha SvarInn-passord eller privat
mottaksnøkkel, og tjenesten skal nekte mottaksoperasjoner. Å skjule SvarInn-fanen
er ikke nok. Personlige oppsettfiler eller kommandolinjevalg skal ikke kunne
oppheve sperren.

Alt inngående mottas, kontrolleres og behandles i sikret sone. Eventuelle svar
på utgående brev fra intranett skal også rutes dit og testes ende til ende.
Appen skal ikke automatisk kopiere inngående dokumenter eller metadata til
intranett. Bare materiale vurdert og godkjent for utførsel følger eksisterende
sluser. Eksterne merkelapper som «ikke sensitiv» skal ikke alene utløse dette.

Sonepolicy må omfatte dokumenter, metadata, logger, mellomlagring, backup og
adresseregister. IT-drift må også vurdere utklippstavle, omdirigerte disker og
utskrift i terminalsesjoner, slik at disse ikke omgår godkjente sluser.
Appen kan ikke garantere at et vedlegg er ufølsomt bare fordi brukeren har
krysset av for det. Tillatt innhold og kontrollansvar må fastsettes lokalt.

### Kildegrunnlag for anbefalingen

Kontrollert 23.10.2026. Dette er prosjektets foreslåtte design, ikke en
påstand om at KS foreskriver denne terminalserverarkitekturen.

- [Microsoft: Windows access tokens og SID](https://learn.microsoft.com/en-us/windows/win32/secauthz/access-tokens)
- [Microsoft: tilgangskontroll med ACL](https://learn.microsoft.com/en-us/windows/win32/secauthz/access-control-lists)
- [Microsoft: tilgangskontroll for named pipes](https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights)
- [KS: integrasjoner og kontotilganger](https://developers.fiks.ks.no/felles/integrasjoner/)
- [KS: SvarInn-autentisering, henting og kryptering](https://developers.fiks.ks.no/tjenester/svarut/svarinn-rest/index.html)
