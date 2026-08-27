---
name: brukerdialog-nais-deploy
description: Preset for oppgaver som endrer Nais-manifest, deploy-workflow eller annen infrastruktur-/deploykonfigurasjon
license: MIT
compatibility: Nais-applikasjoner med .nais/nais*.yaml og GitHub Actions-deploy
metadata:
  domain: infra
  tags: nais deploy accesspolicy github-actions planlegger-preset
---

# Nais-deploy preset

Brukes av `planlegger` når en oppgave endrer Nais-manifest, deploy-workflow eller
annen infrastruktur-/deploykonfigurasjon. Basert på det etablerte `nais`-skillet
(manifest-struktur, pod-lifecycle, feilsøking) — dette presetet er den korte,
`planlegger`-spesifikke versjonen som avgjør sti/planreview og tvinger inn brief-felt.

## Trigger

Oppgaven endrer en av:
- `.nais/*.yaml`/`nais.yaml` (accessPolicy, ressurser, replicas, env, secrets)
- `.github/workflows/*` som bygger eller deployer
- GCP-ressurser deklarert via Nais (`gcp.sqlInstances`, `gcp.redis`, `gcp.buckets`)

## Default sti

- `Sti=komplisert`
- `Krever planreview=ja`
- **Alltid stopp-punkt før delegasjon** (dette faller allerede inn under
  "infrastruktur, secrets eller deploy-konfigurasjon" i planleggers
  "Stopp-punkter før risikofylte endringer" — bruker må bekrefte eksplisitt).

Feil i denne kategorien påvirker ofte produksjonstilgjengelighet direkte og kan være
vanskelige å reversere raskt (f.eks. `accessPolicy` som stenger ute en avhengighet, eller
manglende memory-limit som gir OOM-problemer i klyngen).

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **Diff i tilgang**: `accessPolicy` er deny-all som default — eksakt hvilke
  `inbound`/`outbound`-regler legges til, endres eller fjernes, og hvem/hva det gjelder.
- **Miljøscope**: om endringen gjelder dev, prod, eller begge (`nais-dev.yaml`/
  `nais.yaml` er separate manifester) — og om den skal rulles ut trinnvis (dev først,
  verifiser i Grafana/Loki, så prod).
- **Rollback-plan**: hvordan reversere endringen raskt hvis den feiler i prod (revert
  av manifest + ny deploy via CI/CD, ikke manuell inngripen i klyngen).
- **Ressurskonsekvens**: hvis ressurser (CPU-request/memory/replicas) endres, hvorfor,
  og hvilken last-antakelse det er basert på (se ressurstabellen under).

## Sjekkliste for koder

- [ ] `accessPolicy.inbound` og `.outbound` er eksplisitt — ingen implisitt/åpen tilgang
      (default er deny-all, så manglende regel = ingen tilgang, ikke "alt tillatt").
- [ ] Ingen nye secrets er hardkodet i manifest eller workflow; de refereres via
      `envFrom`/Nais sitt secret-oppsett.
- [ ] CPU-**limits** er **ikke** satt (kun `requests`) — CPU-limits gir throttling.
      Memory-**limits** derimot er obligatorisk (manglende memory-limit gir OOM-problemer
      i klyngen).
- [ ] Endringer i `replicas`/ressurser er begrunnet i brief, ikke vilkårlige tall (se
      liten/medium/stor-tabellen i `nais`-skillet: 50m/256Mi, 100m/512Mi, 200m/1Gi).
- [ ] Ingen egen `preStop`-hook er lagt til — Nais injiserer allerede `sleep 5`, og
      `terminationGracePeriodSeconds` må være større enn 5s + faktisk drainingtid.
- [ ] `{{ image }}` (eller tilsvarende CI/CD-plassholder) er ikke hardkodet til et
      spesifikt image i manifestet.
- [ ] GitHub Actions-steg bruker pinnet versjon (SHA eller kjent tag), ikke `@main`.
- [ ] Endringen deployes til dev før prod i samme workflow/rekkefølge som eksisterende
      pipeline.

## Ikke gjør

- Ikke sett `accessPolicy` til å tillate alt (`*`) for å "fikse" en tilgangsfeil raskt.
- Ikke fjern helsesjekk-endepunkter (`liveness`/`readiness`) eller `prometheus`-oppsett
  som del av en urelatert endring.
- Ikke deploy direkte til prod uten at endringen først er verifisert i dev.
- Ikke legg til nye permissions i GitHub Actions-workflows uten eksplisitt begrunnelse
  i brief.
- Ikke sett readiness til `false` ved SIGTERM eller legg til egen `preStop`-sleep —
  Nais håndterer dette allerede (LB dreneres, appen får SIGTERM, drainer in-flight
  requests og avslutter).
