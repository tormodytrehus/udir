# Installasjon - ett steg om gangen

## Steg 1: Opprett repository

På GitHub velger du **New repository** og bruker:

- Repository name: `udir-radar`
- Visibility: Public
- Add README: Av
- Add .gitignore: Ingen
- License: Ingen

Klikk **Create repository**.

## Steg 2: Last opp filene

1. Pakk ut ZIP-filen på maskinen.
2. Velg **uploading an existing file** i det tomme repositoryet.
3. Last opp alt innholdet i den utpakkede mappen.
4. Kontroller at `.github/workflows/monitor.yml` også er med. Mappen er skjult
   på mange maskiner.
5. Klikk **Commit changes**.

Hvis GitHub-nettsiden ikke vil laste opp `.github`, velger du **Add file**,
**Create new file**, skriver `.github/workflows/monitor.yml` som filnavn og
limer inn innholdet fra den lokale filen.

## Steg 3: Første kjøring

1. Åpne **Actions**.
2. Velg **Overvåk Udir**.
3. Klikk **Run workflow** og deretter den grønne **Run workflow**-knappen.
4. Vent til kjøringen blir grønn.

Første kjøring lager en stille grunnlinje. Gamle Udir-publiseringer skal ikke
fylle RSS-strømmen.

## Steg 4: Legg inn RSS-adressen

Bruk:

`https://raw.githubusercontent.com/DITT-BRUKERNAVN/udir-radar/main/public/feed.xml`

Bytt ut `DITT-BRUKERNAVN`. RSS.app skal bare abonnere på adressen; ikke legg
inn flere søkeord eller filtre der.

## Hvis kjøringen blir rød

Åpne den røde kjøringen og se på steget **Test og kontroller kilder**. Ikke
slett `state/state.json` eller `public/feed.xml`. Sikkerhetskontrollen er laget
for å bevare siste fungerende tilstand når Udir endrer en side.
