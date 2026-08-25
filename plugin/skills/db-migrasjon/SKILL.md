---
name: db-migrasjon
description: Preset for oppgaver som endrer databaseskjema via Flyway-migrasjoner
license: MIT
compatibility: Kotlin/Java med Flyway og PostgreSQL
metadata:
  domain: backend
  tags: database flyway migration backfill planlegger-preset
---

# DB+migrasjon preset

Brukes av `planlegger` når en oppgave krever en databaseendring.

## Trigger

Oppgaven nevner kolonne, tabell, migrasjon, backfill eller Flyway.

## Default sti

- `Sti=komplisert`
- `Krever planreview=ja`

Skjemaendringer er default komplisert fordi feil her er vanskelig å rulle tilbake og kan
påvirke andre konsumenter av samme tabell.

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **Migrasjonsrekkefølge**: hvilken `V{n}__beskrivelse.sql`-fil, og hva den gjør steg for steg.
- **Rollback-strategi**: hvordan man reverserer endringen hvis den feiler i prod (Flyway har
  ikke automatisk rollback — beskriv manuell reverseringsplan).
- **Backfill-plan**: hvis eksisterende rader må oppdateres, beskriv batch-strategi (unngå å
  låse hele tabellen i én transaksjon).
- **Kompatibilitet gammel/ny kode**: appen ruller ut gradvis (flere pods), så skjemaet må
  fungere med både gammel og ny kodeversjon i en overgangsperiode (expand/contract-mønster).

## Sjekkliste for koder

- [ ] Migrasjonsfil følger navnekonvensjon `V{version}__{description}.sql`.
- [ ] Nye kolonner er enten nullable eller har en default-verdi (unngår lange table locks).
- [ ] Ingen `DROP COLUMN`/`DROP TABLE` uten at det er eksplisitt godkjent i brief
      (bruk expand/contract: legg til nytt først, fjern gammelt i egen, senere migrasjon).
- [ ] Indekser er vurdert for nye kolonner som brukes i `WHERE`/`JOIN`.
- [ ] Migrasjon er testet mot en realistisk datamengde, ikke bare tom tabell.

## Ikke gjør

- Ikke gjør destruktive endringer (drop/rename) i samme migrasjon som introduserer nytt behov.
- Ikke stol på at migrasjonen kjører før alle pods er oppdatert til ny kode.
- Ikke legg til `NOT NULL`-kolonne uten default på en tabell som allerede har rader.
