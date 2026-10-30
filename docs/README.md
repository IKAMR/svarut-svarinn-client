# Dokumentoversikt

Dokumentasjon av klientens funksjoner, bruk, oppsett og tekniske oppbygning.
Implementert og planlagt funksjonalitet er beskrevet hver for seg.
Kontoinformasjon og privat korrespondanse lagres lokalt, ikke i Git.

## Bruk og oppsett

| Dokument | Innhold |
| --- | --- |
| [GUI.md](GUI.md) | Faner, navigasjon, lagring og synlig status |
| [CONFIGURATION.md](CONFIGURATION.md) | Lokalt JSON-oppsett og datamappe |
| [TEST-SETUP.md](TEST-SETUP.md) | Oppsett hos KS og registrering av lokale tilkoblingsdata |
| [KS-API.md](KS-API.md) | API-versjoner, endepunkter, autentisering og kildeavvik |
| [SECURITY.md](SECURITY.md) | Lokal databeskyttelse og sikkerhetskrav |

## Funksjonalitet og kvalitet

| Dokument | Innhold |
| --- | --- |
| [ROADMAP.md](ROADMAP.md) | Planlagt funksjonalitet og avgrensninger |
| [GO-NOGO.md](GO-NOGO.md) | Krav til funksjon, sikkerhet og drift før produksjonsbruk |
| [TESTING.md](TESTING.md) | Automatiserte tester, praktisk test og CLI-kontroll |
| [test-results/v0.1.0-a2.md](test-results/v0.1.0-a2.md) | Automatisert testresultat for gjeldende kode |
| [manual-test-results/README.md](manual-test-results/README.md) | Dokumentasjon av praktiske tester |
| [RELEASES.md](RELEASES.md) | Funksjonsendringer og versjonsstatus |

## Teknisk oppbygning og utvikling

| Dokument | Innhold |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Grensene mellom GUI, kjernelogikk og KS-klient |
| [CODE-MAP.md](CODE-MAP.md) | Kodefiler og deres ansvar |
| [SOURCES.md](SOURCES.md) | Offentlige kilder og relaterte repositoryer |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Arbeidsmetode, Git/ZIP, leserekkefølge og versjonering |
| [METHOD-OBSERVATIONS.md](METHOD-OBSERVATIONS.md) | Erfaringer med utviklingsmetoden |

Før kodeendringer: les [utviklingskontrakten](DEVELOPMENT.md) og
[kodekartet](CODE-MAP.md), deretter dokumentene for det aktuelle temaet.
