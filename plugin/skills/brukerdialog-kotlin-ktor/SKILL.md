---
name: brukerdialog-kotlin-ktor
description: Preset for oppgaver som legger til eller endrer Kotlin/Ktor-backend-kode (ruter, repository, Rapids & Rivers)
license: MIT
compatibility: Kotlin/Ktor på Nais, Kotliquery/Flyway, Rapids & Rivers
metadata:
  domain: backend
  tags: kotlin ktor rapids-rivers kotliquery planlegger-preset
---

# Kotlin+Ktor preset

Brukes av `planlegger` når en oppgave legger til eller endrer Kotlin/Ktor-backend-kode.
Basert på de etablerte skillsene `ktor-scaffold` (prosjektstruktur) og `kotlin-app-config`
(sealed config) — dette presetet er den korte, `planlegger`-spesifikke versjonen som
avgjør sti/planreview og tvinger inn brief-felt for `koder`.

## Trigger

Oppgaven legger til eller endrer:
- Ktor-ruter, `River`/`PacketListener` (Rapids & Rivers), eller repository-kode i Kotlin
- oppsett av `ApplicationBuilder`, sealed konfigurasjon, eller DI-oppsett (Koin/manuell)

Ikke overlapp med `brukerdialog-db-migrasjon` (skjemaendringer har eget preset) eller
`brukerdialog-api-kafka` (endepunkt+event i samme oppgave har eget preset) — bruk dette
presetet når oppgaven er generell Kotlin/Ktor-kode uten at de mer spesifikke triggerne
slår inn.

## Default sti

- Ny rute/repository-metode som følger etablert mønster i samme fil/mappe:
  `Sti=enkel`, `Krever planreview=nei`.
- Ny service/modul, endring i transaksjonsstrategi, eller endring i DI-oppsett:
  `Sti=komplisert`, `Krever planreview=ja`.

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **Ruter som extension functions**: `fun Application.xRoutes()`, ikke frittstående
  funksjoner eller klasser med arv.
- **DI-tilnærming**: konstruktørinjeksjon uten rammeverk for enkle tilfeller (pass
  avhengigheter eksplisitt inn); bruk Koin **kun** hvis prosjektet allerede bruker det
  for wiring av mange services/repositories. Ikke innfør Koin i et prosjekt som ikke
  allerede har det, uten eksplisitt begrunnelse i brief.
- **Database-tilgang**: Kotliquery + HikariCP, ikke JPA/Hibernate. Angi hvilket
  transaksjonsmønster som brukes hvis flere repository-kall må være atomiske (enkelt
  `session.transaction`-block, eksplisitt `DbTransaction`-parameter, eller
  `ThreadLocal`-basert — se `kotlin-ktor`-instruksjonene for når hvert passer). Advarsel:
  `ThreadLocal` propagerer ikke til nye coroutines — ingen `launch`/`async` i en
  transaksjonsblokk.
- **Rapids & Rivers** (hvis event-drevet): `precondition`/`validate` i `River`-oppsettet,
  og om et nytt event skal publiseres etter behandling.
- **Feilhåndtering**: sealed `DomainError`/`Either` kun hvis prosjektet allerede bruker
  Arrow-kt — ikke innfør det i et prosjekt som ikke allerede har det.

## Sjekkliste for koder

- [ ] Ruter er extension functions på `Application`, ikke egne klasser med arv.
- [ ] Ingen ny DI-rammeverk (Koin) innført uten at det allerede var i bruk i prosjektet.
- [ ] Databasetilgang bruker Kotliquery, ikke JPA/Hibernate.
- [ ] Transaksjonsblokker inneholder ingen `launch`/`async`/andre coroutine-buildere.
- [ ] `/isalive`, `/isready`, `/metrics` er ikke fjernet eller brutt av ruteendringen.
- [ ] Testnavn følger norsk backtick-konvensjon (`` `skal returnere feil når ...` ``) og
      bruker Kotest-matchers.

## Ikke gjør

- Ikke innfør arv, interfaces eller DI-rammeverk uten en god, eksplisitt begrunnelse.
- Ikke bruk `ThreadLocal`-transaksjoner sammen med coroutine-builders i samme blokk.
- Ikke sett `/isready` til å returnere feil ved SIGTERM eller legg til egen
  preStop-hook — Nais håndterer graceful shutdown allerede.
- Ikke innfør Arrow-kt eller andre nye funksjonelle rammeverk i et prosjekt som ikke
  allerede bruker dem.
