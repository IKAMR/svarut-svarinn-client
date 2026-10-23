# Planlagt funksjonalitet

Dette dokumentet beskriver funksjoner som ikke er implementert i a1.
Gjeldende funksjoner og begrensninger er oppsummert i [README](../README.md).

| Område | Planlagt innhold | Forventet resultat |
| --- | --- | --- |
| Terminalserver og brukertilgang | Personlig Windows-identitet, AD-sikkerhetsgrupper per sone/rolle, administratorstyrt oppsett og autorisasjon utenfor GUI | Gruppemedlemskap gir adgang; ikke et parallelt manuelt brukerregister |
| Sonedeling | Samme kodebase med administrert sonepolicy; utgående i intranett, sending og mottak i sikret sone; separate data og tilganger | SvarInn skjules og sperres i intranett; manglende oppsett er ikke det samme som deaktivert funksjon |
| Autentisering | Tjenesteeid hemmelighetslager, Maskinporten for SvarUt og service-tilgang for SvarInn | Verifisert tilgang i KS sitt testmiljø uten deling av hemmeligheter til GUI-brukere |
| SvarUt | Sending til organisasjon og person via Send V3, flere dokumenter og Status V3 | Forsendelses-ID, varig lokal registrering og sporbar status |
| SvarInn | Liste, nedlasting, dekryptering, SHA-256-kontroll og varig lokal lagring | Komplette dokumenter og metadata med kontrollert integritet |
| Kvittering og gjenopptak | Kvittering etter verifisert lagring, avstemming, restart og håndtering av ukjent sendeutfall | Ingen tap eller dobbeltbehandling i avtalte feiltester |
| Sikkerhet og drift | Tilgangsbeskyttelse, nøkkelbytte, backup/gjenoppretting og overvåking | Dokumentert sikker og gjenopprettbar databehandling |

Krav til verifikasjon beskrives i [GO-NOGO.md](GO-NOGO.md).
Krypteringsformat og dekryptering skal verifiseres mot kompatible
referanseimplementasjoner eller testdata, ikke utledes fra antakelser.

## Senere: adresseregister

Et adresseregister skal vurderes etter grunnleggende brukertilgang, sending
og mottak. Det bør være atskilt fra AD-basert brukertilgang, ha kontrollerte
redigeringsrettigheter og kunne skille virksomheter og personer. Felles
adresseregister betyr ikke automatisk deling mellom sonene. Faktiske
mottakeropplysninger lagres utenfor repoet. Ingen registerfunksjon er
implementert.

## Avgrensning

Fiks melding, eksterne sak-/arkivintegrasjoner, automatisk overføring mellom
soner, signering og NHN er ikke del av det planlagte grunnomfanget.
Terminalserver og sonedeling er nye krav; komponentdelingen i ARCHITECTURE
er foreslått, ikke implementert eller praktisk verifisert.
