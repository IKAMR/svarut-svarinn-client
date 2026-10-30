# Utviklingskontrakt

## Autoritativ arbeidsflyt

Prosjektet følger [Incremental AI-Assisted Development Method](https://github.com/IKAMR/incremental-ai-development-method)
og brukerens eksplisitte instruksjoner. Assistenten endrer ikke GitHub,
oppretter ikke Issues/branches og committer eller pusher ikke.

1. Les gjeldende repository og relevante dokumenter.
2. Implementer bare det avtalte incrementet.
3. Lever ZIP med repository-relative stier, nye/endrede filer og tester.
4. Brukeren legger inn filene, kjører `test.bat` og praktisk test.
5. Brukeren godkjenner, committer og pusher.
6. Assistenten kontrollerer pushet commit, filendringer, versjon og dokumentasjon.
7. Nytt increment lages først på brukerens instruksjon.

ZIP-er er transport, ikke Git-historikk. Lever bare nye og endrede filer
med repository-relative stier. Første delta i et nytt increment er relativt
til kontrollert, pushet baseline. Senere fix-delta inneholder bare endringer
siden forrige leveranse, med mindre brukeren ber om en kumulativ pakke.
Ingen `.git`-mappe, runtime-data, private kilder eller nøkler følger med.
Etter godkjent push er den commiten ny baseline.

## Dokumentansvar og leserekkefølge

README og dokumentoversikten beskriver funksjoner, bruk og teknisk innhold.
Detaljer om samarbeids- og leveranseløpet hører hjemme i denne filen, ikke
i produktpresentasjonen. Interne produksjonsmål og prosjektfrister skal ikke
presenteres som funksjonsbeskrivelse eller lovet tilgjengelighet.

Les denne filen, ARCHITECTURE og CODE-MAP før utvikling. Les GUI ved
presentasjonsendringer, CONFIGURATION/SECURITY ved persistens og autentisering,
KS-API/TEST-SETUP ved KS-kall, og TESTING ved endret oppførsel.
GO-NOGO og ROADMAP skal skille beslutningskriterier fra faktisk funksjonalitet.

Før levering: søk etter foreldede statuspåstander i README, docs, hjelpetekster
og tester. `Implementert`, `automatisk testet`, `praktisk verifisert` og
`planlagt` er forskjellige tilstander.

## Prinsipper fra Data Workflow Manager

Gjenbruk arbeidsformen, ikke dagens GUI-implementasjon: tynn GUI over delte
tjenester, lokal persistens, tydelig aktiv kontekst, responsiv layout,
felles tester og dokumenterte grensesnitt. Ingen DWM-import, kopiert monolitt,
profilmotor eller operasjons-/jobblistemodell bygges inn her.

Brukerens eksplisitte delta-instruksjon gjelder dette repoet. Andre DWM-
spesifikke unntak overføres ikke automatisk.

## Teknisk minimum

Python 3.11+, Tkinter/ttk og cryptography fra requirements.txt. Windows er målplattform,
men supportpåstander krever faktisk lokal verifikasjon. Tester bruker
midlertidige mapper, genererte nøkler og simulerte svar, aldri brukerens oppsett.
Testinngangen sperrer utgående nettverk. Faktiske KS-tester krever brukerens
lokale testoppsett og skal ikke blandes med automatisert evidens.
Ikke legg domenelogikk i `.bat` eller lagring/API-kall i widget-callbacks.

Versjonen eies av `svarut_svarinn_client/__init__.py`. ZIP-navn og rapport
bruker samme utviklingsidentifikator. Versjonsnotater samles
i RELEASES; ikke opprett permanente designfiler per alpha.

## Avgrensning

Ingen sak-/arkivsystemintegrasjon, Fiks melding, Issues-oppsett eller generell
integrasjonsplattform i første løp. Logging av aktiviteter i andre systemer er
utenfor dette repoets nåværende ansvar.
