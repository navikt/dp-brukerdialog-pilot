---
name: nais-deploy
description: Preset for oppgaver som endrer Nais-manifest, deploy-workflow eller annen infrastruktur-/deploykonfigurasjon
license: MIT
compatibility: Nais-applikasjoner med .nais/nais*.yaml og GitHub Actions-deploy
metadata:
  domain: infra
  tags: nais deploy accesspolicy github-actions planlegger-preset
---

# Nais-deploy preset

Brukes av `planlegger` når en oppgave endrer Nais-manifest, deploy-workflow eller
annen infrastruktur-/deploykonfigurasjon.

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
vanskelige å reversere raskt (f.eks. `accessPolicy` som stenger ute en avhengighet).

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **Diff i tilgang**: eksakt hvilke `accessPolicy.inbound`/`outbound`-regler legges til,
  endres eller fjernes, og hvem/hva det gjelder.
- **Miljøscope**: om endringen gjelder dev, prod, eller begge — og om den skal rulles ut
  trinnvis (dev først, verifiser, så prod).
- **Rollback-plan**: hvordan reversere endringen raskt hvis den feiler i prod (f.eks.
  revert av manifest + ny deploy, ikke manuell inngripen i klyngen).
- **Ressurskonsekvens**: hvis ressurser (CPU/memory/replicas) endres, hvorfor, og hvilken
  last-antakelse det er basert på.

## Sjekkliste for koder

- [ ] `accessPolicy.inbound` og `.outbound` er eksplisitt — ingen implisitt/åpen tilgang.
- [ ] Ingen nye secrets er hardkodet i manifest eller workflow; de refereres via
      `envFrom`/Nais sitt secret-oppsett.
- [ ] CPU-limits er **ikke** satt (kun `requests`), i tråd med Nais-anbefaling.
- [ ] Endringer i `replicas`/ressurser er begrunnet i brief, ikke vilkårlige tall.
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
