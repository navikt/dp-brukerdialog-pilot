# Changelog

Alle nevneverdige endringer i denne pluginen dokumenteres her.
Format følger løst [Keep a Changelog](https://keepachangelog.com/), versjonsnummer i `plugin/plugin.json`.

## [0.3.0]

### Lagt til
- Ny intern agent `reviewer` (`plugin/agents/reviewer.agent.md`, modell
  `gemini-3.7-flash` — bevisst en annen modellfamilie enn `koder`/`planlegger`
  for å unngå delte blindsoner, samtidig en lett/rask-tier for lav kost).
  Delegeres av `planlegger` etter at `koder` er ferdig, men før `FERDIG`
  rapporteres til bruker. Sjekker den faktiske diffen (ikke planen — det gjør
  planreview allerede) opp mot brief: akseptkriterier, "ikke gjør"-brudd,
  scope-kryp, manglende verifisering og stopp-punkt-brudd.
- Reviewer kjører alltid (uansett sti), men bare når `koder` faktisk endret
  filer. Ved `NEEDS_CHANGES` sendes ett avgrenset oppfølgingsbrief tilbake til
  `koder` (maks 1 retry-runde), deretter eskaleres til bruker i stedet for å
  loope videre. Ved `BLOCKED` (stopp-punkt-brudd) stoppes alltid, uansett
  hvor liten endringen ellers virker.
- Planleggers sluttoppsummering inneholder nå alltid en
  `Reviewer: <APPROVED|NEEDS_CHANGES|BLOCKED>`-linje (eller "hoppet over" hvis
  ingen filer ble endret), for åpenhet om reviewer-vurderingen.
- Ny kontraktstest `scripts/eval_reviewer.py` + `eval/reviewer-tests.json` (4
  scenarier: ren diff, "ikke gjør"-brudd, manglende verifisering,
  stopp-punkt-brudd).
- Nytt `expect_output_contains`-assertion i `eval_integration.py` + nytt
  scenario (id 4) som verifiserer at reviewer-steget faktisk trigges i den
  ekte ende-til-ende-flyten.

## [0.2.0]

### Lagt til
- `.github/plugin/marketplace.json`: riktig marketplace-manifest for
  distribusjon (`copilot plugin marketplace add` + `copilot plugin install
  <navn>@<marketplace>`), i stedet for direkte sti-/repo-install som CLI-en nå
  advarer om at blir faset ut. Den gamle, uoffisielle `package-manifest.json`
  (som CLI-en aldri faktisk leste) er fjernet.
- To nye scenarioer i `eval_integration.py`: komplisert sti (offentlig
  API-kontraktendring i en DTO) og persondata-stopp-punkt (fødselsnummer-
  endepunkt). Sistnevnte innfører `expect_no_file_changes`-assertion, som
  verifiserer at `planlegger` gjør null filendringer når den treffer et
  stopp-punkt den ikke kan få bekreftet (harnessen kjører med
  `--no-ask-user`), i stedet for å gjette seg videre.
- CI-sjekk (`scripts/validate_plugin_schema.py`) som validerer agent-/skill-
  frontmatter (påkrevde felt, `name` matcher filnavn/mappenavn) og at
  `.github/plugin/marketplace.json` ikke har driftet fra `plugin/plugin.json`
  (feil `source`-sti, eller name/version-mismatch). Kjører uten
  Copilot-lisens, som en del av CI-gaten.
- Ekte end-to-end integrasjonstest (`scripts/eval_integration.py`,
  `eval/integration-tests.json`): kjører `planlegger` med `--allow-all-tools`
  mot en engangs git-scratch-repo og verifiserer det faktiske filresultatet
  på disk, i motsetning til de andre harnessene som simulerer kontrakten uten
  verktøybruk.
- Domain-presets (`API+Kafka`, `DB+migrasjon`, `Persondata`) er trukket ut fra
  `planlegger.agent.md` til egne skills i `plugin/skills/`, hver med trigger,
  default sti/planreview, obligatoriske brief-felt, sjekkliste for `koder` og
  en ikke-gjør-liste.
- Automatisk sesjonsopprydding i eval-harnessen: hver `copilot -p`-kjøring får
  en egen sesjons-UUID og slettes (DB-rader + `session-state`-mappe) rett
  etter kjøring, slik at sesjonslisten ikke fylles opp av testkjøringer.
  Nytt flagg `--keep-sessions` for å beholde sesjoner ved feilsøking.

## [0.1.0]

### Lagt til
- Første versjon av pluginen: `planlegger` (synlig for bruker) og `koder`
  (intern, delegert av planlegger) som Copilot-agenter.
- Fast arbeidskontrakt i planleggers første svar (modus, sti, hvorfor, neste
  steg, stopp-punkt) og et strengt `KODER_BRIEF`-format mellom agentene.
- Sti- og planreview-policy (enkel vs. komplisert), operasjonsmoduser
  (`hurtig`, `standard`, `trygg`), og stopp-punkter for
  database/auth/persondata/secrets.
- Modell-, logg-, MCP- og skills-policy for agentene, samt kryssrepo-policy
  med håndoff-mal.
- Eval-harness med tre nivåer: `eval_planlegger.py` (beslutninger),
  `eval_koder_brief.py` (brief-kontrakt), `eval_golden_trace.py`
  (ende-til-ende planlegger → koder), alle med flertallsavgjørelse
  (`--repeats`) og suite-filtrering (`smoke`/`policy`).
- CI-gate (`.github/workflows/eval-harness.yml`) med statiske sjekker av
  scripts og eval-matriser (live eval kjøres lokalt, ikke i CI, siden GitHub
  Actions ikke har Copilot-lisens eller tilgang til andre team-repo).
