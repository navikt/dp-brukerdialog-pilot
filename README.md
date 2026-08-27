# dp-brukerdialog-pilot

En enkel AI-pilot som **ren Copilot-plugin** med fire agenter:
- `planlegger` (synlig for bruker)
- `koder` (intern, delegert av planlegger — unntak: for svært små, mekaniske
  mikro-endringer på enkel sti kan planlegger gjøre endringen selv, se
  "Mikro-endring-unntak" i `plugin/agents/planlegger.agent.md`)
- `reviewer` (intern, delegert av planlegger etter koder — kvalitetssjekker den
  faktiske diffen før planlegger rapporterer FERDIG)
- `pr-reviewer` (synlig for bruker, uavhengig av de tre andre — reviewer andres
  PR-er/branches på forespørsel, se "PR-reviewer" under)

Se [CHANGELOG.md](./CHANGELOG.md) for versjonshistorikk.

## Copilot-plugin-struktur

Plugin-filer:

```text
.github/plugin/marketplace.json
plugin/plugin.json
plugin/agents/planlegger.agent.md
plugin/agents/koder.agent.md
plugin/agents/reviewer.agent.md
plugin/agents/pr-reviewer.agent.md
plugin/skills/brukerdialog-api-kafka/SKILL.md
plugin/skills/brukerdialog-db-migrasjon/SKILL.md
plugin/skills/brukerdialog-persondata/SKILL.md
plugin/skills/brukerdialog-frontend-aksel/SKILL.md
plugin/skills/brukerdialog-testrammeverk/SKILL.md
plugin/skills/brukerdialog-nais-deploy/SKILL.md
```

Målet i første versjon var en bevisst liten plugin med:
- 1 planlegger-agent som delegerer
- 1 koder-agent som implementerer
- 0 skills

Vi har siden lagt til 6 domain-preset-skills (se "Domain-preset-skills" under) for å gjøre
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

Du skal se `planlegger` og `pr-reviewer` som bruker-valg. `koder` og `reviewer` er
interne og vises ikke i `/agent`.

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
- `Frontend+Aksel`
- `Testrammeverk`
- `Nais-deploy`

## Domain-preset-skills

Presetene er egne skills i `plugin/skills/`, ikke innebygd tekst i agentfilen:

- `plugin/skills/brukerdialog-api-kafka/SKILL.md`
- `plugin/skills/brukerdialog-db-migrasjon/SKILL.md`
- `plugin/skills/brukerdialog-persondata/SKILL.md`
- `plugin/skills/brukerdialog-frontend-aksel/SKILL.md` — UI-komponenter med Aksel Design System
  (@navikt/ds-react). Enkel sti for isolerte komponent-tillegg, komplisert for nye
  sider/bred layout-endring.
- `plugin/skills/brukerdialog-testrammeverk/SKILL.md` — innføring av nytt testrammeverk/CI-oppsett
  (Vitest/Playwright/Kotest), ikke enkelttester i eksisterende oppsett.
- `plugin/skills/brukerdialog-nais-deploy/SKILL.md` — endringer i Nais-manifest, deploy-workflow
  eller GCP-ressurser. Faller inn under eksisterende infra/secrets-stopp-punkt.

Hver skill inneholder trigger, default sti/planreview, obligatoriske ekstra brief-felt,
sjekkliste for `koder` og en "ikke gjør"-liste. Fordelen med egne skill-filer fremfor
innebygd tekst er at de er lettere å teste/utvide isolert, og at de er tydelig
tilgjengelige for andre agenter/verktøy som leser skills uavhengig av `planlegger`.

## PR-reviewer

`pr-reviewer` er en frittstående, bruker-invokerbar agent for å reviewe **andres**
PR-er/branches — uavhengig av `planlegger`→`koder`→`reviewer`-kjeden, som kun
kvalitetssikrer vårt eget arbeid internt i én økt.

