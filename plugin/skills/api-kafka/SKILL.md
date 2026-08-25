---
name: api-kafka
description: Preset for oppgaver som kombinerer et API-endepunkt med et Kafka-event i samme leveranse
license: MIT
compatibility: Kotlin/Ktor eller Spring Boot backend med Kafka/Rapids & Rivers
metadata:
  domain: backend
  tags: api kafka rapids-rivers event-driven planlegger-preset
---

# API+Kafka preset

Brukes av `planlegger` når en oppgave kombinerer et REST-endepunkt med et event/topic i samme leveranse.

## Trigger

Oppgaven nevner **både**:
- et endepunkt (endpoint/API/rute), **og**
- et event/hendelse/topic/Kafka i samme oppgave.

## Default sti

- `Sti=komplisert`
- `Krever planreview=ja`

Dette er default fordi endring i én kanal (API) uten å tenke på den andre (event) lett skaper
inkonsistens mellom synkron respons og asynkron hendelse.

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **API-kontrakt**: eksakt request/response-form, inkl. feltnavn og typer.
- **Event-schema**: eksakt feltliste for eventet, inkl. versjon (`{team}.{domene}.v1`).
- **Idempotens**: hvordan konsument/produsent unngår duplikate effekter ved re-levering.
- **Feilstrategi**: hva skjer hvis API-kallet lykkes men event-publisering feiler (eller omvendt)?

## Sjekkliste for koder

- [ ] API-respons og event-payload er konsistente (samme data, ikke motstridende feltnavn).
- [ ] Event publiseres **etter** vellykket tilstandsendring, ikke før.
- [ ] Konsument-side (hvis del av scope) håndterer duplikate meldinger idempotent.
- [ ] Feilhåndtering logger uten å eksponere persondata (se `persondata`-preset).
- [ ] Topic/versjon følger `{team}.{domene}.v1`-konvensjon.

## Ikke gjør

- Ikke publiser event før API-transaksjonen er committet.
- Ikke anta at konsumenten kjører synkront med produsenten.
- Ikke innfør nye topics uten at det er eksplisitt godkjent i brief.
