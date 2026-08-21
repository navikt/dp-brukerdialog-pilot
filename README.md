# dp-brukerdialog-pilot

En enkel AI-pilot som **ren Copilot-plugin** med to agenter:
- `planlegger` (synlig for bruker)
- `koder` (intern, delegert av planlegger)

## Copilot-plugin-struktur

Plugin-filer:

```text
package-manifest.json
plugin/plugin.json
plugin/agents/planlegger.agent.md
plugin/agents/koder.agent.md
```

Målet i første versjon er en bevisst liten plugin med:
- 1 planlegger-agent som delegerer
- 1 koder-agent som implementerer
- 0 skills

## Installer lokalt

Fra repo-roten:

```bash
copilot plugin install ./plugin
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

## Oppdatere lokal installasjon etter endringer

Hvis du endrer agentfiler/manifest, installer på nytt:

```bash
copilot plugin install ./plugin
```

Eventuelt fjern og installer igjen:

```bash
copilot plugin uninstall dp-brukerdialog-pilot
copilot plugin install ./plugin
```

Dette er bevisst for å holde pluginen liten og enkel å bygge videre på.

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

## CI-gate

Workflowen `.github/workflows/eval-harness.yml` kjører:
- statiske sjekker av scripts + eval-filer

Live-eval kjøres lokalt:

```bash
python3 scripts/eval_planlegger.py --run --suite smoke --repeats 3
python3 scripts/eval_planlegger.py --run --suite policy --repeats 5
python3 scripts/eval_koder_brief.py --run --suite smoke --repeats 3
python3 scripts/eval_koder_brief.py --run --suite policy --repeats 5
python3 scripts/eval_golden_trace.py --run --suite smoke --repeats 3
python3 scripts/eval_golden_trace.py --run --suite policy --repeats 5
```