Bruk den ved å velge `pr-reviewer` i `/agent` og be den reviewe en PR eller branch, f.eks.:

```text
Review PR #12
Review branchen min mot main
Review de uncommittede endringene mine
```

**Diff-strategi** (prioritert rekkefølge):
1. `gh pr diff <nr>` hvis PR-nummer er oppgitt og `gh`-CLI er tilgjengelig/autentisert.
2. Ellers `git diff <base>...<head>` mot detektert default-branch eller oppgitt branch,
   inkludert uncommittede endringer.
3. MCP (f.eks. IntelliJ sin PR-integrasjon) kan berike konteksten, men er aldri en
   forutsetning — samme prinsipp som `planlegger`s MCP-policy.

`pr-reviewer` er **read-only** som hovedregel: den gjør aldri filendringer eller
commits. Den skriver alltid ut en strukturert review i terminalen
(sikkerhetskritisk / infrastruktur / kodekvalitet), og flagger for et menneske —
den blokkerer aldri og gir ikke et formelt godkjent/avvist-verdikt (det er den
interne `reviewer`s jobb for vårt eget arbeid, ikke denne agentens jobb for andres
PR-er).

**PR-kommentar-posting (opt-in, unntaket fra read-only):** som standard poster den
ingenting. Hvis du eksplisitt ber om det i samme oppgave ("post som kommentar på
PR-en"), **og** et konkret PR-nummer er kjent (kun via `gh pr diff <nr>`-flyten,
ikke generisk `git diff`), **og** `gh`-CLI er installert og autentisert
(`gh auth status`): poster den reviewrapporten med
`gh pr comment <nr> --body-file <fil>` og rapporterer om det lyktes. Mangler ett av
disse vilkårene, forsøker den ikke posting i det hele tatt — den forklarer i stedet
konkret hvorfor i rapportens `Kommentar-posting`-linje, og faller tilbake til vanlig
terminal-only-oppførsel.

Verifisert med en **fake `gh`-binær** i eval-harnessen (`eval/pr-reviewer-tests.json`,
`scripts/eval_pr_review.py`), portabel uansett om maskinen som kjører evalen faktisk
har `gh` installert (PATH saneres for et ekte `gh` i "absent"-modus, så testen ikke
bare "tilfeldigvis" passerer fordi dette miljøet mangler `gh`):
- id 3 (`gh_mode=absent`): `gh` finnes ikke på PATH — agenten faller korrekt tilbake
  uten å krasje eller late som noe ble postet.
- id 4 (`gh_mode=unauthenticated`): en fake `gh` finnes, men `gh auth status` feiler —
  samme korrekte fallback.
- id 5 (`gh_mode=authenticated`): en fake `gh` finnes og lykkes — harnessen
  verifiserer at et ekte `gh pr comment --body-file`-kall faktisk ble fanget opp
  (ikke bare at outputen *påstår* posting), via en fake-gh-`comment-capture`-fil.

