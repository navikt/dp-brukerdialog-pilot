# dp-brukerdialog-pilot

En enkel AI-pilot som **ren Copilot-plugin** med seks agenter. Dette dokumentet
er en kort oversikt — se lenkene under for detaljer.

Se [CHANGELOG.md](./CHANGELOG.md) for versjonshistorikk.

## Kom i gang

```bash
copilot plugin marketplace add <owner>/dp-brukerdialog-pilot
copilot plugin install dp-brukerdialog-pilot@dp-brukerdialog-pilot
```

Se [docs/installasjon.md](./docs/installasjon.md) for lokal utvikling, verifisering
og oppdatering etter endringer.

## Agentene

| Agent | Synlig for bruker | Kort |
|---|---|---|
| `sparring` | Ja | Avklarer problem, ønsket effekt og brukerverdi for én oppgave/idé, før den blir en plan. Kobler seg på `planlegger` etter eksplisitt godkjenning. |
| `planlegger` | Ja | Hovedagenten. Avklarer mål/sti, lager `KODER_BRIEF`, kjører planreview ved behov, delegerer til `koder`. |
| `koder` | Nei (intern) | Implementerer avgrensede kodeendringer fra `planlegger`s brief. |
| `reviewer` | Nei (intern) | Kvalitetssjekker `koder`s faktiske diff før `planlegger` rapporterer ferdig. |
| `pr-reviewer` | Ja | Frittstående — reviewer **andres** PR-er/branches på forespørsel. Read-only, blokkerer aldri. |
| `troubleshoot` | Nei (kun via script) | Frittstående — feilsøker produksjonsproblemer på Nais. Startes kun via `scripts/troubleshoot-safe.sh`, se hvorfor i [docs/agenter.md](./docs/agenter.md#troubleshoot). |

Se [docs/agenter.md](./docs/agenter.md) for fullstendig beskrivelse av hver
agent, pluginstruktur, modellvalg, domain-preset-skills og diagnostikk.

## Domain-preset-skills

12 skills i `plugin/skills/` gjør `KODER_BRIEF` mer treffsikker på Nav-typiske
oppgaver (Kafka, Nais-deploy, persondata, Aksel, TokenX/BFF-auth, med mer),
uten å blåse opp agent-promptet. Se
[docs/agenter.md#domain-preset-skills](./docs/agenter.md#domain-preset-skills)
for full liste og triggere.

## Testing og eval

Pluginen har eval-harnesser for `planlegger`, `koder`, `reviewer`,
`pr-reviewer` og `troubleshoot` — både simulerte kontrakttester og ekte
scratch-repo-kjøringer med verktøy skrudd på. Se
[docs/testing.md](./docs/testing.md) for alle kommandoer, hva hver test
faktisk dekker, og kjente flakiness-mønstre.

## Bidra

Se agentfilene i `plugin/agents/` for konvensjoner. Kjør alltid
`python3 scripts/validate_plugin_schema.py` etter endringer i
agent-/skill-frontmatter.
