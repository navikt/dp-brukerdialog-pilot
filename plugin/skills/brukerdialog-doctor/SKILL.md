---
name: brukerdialog-doctor
description: "Sjekker at dp-brukerdialog-pilot er riktig installert, at agentene og skillsene er synlige i sesjonen som forventet (skiller mellom bruker-valgbare og internt-only agenter), og om noen av pluginens brukerdialog-*-skills overlapper i navn eller innhold med andre installerte skills (personal, prosjekt eller andre plugins). Kun for eksplisitt bruk når brukeren ber om diagnose/sjekk av oppsettet — les-only audit, trigges aldri automatisk."
disable-model-invocation: true
license: MIT
compatibility: Copilot CLI-sesjoner med dp-brukerdialog-pilot installert
metadata:
  domain: meta
  tags: audit doctor diagnostikk skills plugin
---

# Brukerdialog doctor

Read-only audit av om dp-brukerdialog-pilot fungerer som forventet i denne
sesjonen. Trigges kun når brukeren eksplisitt ber om det (f.eks. "sjekk
oppsettet", "er pluginen riktig installert?", "diagnostiser skills"). Aldri
en del av planlegger sin vanlige rute-logikk.

## Hold audit read-only

Ikke opprett, endre, slett, commit, push, installer, aktiver, deaktiver eller
oppdater noe mens denne skillen er aktiv. Bare les og rapporter.

## Steg 1: Verifiser installasjon

Kjør `copilot plugin list` og bekreft:
- `dp-brukerdialog-pilot@dp-brukerdialog-pilot` er listet
- Versjonen matcher `plugin/plugin.json` sin `version` i dette repoet (hvis
  repoet er tilgjengelig lokalt)

Manglende oppføring betyr `NOT_READY`, ikke automatisk feilinstallert — sjekk
om `copilot plugin marketplace update` er kjørt nylig.

## Steg 2: Verifiser at agentene er synlige (eller riktig skjult)

Kun `planlegger` og `pr-reviewer` er `user-invocable: true` og skal vises i
`/agent`-dashbordet. `koder` og `reviewer` er internt-only (delegeres av
`planlegger`, ikke direkte valgbare — dette er tilsiktet, ikke en feil).
`troubleshoot` er også `user-invocable: false` **med vilje** (se CHANGELOG
[0.10.2]): den skal kun startes via `scripts/troubleshoot-safe.sh`, som bruker
`--agent`-flagget direkte og dermed omgår `/agent`-menyen. Rapporter
`UNVERIFIED` hvis dashbordet ikke er observerbart (f.eks. i en scriptet
`-p`-kjøring) — ikke `NOT_READY` bare fordi `koder`/`reviewer`/`troubleshoot`
ikke dukker opp i `/agent`, det er forventet oppførsel.

## Steg 3: Verifiser skills og se etter overlapp

Kjør `copilot skill list` og finn alle 12 `brukerdialog-*`-skills under
"Plugin skills":

`brukerdialog-api-kafka`, `brukerdialog-bff-auth`, `brukerdialog-create-skill`,
`brukerdialog-db-migrasjon`, `brukerdialog-doctor`, `brukerdialog-frontend-aksel`,
`brukerdialog-kotlin-ktor`, `brukerdialog-nais-deploy`, `brukerdialog-observability`,
`brukerdialog-persondata`, `brukerdialog-security-owasp`, `brukerdialog-testrammeverk`

Skills fra ulike kilder (personal, plugin, project, builtin) slås sammen til
én flat liste i denne CLI-versjonen — det finnes ingen automatisk namespacing
eller presedensregel. Se derfor etter:

- **Eksakt navnekollisjon**: et annet installert skill med akkurat samme navn
  som en av våre `brukerdialog-*`-skills. Prefikset gjør dette usannsynlig,
  men sjekk likevel — en bruker kan i teorien ha en egen skill med samme navn.
- **Faglig overlapp uten navnekollisjon** (forventet, ikke en feil i seg selv):
  f.eks. `brukerdialog-nais-deploy` vs. personal `nais`, `brukerdialog-frontend-aksel`
  vs. `aksel-builder`/`aksel-spacing`, `brukerdialog-kotlin-ktor` vs.
  `ktor-scaffold`/`kotlin-app-config`, `brukerdialog-observability` vs.
  `observability-setup`/`observability-debugging`, `brukerdialog-testrammeverk`
  vs. `playwright-testing`, `brukerdialog-bff-auth` vs. personal
  `tokenx-auth`/`nav-auth`. Rapporter disse som `DUPLICATION` (informativt) —
  ikke en `BLOCKER` — siden `brukerdialog-*`-varianten er et smalt
  planlegger-preset (brief-felt, sjekkliste), mens de andre er bredere
  fagkunnskap. Begge kan brukes samtidig uten konflikt.

## Steg 4: Rapporter

```text
BRUKERDIALOG_DOCTOR: READY | READY_WITH_GAPS | NOT_READY | UNVERIFIED

Installasjon:
- Plugin listet i `copilot plugin list`: VERIFIED | UNVERIFIED
- Versjon matcher plugin.json: VERIFIED | UNVERIFIED | N/A

Agenter:
- planlegger, pr-reviewer synlige i /agent: VERIFIED | UNVERIFIED
- koder, reviewer, troubleshoot korrekt SKJULT fra /agent (tilsiktet,
  user-invocable: false): VERIFIED | UNVERIFIED

Skills (11 brukerdialog-*):
- Alle 11 funnet i `copilot skill list`: VERIFIED | <mangler: liste> | UNVERIFIED
- Navnekollisjoner: INGEN | <liste over eksakte navnetreff>
- Faglig overlapp (informativt, ikke blokkerende): <liste, eller INGEN>

Minste neste steg:
- <én konkret handling, eller "ingen">
```

Bruk `NOT_READY` kun når plugin eller minst én agent/skill faktisk mangler.
Bruk `UNVERIFIED` når noe ikke kan observeres i denne sesjonstypen. Ikke gjett
— skill mellom bekreftet fakta og det som ikke kunne sjekkes.

## Ikke gjør

- Ikke installer, oppdater eller avinstaller plugin/skills under audit.
- Ikke anta at et navn-overlapp er en feil — de fleste overlapp er tilsiktet
  bredde/smalhet-forskjell, ikke duplisert arbeid.
- Ikke rapporter `NOT_READY` bare fordi `/agent`-dashbordet ikke kunne sjekkes
  i en ikke-interaktiv kjøring — bruk `UNVERIFIED` for den delen i stedet.