> **Ikke testet mot ekte GitHub:** fake-`gh`-en verifiserer at agenten kaller riktig
> `gh`-kommando med riktig argumenter i alle tre tilstander, men selve `gh pr
> comment`-kallet mot en ekte PR på github.com er fortsatt ikke kjørt live (ingen
> `gh`-CLI/root-tilgang i dette miljøet). Test selv på en maskin med ekte `gh`
> installert og innlogget før du stoler fullt på denne biten.

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
> modellen enten stopper med et unødvendig avklaringsspørsmål eller hevder å ha
> gjort en endring uten faktisk å ha kalt verktøyet. Dette er bekreftet
> modell-agnostisk: reprodusert med både `gpt-5.4` (falt tilbake til `auto`,
> brukt før `planlegger` ble pinnet) og med `claude-sonnet-4.6`/`claude-sonnet-5`
> i direkte A/B-testing (se CHANGELOG [0.4.1]/[0.4.2]). `planlegger` er nå
> pinnet til `claude-sonnet-4.6` for å unngå udokumentert `auto`-fallback, men
> det løser ikke denne kategorien flakiness — kun modellvalg-usikkerheten.
>
> **Løst (tidligere kjent flakiness):** scenario id 3 (persondata-stopp-punkt)
> viste tidligere samme mønster — sa i prosa at den stoppet (`NEEDS_DECISION`)
> men fortsatte å implementere likevel. Løst i [0.4.3] ved å gjøre
> `STOPPUNKT` til en eksplisitt hard grense i `planlegger.agent.md` (ingen
> verktøykall etter at `STOPPUNKT` er skrevet, fail-closed ved tvil, sjekk
> triggere før implementasjonsdetaljer). Verifisert 8/8 rene kjøringer etter
> endringen (mot tydelige brudd før). Følges opp om ny flakiness dukker opp.
>
> **Kjent flakiness (2):** for svært små mikro-endringer (se
> "Mikro-endring-unntak" i `planlegger.agent.md`) hender det ofte at planlegger
> feilaktig sier `Reviewer: hoppet over (ingen filendringer)` selv om
> `git diff` faktisk viser en endring. Flere runder med instruksjonsskjerping
> er forsøkt (eksplisitt "scope ≠ ingen endring", og en "hard sperre før
> FERDIG"-regel likt mønsteret som løste stopp-punkt-flakinessen) — ingen av
> dem ga en klar, målbar forbedring for dette spesifikke tilfellet (fortsatt
> ~1/5–2/3 feilrate i gjentatt testing). I motsetning til stopp-punkt-fiksen
> ser dette ut som en dypereliggende modell-tendens til å ta snarveier på
> trivielle oppgaver, ikke noe ren promptjustering løser. Bekreftet
> modell-agnostisk (`gpt-5.4`/`auto`, `claude-sonnet-4.6`, `claude-sonnet-5`).
> `eval_integration.py` sjekker nå (siden [0.5.1]) faktisk semantisk korrekthet
> via `expect_reviewer_verdict_if_changed` (sjekker ekte `git status` mot
> output), så denne testen fanger nå reelt opp problemet i stedet for å skjule
> det bak en tekst-substring-sjekk — det er selve fiksen i [0.5.1], ikke en
> løsning på flakinessen.

## Ekte PR-reviewer-test (scratch-repo)

Samme prinsipp som integrasjonstesten over, men for `pr-reviewer`. Siden
`pr-reviewer` skal være read-only, er hovedsjekken at `git diff` er **helt
uendret** før og etter kjøringen (ikke at bestemte filer endret seg):

```bash
python3 scripts/eval_pr_review.py --run
```

Dette:
- oppretter en scratch-repo med et `base_files`-innhold (committed)
- legger på `pr_files`-innhold **uten** å committe (simulerer PR-diffen som
  skal reviewes)
- tar en snapshot av `git diff` før agent-kjøring, kjører `pr-reviewer` med
  `--allow-all-tools`, og verifiserer at diffen er identisk etterpå (ingen
  filendringer) og at ingen ny commit ble gjort
- sjekker at sluttsvaret inneholder forventede nøkkelord (f.eks. et planta
  problem som skal flagges)

Suiten dekker tre scenarioer:
- `smoke` (id 1): en ren, uskyldig endring — bekrefter at agenten kjører og
  svarer i riktig format uten å krasje eller gjøre endringer.
- `policy` (id 2): en plantet feil (fødselsnummer logget i vanlig logg) —
  verifiserer at reviewen faktisk flagger det konkrete sikkerhetsproblemet.
- `smoke` (id 3): ber eksplisitt om PR-kommentar-posting uten at `gh` er
  tilgjengelig — verifiserer at opt-in-postingen faller korrekt tilbake til
  terminal-only med en tydelig forklaring, i stedet for å krasje eller late
  som noe ble postet.

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
python3 scripts/eval_pr_review.py --run
```
