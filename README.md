# dp-brukerdialog-pilot

En enkel AI-pilot som **ren Copilot-plugin** med tre agenter:
- `planlegger` (synlig for bruker)
- `koder` (intern, delegert av planlegger)
- `reviewer` (intern, delegert av planlegger etter koder — kvalitetssjekker den
  faktiske diffen før planlegger rapporterer FERDIG)

Se [CHANGELOG.md](./CHANGELOG.md) for versjonshistorikk.

## Copilot-plugin-struktur

Plugin-filer:

```text
.github/plugin/marketplace.json
plugin/plugin.json
plugin/agents/planlegger.agent.md
plugin/agents/koder.agent.md
plugin/agents/reviewer.agent.md
plugin/skills/api-kafka/SKILL.md
plugin/skills/db-migrasjon/SKILL.md
plugin/skills/persondata/SKILL.md
```

Målet i første versjon var en bevisst liten plugin med:
- 1 planlegger-agent som delegerer
- 1 koder-agent som implementerer
- 0 skills

Vi har siden lagt til 3 domain-preset-skills (se "Domain-preset-skills" under) for å gjøre
`KODER_BRIEF` mer treffsikker på Nav-typiske oppgaver, uten å blåse opp agent-promptet.

## Installer

Direkte install fra sti/repo/URL er under utfasing i Copilot CLI ("Direct plugin installs
(repos, URLs, local paths) are deprecated"). Bruk marketplace-oppsettet i stedet:

```bash
copilot plugin marketplace add <owner>/dp-brukerdialog-pilot
copilot plugin install dp-brukerdialog-pilot@dp-brukerdialog-pilot
```

For lokal utvikling (uten å pushe til GitHub først) kan du legge til marketplacet fra en
lokal sti:

```bash
copilot plugin marketplace add /full/sti/til/dp-brukerdialog-pilot
copilot plugin install dp-brukerdialog-pilot@dp-brukerdialog-pilot
```

Verifiser installasjon:

```bash
copilot plugin list
```

Start en ny Copilot-sesjon og velg agent med:

```text
/agent
```

Du skal kun se `planlegger` som bruker-valg.

## Når du bør vente eller avbryte

- Vent når statusen viser tydelig fremdrift i en kompleks oppgave.
- Avbryt eller sjekk hvis en liten oppgave bruker lang tid uten synlig fremdrift, eller hvis tester feiler tidlig og ikke blir håndtert.

Planlegger bruker faste progresjonsetiketter i dialogen:
- `STARTET`
- `DELEGERER`
- `VALIDERER`
- `FERDIG`
- `STOPPET`

Ved database/auth/persondata/secrets ber planlegger om eksplisitt bekreftelse før den går videre.

Planlegger støtter også operasjonsmoduser:
- `hurtig` (tempo)
- `standard` (default)
- `trygg` (strengere review/stopp)

Og den bruker domain-presets for Nav-typiske oppgaver:
- `API+Kafka`
- `DB+migrasjon`
- `Persondata`

## Domain-preset-skills

Presetene er egne skills i `plugin/skills/`, ikke innebygd tekst i agentfilen:

- `plugin/skills/api-kafka/SKILL.md`
- `plugin/skills/db-migrasjon/SKILL.md`
- `plugin/skills/persondata/SKILL.md`

Hver skill inneholder trigger, default sti/planreview, obligatoriske ekstra brief-felt,
sjekkliste for `koder` og en "ikke gjør"-liste. Fordelen med egne skill-filer fremfor
innebygd tekst er at de er lettere å teste/utvide isolert, og at de er tydelig
tilgjengelige for andre agenter/verktøy som leser skills uavhengig av `planlegger`.

## Oppdatere installasjon etter endringer

Hvis du endrer agentfiler/skills/manifest, oppdater marketplacet og installer på nytt:

```bash
copilot plugin marketplace update dp-brukerdialog-pilot
copilot plugin install dp-brukerdialog-pilot@dp-brukerdialog-pilot
```

Eventuelt fjern og installer igjen:

```bash
copilot plugin uninstall dp-brukerdialog-pilot
copilot plugin install dp-brukerdialog-pilot@dp-brukerdialog-pilot
```

Dette er bevisst for å holde pluginen liten og enkel å bygge videre på.

## Sesjonsopprydding for eval-kjøringer

Hver `copilot -p`-kjøring i eval-harnessen oppretter en lokal sesjon. Som default sletter
harnessen sesjonen (DB-rader i `~/.copilot/session-store.db` + `~/.copilot/session-state/<id>/`)
rett etter hver kjøring, slik at sesjonslisten ikke fylles opp av testkjøringer.

Bruk `--keep-sessions` for å beholde sesjonene (f.eks. for å feilsøke en enkelt kjøring):

```bash
python3 scripts/eval_planlegger.py --run --keep-sessions
```

## Eval-harness

Kjør faste prompts mot `planlegger` og score beslutningene automatisk:

```bash
python3 scripts/eval_planlegger.py --run
```

For mer stabil måling (mindre tilfeldig variasjon mellom kjøringer), kjør med flertallsavgjørelse:

```bash
python3 scripts/eval_planlegger.py --run --repeats 3
```

Merk: Hvis ingen svarvariant får faktisk flertall (>50%), markeres testen som `inconclusive` og feiler.

Kjør bare rask suite:

```bash
python3 scripts/eval_planlegger.py --run --suite smoke --repeats 3
```

Kjør policy-suite:

```bash
python3 scripts/eval_planlegger.py --run --suite policy --repeats 5
```

For å bare skrive ut promptene:

```bash
python3 scripts/eval_planlegger.py --emit-prompts
```

Harnessen forventer at `planlegger` svarer med kort JSON i eval-modus, og sjekker
om sti, planreview, koder og spørsmål matcher forventet resultat.

Testmatrisen (`eval/planlegger-tests.json`) dekker også operasjonsmoduser
(f.eks. at en sikkerhetstrigger krever planreview selv i `hurtig`-modus via
et `modus`-felt på testen) og domain-presets (`API+Kafka`, `DB+migrasjon`).

> Harnessen bruker `copilot -p` i programmatisk modus, så du må ha Copilot CLI
> installert og tilgjengelig i PATH lokalt.

## KODER_BRIEF-harness

Valider at `planlegger` produserer en komplett `KODER_BRIEF` med riktige nøkkelfelt:

```bash
python3 scripts/eval_koder_brief.py --run --repeats 3
```

Dette sjekker:
- at alle obligatoriske `KODER_BRIEF`-felter finnes
- at `Sti` og `Krever planreview` matcher forventningen
- at resultatet har faktisk flertall

## Golden trace (ende-til-ende)

Valider hele kjeden fra brukerprompt til koder-statusformat:

```bash
python3 scripts/eval_golden_trace.py --run --repeats 3
```

Dette sjekker:
- at `planlegger` returnerer komplett `KODER_BRIEF`
- at `koder` svarer i riktig statusformat
- at `Sti` og `Krever planreview` matcher forventet golden-trace
- at `koder`-status er innenfor forventet statussett per test

## Reviewer-harness

Valider at `reviewer`-agenten returnerer riktig verdikt (`APPROVED`/`NEEDS_CHANGES`/
`BLOCKED`) gitt et syntetisk `KODER_BRIEF` + `koder`s statusrapport:

```bash
python3 scripts/eval_reviewer.py --run --repeats 3
```

Dette sjekker at reviewer:
- godkjenner en ren diff som samsvarer med briefet (`APPROVED`)
- krever endring ved rapportert `Ikke gjør`-brudd, f.eks. en ugodkjent ny
  dependency (`NEEDS_CHANGES`)
- krever endring ved manglende/uekte verifisering (`NEEDS_CHANGES`)
- blokkerer ved rapportert stopp-punkt-brudd, f.eks. fødselsnummer logget i
  vanlig logg (`BLOCKED`), uansett hvor liten endringen ellers virker

## Ekte integrasjonstest (scratch-repo)

De andre harnessene er simulerte kontrakttester ("ikke bruk verktøy, ikke gjør
filendringer") og kan derfor ikke fange feil i selve verktøybruken. Denne
harnessen kjører et ekte oppdrag med verktøy skrudd på, i en engangs
git-scratch-repo, og verifiserer det faktiske resultatet på disk:

```bash
python3 scripts/eval_integration.py --run
```

Dette:
- oppretter en midlertidig git-repo med gitt fixture-innhold
- kjører `planlegger` mot den med `--allow-all-tools` (ekte fil-/verktøybruk)
- sjekker at forventet innhold faktisk finnes i filene etterpå
- sjekker at det ikke ble gjort en uventet commit (policy: ingen auto-commit)
- rydder opp scratch-repo og lokal sesjon automatisk (`--keep-scratch` /
  `--keep-sessions` for å beholde dem ved feilsøking)

Testene defineres i `eval/integration-tests.json` med `fixture` (filer som
seedes), `prompt` (det ekte oppdraget) og
`expect_contains`/`expect_no_commit`/`expect_no_file_changes`/`expect_output_contains`.

Suiten dekker fire reelle scenarioer:
- `smoke` (id 1): enkel sti, direkte filendring uten planreview.
- `policy` (id 2): komplisert sti (offentlig API-kontraktendring) — verifiserer
  at oppgaven fortsatt fullføres korrekt end-to-end selv når den krever et
  ekstra planreview-steg internt.
- `policy` (id 3): persondata-stopp-punkt (fødselsnummer-endepunkt) —
  verifiserer at `planlegger` ikke gjør noen filendringer i det hele tatt når
  den treffer et stopp-punkt den ikke kan få bekreftet (harnessen kjører med
  `--no-ask-user`), altså at den fail-closed-oppfører seg trygt i stedet for å
  gjette seg videre.
- `smoke` (id 4): verifiserer at reviewer-steget faktisk trigges i den ekte
  flyten, ved å sjekke at planleggers sluttsvar inneholder den obligatoriske
  `Reviewer: <status>`-linjen.

> Denne harnessen tar vesentlig lengre tid enn de andre (ekte agentkjøring med
> verktøy), så den er ikke ment å kjøres med høy `--repeats` som de andre.

> **Kjent flakiness:** scenario id 2 (komplisert sti) kan av og til feile fordi
> modellen (falt tilbake til `auto` siden `gpt-5.4` ikke er tilgjengelig i
> dette miljøet) enten stopper med et unødvendig avklaringsspørsmål eller
> hevder å ha gjort en endring uten faktisk å ha kalt verktøyet. Dette er
> bekreftet å være modell-flakiness som fantes før reviewer-agenten ble lagt
> til (reprodusert identisk på forrige plugin-versjon), ikke en regresjon.

## CI-gate

Workflowen `.github/workflows/eval-harness.yml` kjører:
- statiske sjekker av scripts + eval-filer
- `scripts/validate_plugin_schema.py`: validerer at agent-/skill-frontmatter
  har påkrevde felt, at `name` matcher filnavn/mappenavn, og at
  `.github/plugin/marketplace.json` ikke har driftet fra `plugin/plugin.json`
  (feil `source`-sti, eller name/version-mismatch). Ingen Copilot-lisens
  kreves for denne sjekken.

Live-eval kjøres lokalt:

```bash
python3 scripts/eval_planlegger.py --run --suite smoke --repeats 3
python3 scripts/eval_planlegger.py --run --suite policy --repeats 5
python3 scripts/eval_koder_brief.py --run --suite smoke --repeats 3
python3 scripts/eval_koder_brief.py --run --suite policy --repeats 5
python3 scripts/eval_golden_trace.py --run --suite smoke --repeats 3
python3 scripts/eval_golden_trace.py --run --suite policy --repeats 5
python3 scripts/eval_reviewer.py --run --suite smoke --repeats 3
python3 scripts/eval_reviewer.py --run --suite policy --repeats 5
python3 scripts/eval_integration.py --run
```
