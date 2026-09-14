# Udir-radar

En støysvak publiseringsradar for Utdanningsdirektoratets lokale skole- og
barnehagetall. Oppsettet følger Orkland, Skaun, Heim, Rennebu og Rindal.

## Hva den gjør

- kontrollerer Udirs publiseringskalender hver virkedag
- følger nye relevante lenker på Udirs sider for grunnskole, Elevundersøkelsen
  og barnehage
- lager maksimalt én samlet RSS-melding per kjøring
- varsler høyst én gang per statistikkområde og årgang
- oppretter en stille grunnlinje ved første kjøring
- stanser uten å endre tilstanden hvis en kilde er tom eller endret på en måte
  som gjør den uleselig

Radaren varsler om at nye tall er klare og gir originalkildene. Den lager ikke
automatiske rangeringer eller bastante konklusjoner om små skoler. Tallene må
kontrolleres redaksjonelt i Udirs statistikkbank.

## Installering på GitHub

1. Opprett et nytt offentlig repository, for eksempel `udir-radar`.
2. Pakk ut ZIP-filen og last opp **innholdet** i mappen, ikke selve mappen.
3. Pass på at den skjulte mappen `.github` blir med.
4. Åpne fanen **Actions** og aktiver workflows dersom GitHub spør.
5. Velg **Overvåk Udir** og kjør **Run workflow** én gang.
6. Første kjøring er stille. Den skal opprette eller oppdatere
   `state/state.json` og `public/feed.xml`.

## RSS-adresse

Når repositoryet er opprettet, er adressen:

`https://raw.githubusercontent.com/DITT-BRUKERNAVN/udir-radar/main/public/feed.xml`

Bytt `DITT-BRUKERNAVN` med GitHub-brukernavnet ditt. Legg denne adressen inn i
RSS.app eller en vanlig RSS-leser. Du skal ikke lage ekstra filtre i RSS.app.

## Varselmengde

Normalt fire til seks meldinger i året, med et hardt tak på seks tema-varsler
per årgang. Kalenderdato og publisert artikkel slås sammen logisk, slik at de
ikke kan gi to varsler om eksempelvis «Nasjonale prøver 2026». Flere
publiseringer som oppdages i samme kjøring samles dessuten i én RSS-melding.

## Hva redaksjonen bør kontrollere

Ved et varsel, søk etter kommunenummer 5059, 5029, 5055, 5022 og 5061. Se på:

- utvikling fra forrige sammenlignbare år
- forskjell fra Trøndelag og landet
- deltakelse og eventuelle skjulte verdier
- om endringen gjelder hele kommunen eller én skole
- metodeendringer og små elevkull

## Endre kilder og tema

Alt styres i `config.json`. Søkeordene ligger under `sources[].terms`.
Ikke sett `minimum_matches` lavere uten å kontrollere hvorfor en kilde har
mistet treff; sikkerhetsgrensen hindrer at en ombygd nettside lager falske
varsler eller ødelegger tilstanden.

## Tidsplan

Workflowen kjører klokken 07:17 UTC på hverdager, omtrent klokken 08:17 norsk
vintertid og 09:17 norsk sommertid. Det er mer enn ofte nok for disse kildene.

## Kilder

- https://www.udir.no/kalender/Publiseringer/
- https://www.udir.no/tall-og-forskning/statistikk/statistikk-grunnskole/
- https://www.udir.no/tall-og-forskning/brukerundersokelser/elevundersokelsen/resultater/offentlige-resultater-grunnskole/
- https://www.udir.no/tall-og-forskning/statistikk/statistikk-barnehage/
- https://www.udir.no/om-udir/data/api-data-fra-elevundersokelsen/

Data fra Udir er tilgjengelig for viderebruk under Norsk lisens for offentlige
data (NLOD). Oppgi Utdanningsdirektoratet som kilde.
