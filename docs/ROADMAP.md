# Planlagt funksjonalitet

Klienten har testkode for Maskinporten, SvarInn-liste, én PDF til
organisasjon og status. Første praktiske verifikasjon er reelle kall mot KS-test
med lokale kontotilganger. Beståtte simulerte tester er ikke et leveringsbevis.
Se [TEST-SETUP.md](TEST-SETUP.md) og [README](../README.md).

| Område | Gjenstående innhold | Forventet resultat |
| --- | --- | --- |
| Full SvarInn-rundtur | Nedlasting, dekryptering, SHA-256, varig mottakslagring og eksplisitt kvittering | Identiske dokumenter; kvittering først etter kontrollert lagring |
| SvarUt-utvidelser | Personmottaker, flere dokumenter og nødvendige leveringsvalg | Verifisert funksjonsdekning utover én digital organisasjonssending |
| Avstemming/gjenopptak | Kontrollert avklaring av ukjent sendeutfall og komplette mottakstransaksjoner | Ingen tap/dobbelbehandling i avtalte feiltester |
| Terminalserver og tilgang | Verifisert Windows-identitet, AD-grupper, administrert oppsett og tjenesteautorisasjon | Gruppetilgang uten parallelt manuelt brukerregister |
| Sonedeling | Samme kodebase med administrert sonepolicy, separate data/tilganger | SvarInn skjules og sperres i intranett; ikke bare tomt oppsett |
| Hemmeligheter og drift | Tjenesteeid hemmelighetslager, nøkkelbytte, backup/gjenoppretting og overvåking | Forsvarlig flerbruker-/produksjonsdrift |

AD og tjenestedrift er krav før flerbruker/produksjon, men ikke sperrer foran
en avgrenset enkeltbrukertest med ufølsomme data i KS sitt testmiljø.
Krypteringsformatet skal verifiseres mot referanseimplementasjon og faktiske
testdata, ikke utledes av antakelser. Produksjonskrav: [GO-NOGO.md](GO-NOGO.md).

## Senere: adresseregister

Adresseregisteret skal være atskilt fra AD-tilgang, med kontrollerte
redigeringsrettigheter og skille mellom virksomheter/personer. Det skal
ikke deles automatisk mellom sonene. Faktiske mottakeropplysninger lagres
utenfor repoet. Registeret er ikke implementert.

## Avgrensning

Fiks melding, sak-/arkivintegrasjoner, automatisk overføring mellom soner,
dokumentsignering og NHN inngår ikke i grunnomfanget. Valgt AD-prinsipp er
dokumentert; konkret tjenestetransport og fysisk plassering er ikke låst.
