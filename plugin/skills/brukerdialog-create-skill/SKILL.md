---
name: brukerdialog-create-skill
description: "Prosess for å lage, revidere eller diagnostisere en domain-preset-skill i denne pluginen (plugin/skills/). Kun for eksplisitt bruk når noen ber om en ny/endret preset-skill i selve dp-brukerdialog-pilot-repoet, eller lurer på hvorfor en skill ikke trigges — trigges aldri automatisk under vanlige kodeoppgaver."
disable-model-invocation: true
license: MIT
compatibility: dp-brukerdialog-pilot sitt eget plugin/skills/-tre
metadata:
  domain: meta-plugin-vedlikehold
  tags: skill-authoring meta domain-preset planlegger-preset
---

# Lag/revider en domain-preset-skill

Denne skillen gjelder kun **pluginens egne** domain-preset-skills
(`plugin/skills/brukerdialog-*`) — ikke dokumentasjon/skills i repoene
agentene jobber i (se "Repo-dokumentasjon" i `koder.agent.md`, som er ren
flagging, ikke opprettelse).

## 1. Bekreft at det faktisk er et gap

- Les gjennom eksisterende skills i `plugin/skills/` og preset-tabellen i
  `planlegger.agent.md`. Ikke lag en ny skill hvis et eksisterende preset
  allerede burde utvides i stedet.
- Grunngi behovet i noe konkret: en reell oppgave/gjentagende mønster, ikke en
  antagelse. Hvis usikker på hvilket område som gir mest verdi, spør brukeren
  (`ask_user`) i stedet for å gjette — det er slik `brukerdialog-bff-auth` og
  `brukerdialog-security-owasp` ble valgt.

## 2. Design innholdet

Følg strukturen fra en eksisterende skill (f.eks. `brukerdialog-bff-auth`)
som mal:

- **Frontmatter**: `name` (matcher mappenavn, `brukerdialog-`-prefiks),
  `description` (ett-linjes triggerbeskrivelse — dette telles i
  discovery-budsjettet, se punkt 5), `license: MIT`, `compatibility`,
  `metadata.domain`/`metadata.tags`.
- **Trigger**: konkrete signaler i oppgaveteksten som aktiverer presetet.
- **Default sti/planreview**: hva som er `enkel` vs. `komplisert` for dette
  området spesifikt (ikke bare den generelle definisjonen i
  `planlegger.agent.md`).
- **Obligatoriske brief-felt**: hva `KODER_BRIEF` må inneholde for akkurat
  denne typen oppgave (f.eks. audience-format for `bff-auth`).
- **Sjekkliste / "ikke gjør"**: konkrete fallgruver spesifikt for området.

## 3. Registrer og valider

- Registrer presetet i `planlegger.agent.md`s preset-tabell.
- Oppdater README: preset-listen, "Domain-preset-skills"-seksjonen, og
  agent-/skilltallene andre steder i filen.
- Kjør `python3 scripts/validate_plugin_schema.py` — dette sjekker også at
  det aggregerte discovery-budsjettet (`MAX_DISCOVERY_TEXT_BYTES`) ikke
  sprenges. Hvis det feiler: korter ned `description`, ikke bare hev
  budsjettet uten å vurdere om beskrivelsen kan strammes.

## 4. Valider empirisk, ikke bare skriftlig

Hvis presetet endrer en reell sti/planreview/koder-avgjørelse i et konkret
scenario, legg til (eller oppdater) et scenario i
`eval/planlegger-tests.json` og kjør det med `--repeats 3` eller mer for å
bekrefte at det faktisk gir forventet utfall — ikke anta at prosaen i skillen
alene endrer modellens avgjørelse. Se `scripts/eval_planlegger.py`.

## 5. Oppdater CHANGELOG og versjon

- Beskriv gapet skillen dekker og hvorfor, ikke bare hva som ble lagt til.
- Ny skill er normalt en minor-bump; ren tekstrettelse i en eksisterende
  skill er patch. (Denne konvensjonen er ikke alltid fulgt strengt historisk
  — se CHANGELOG for presedens, ikke bare denne regelen.)
- Reinstaller (`copilot plugin marketplace update` + `install`) og bekreft
  riktig versjon/skilltall med `copilot plugin list` før commit.

## Diagnostisere hvorfor en skill ikke trigges

Hvis en skill finnes men ikke plukkes opp av `planlegger`:
- Sjekk om `description` faktisk inneholder ordene/signalene som brukes i
  reelle oppgavetekster — ikke bare interne fagtermer.
- Sjekk om et annet, mer generelt preset "stjeler" treffet fordi det står
  først eller har et bredere treffmønster i preset-tabellen.
- Ikke gjett — kjør en faktisk test-prompt gjennom `eval_planlegger.py` eller
  en ekte sesjon og se hva som velges, fremfor å anta ut fra teksten alene.
