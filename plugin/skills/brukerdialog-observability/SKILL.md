---
name: brukerdialog-observability
description: Preset for oppgaver som legger til eller endrer metrikker, tracing eller health-endepunkter
license: MIT
compatibility: Nais-applikasjoner med Prometheus/Micrometer og OpenTelemetry
metadata:
  domain: observability
  tags: prometheus opentelemetry health metrics logging planlegger-preset
---

# Observability-preset

Brukes av `planlegger` når en oppgave legger til eller endrer metrikker, tracing eller
health-endepunkter. Basert på det etablerte `observability-setup`-skillet — dette
presetet er den korte, `planlegger`-spesifikke versjonen som avgjør sti/planreview og
tvinger inn brief-felt for `koder`.

## Trigger

Oppgaven nevner:
- Prometheus/Micrometer-metrikker, egendefinerte tellere/timere
- OpenTelemetry-spans/tracing
- `/isalive`/`/isready`/`/metrics`-endepunkter
- strukturert logging med nye felt (`kv(...)`)

## Default sti

- Legge til én forretningsmetrikk (counter/timer) i et allerede etablert
  observability-oppsett: `Sti=enkel`, `Krever planreview=nei`.
- Sette opp observability for en ny tjeneste fra bunnen, eller endre
  health-endepunktenes logikk (f.eks. hva `/isready` faktisk sjekker):
  `Sti=komplisert`, `Krever planreview=ja`.

Health-endepunkter er default komplisert fordi feil logikk her (f.eks. `/isready` som
feiler av feil grunn) kan trigge unødvendige restarts eller skjule reelle feil.

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **Hvilke helsesjekker `/isready` faktisk gjør**: eksakt hvilke avhengigheter
  (database, Kafka, eksterne tjenester) som sjekkes, og hva som skal skje hvis én er
  nede (returner `503` — ikke krasj appen).
- **Metrikknavn og -type**: eksakt navn (`snake_case`, f.eks. `users_created_total`),
  om det er en `Counter` eller `Timer`, og hva den forretningsmessig representerer
  (ikke bare tekniske JVM-metrikker som allerede kommer automatisk via
  `JvmMemoryMetrics`/`ProcessorMetrics`).
- **Strukturert logging**: bruk `kv("felt", verdi)`-argumenter i loggkall, ikke
  string-interpolerte meldinger — og aldri persondata i vanlig logg (se
  `brukerdialog-persondata`-preset hvis relevant).
- **Tracing-scope**: hvis manuelle spans legges til, hvilke attributter som settes på
  spannet, og at feil (`span.recordException`) håndteres i en `finally`-blokk slik at
  `span.end()` alltid kalles.

## Sjekkliste for koder

- [ ] `/isalive` svarer uten avhengighetssjekk (bare "er prosessen i live").
- [ ] `/isready` sjekker faktiske avhengigheter og returnerer `503` (ikke krasj) når en
      avhengighet er nede.
- [ ] `/metrics` eksponerer `meterRegistry.scrape()` uautentisert (Nais scraper den
      internt).
- [ ] Nye metrikker har beskrivende navn og enhet (`_total`, `_seconds`), ikke generiske
      navn som `counter1`.
- [ ] Logging bruker strukturerte argumenter (`kv(...)`), ikke string-konkatenering av
      variabel data inn i meldingsteksten.
- [ ] Ingen fødselsnummer, aktør-id, navn, adresse eller tokens i metrikk-tags eller
      logg-felt.
- [ ] Manuelle spans avsluttes alltid (`finally { span.end() }`), selv ved feil.

## Ikke gjør

- Ikke sett `/isready` til å feile av grunner som ikke faktisk påvirker om appen kan
  betjene trafikk (f.eks. ikke koble helsesjekk til en cron-jobbs status).
- Ikke legg til en preStop-hook eller manipuler readiness ved SIGTERM — Nais håndterer
  graceful shutdown med injisert `sleep 5`.
- Ikke legg persondata eller andre sensitive verdier i metrikk-tags (de havner i
  Prometheus/Grafana, som har bredere tilgang enn sikkerlogg).
- Ikke la en glemt `span.end()`-kall (f.eks. ved en tidlig `return` eller kastet
  exception) lekke åpne spans.
