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

ZIP-er er transport, ikke Git-historikk. Innen samme increment er eventuelle
oppdaterte leveranser kumulative fra den avtalte baselinen etter den delte
metoden, med mindre brukeren uttrykkelig ber om bare et fix-delta.
Etter godkjent push er den commiten ny baseline. Ingen `.git`-mappe, runtime-data,
private kilder eller nøkler skal med i leveransen.

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

Den delte metodens leveranseregel gjelder her; DWM har prosjektspesifikke
unntak som ikke automatisk overføres til dette repoet.

## Teknisk minimum

Python 3.11+, standardbibliotek og Tkinter/ttk i a1. Windows er målplattform,
men supportpåstander krever faktisk lokal verifikasjon. Tester bruker
midlertidige mapper og syntetiske verdier, aldri brukerens oppsett.
Ikke legg domenelogikk i `.bat` eller lagring/API-kall i widget-callbacks.

Versjonen eies av `svarut_svarinn_client/__init__.py`. ZIP-navn og rapport
bruker samme utviklingsidentifikator, først `v0.1.0-a1`. Versjonsnotater samles
i RELEASES; ikke opprett permanente designfiler per alpha.

## Avgrensning

Ingen sak-/arkivsystemintegrasjon, Fiks melding, Issues-oppsett eller generell
integrasjonsplattform i første løp. Logging av aktiviteter i andre systemer er
utenfor dette repoets nåværende ansvar.
