# Changelog

Alle nevneverdige endringer i denne pluginen dokumenteres her.
Format følger løst [Keep a Changelog](https://keepachangelog.com/), versjonsnummer i `plugin/plugin.json`.

## [0.6.1]

### Endret
- Omdøpt alle 6 skills med `brukerdialog-`-prefiks (`brukerdialog-api-kafka`,
  `brukerdialog-db-migrasjon`, `brukerdialog-persondata`,
  `brukerdialog-frontend-aksel`, `brukerdialog-testrammeverk`,
  `brukerdialog-nais-deploy`) — samme konvensjon som `grillmester`-pluginen bruker
  for å unngå kollisjon med andre installerte skills. Oppdatert `name`-felt i
  frontmatter, mappenavn og alle referanser i `planlegger.agent.md`/README.
- Styrket innholdet i de 3 nye skillene (`frontend-aksel`, `testrammeverk`,
  `nais-deploy`), som i [0.6.0] var skrevet fra bunnen uten forankring i noe
  eksisterende. De er nå basert på de etablerte, mer utfyllende skillene
  `aksel-builder`, `playwright-testing` og `nais` (MCP-first-regel for Aksel,
  page object/locator-strategi for Playwright, accessPolicy-deny-all/pod-
  lifecycle-detaljer for Nais), kondensert til `planlegger`s korte preset-format.

## [0.6.0]

### Lagt til
- 3 nye domain-preset-skills, samme mønster som `api-kafka`/`db-migrasjon`/`persondata`:
  - `frontend-aksel`: UI-komponenter med Aksel Design System (@navikt/ds-react).
    Enkel sti for isolerte komponent-tillegg i etablert mønster, komplisert sti
    for nye sider eller bred layout/tema-endring.
  - `testrammeverk`: innføring av nytt testrammeverk/CI-testoppsett (Vitest,
    Playwright, Kotest, Testcontainers) — skiller eksplisitt fra å legge til én
    enkelt test i et allerede fungerende oppsett (fortsatt enkel sti).
  - `nais-deploy`: endringer i Nais-manifest, deploy-workflow eller GCP-ressurser.
    Faller allerede inn under det eksisterende infra/secrets-stopp-punktet, så
    skillen legger primært til obligatoriske brief-felt (accessPolicy-diff,
    miljøscope, rollback-plan) fremfor å endre sti/planreview-defaultene.
- Oppdatert `planlegger.agent.md`s skill-referansetabell med trigger og default
  sti/planreview for alle tre nye skills.
- README oppdatert med de nye skillene i "Domain-preset-skills" og innledningen.

## [0.5.1]

### Endret
- Fikset en reell svakhet i `eval_integration.py`: scenario id 4 sjekket
  tidligere kun at teksten `Reviewer:` fantes i output, ikke om verdikten var
  semantisk riktig. Ny assertion `expect_reviewer_verdict_if_changed` sjekker
  nå faktisk `git status` mot output — feiler hvis filer reelt sett ble
  endret men output likevel hevder `Reviewer: hoppet over` uten et ekte
  `APPROVED`/`NEEDS_CHANGES`/`BLOCKED`-verdikt.
- Denne fiksen avdekket at mikro-endring-reviewer-bugen (kjent siden [0.4.1])
  faktisk skjer oftere enn tidligere antatt — tidligere passerte testen alltid
  fordi den kun sjekket tekst-substring.
- Forsøkte en tredje runde med instruksjonsskjerping i `planlegger.agent.md`
  ("hard sperre før FERDIG", samme mønster som løste stopp-punkt-flakinessen
  i [0.4.3]) — ga **ingen** klar, målbar forbedring for dette spesifikke
  tilfellet (fortsatt betydelig feilrate i gjentatt testing). Beholdt
  endringen likevel (ufarlig, kan gi marginal effekt), men dokumentert
  ærlig i README at problemet ikke er løst av ren promptjustering denne
  gangen — trolig en dypereliggende modell-tendens til snarveier på
  trivielle oppgaver.

## [0.5.0]

### Lagt til
- `pr-reviewer` kan nå (opt-in) poste reviewen som en ekte PR-kommentar via
  `gh pr comment <nr> --body-file <fil>`, istedenfor kun terminal-output.
  Dette er det eneste unntaket fra den ellers strenge read-only-kontrakten.
- Posting skjer **kun** når alle tre er sanne: (1) bruker ber eksplisitt om det
  i samme oppgave, (2) et konkret PR-nummer er kjent (kun via `gh pr diff <nr>`,
  ikke generisk `git diff`), og (3) `gh`-CLI er installert og autentisert
  (`gh auth status`). Mangler ett av disse, forsøkes ikke posting — agenten
  forklarer konkret hvorfor i rapportens nye `Kommentar-posting`-linje og
  faller tilbake til vanlig terminal-only-oppførsel.
- Ny eval-scenario (`eval/pr-reviewer-tests.json` id 3) som ber om posting uten
  at `gh` er tilgjengelig — verifiserer at fallback-oppførselen faktisk
  fungerer (ingen krasj, ingen falsk positiv "postet"-melding). Manuelt
  inspisert: output er semantisk korrekt, ikke bare tekst-match.

### Kjent begrensning
- Selve `gh pr comment`-kallet (den ekte postingen til GitHub) er **ikke
  testet live** i dette miljøet — `gh`-CLI kan ikke installeres her (ingen
  root/sudo-tilgang). Implementert etter `gh`s dokumenterte grensesnitt, men
  bør verifiseres på en maskin med `gh` installert og innlogget.

## [0.4.3]

### Endret
- Styrket stopp-punkt-håndhevelsen i `planlegger.agent.md`: sikkerhetstriggere
  (database, auth, persondata, secrets/infra) sjekkes nå **først**, før
  implementasjonsdetaljer vurderes. `STOPPUNKT` er gjort til en eksplisitt
  hard grense — planlegger skal ikke kalle noe verktøy (edit/create/task/bash)
  etter at `STOPPUNKT` er skrevet i samme tur, og fail-closed gjelder ved tvil.
  Lagt til eksplisitt regel for å oppdage og avbryte midt i en implementasjon
  hvis et stopp-punkt-tema dukker opp for sent.
- Årsak: scenario id 3 (persondata-stopp-punkt) i `eval_integration.py` viste
  gjentatte ganger at planlegger kunne si i prosa at den stoppet
  (`NEEDS_DECISION`) men likevel fortsette å implementere endringen —
  bekreftet modell-agnostisk (samme feilrate på `gpt-5.4`/`auto` og
  `claude-sonnet-4.6`).
- Verifisert: 8/8 rene kjøringer av scenario id 3 etter endringen (mot
  gjentatte brudd før). README oppdatert til å markere id 3 som løst.

## [0.4.2]

### Endret
- Pinnet `planlegger` og `pr-reviewer` til `claude-sonnet-4.6` istedenfor
  `gpt-5.4` (som ikke er tilgjengelig i dette miljøet og ga udokumentert,
  varierende `auto`-fallback med varselmelding). En fast, verifisert
  tilgjengelig modell er bedre praksis enn `auto`, selv om modellbytte alene
  ikke fikser den kjente instruksjons-flakinessen (se [0.4.1]).
- Fant og dokumenterte enda et tilfelle av samme flakiness-mønster: scenario
  id 3 (persondata-stopp-punkt) kan av og til si i prosa at den stopper
  (`NEEDS_DECISION`) men likevel fortsette å implementere endringen.
  Bekreftet modell-agnostisk via direkte A/B-test (`gpt-5.4`/`auto` vs.
  `claude-sonnet-4.6`) — samme feilrate på begge. Dokumentert i README som
  utvidelse av eksisterende "Kjent flakiness"-note.

## [0.4.1]

### Endret
- Undersøkte om `planlegger`/`pr-reviewer`s modell (`gpt-5.4`, ikke tilgjengelig i
  dette miljøet, faller tilbake til `auto`) var årsaken til dokumentert flakiness.
  Testet `claude-sonnet-4.6` og `claude-sonnet-5` som erstatning — konklusjon:
  **modellbytte løste ikke problemet** og introduserte i ett tilfelle uleselig
  tekst (modell-glitch). Beholdt derfor `gpt-5.4` uendret.
- Fant og fikset en reell logikkfeil underveis: `planlegger` hoppet iblant over
  formell delegering til `koder` for trivielle 1-fils-endringer og redigerte
  filen selv, men rapporterte deretter feilaktig `Reviewer: hoppet over (ingen
  filendringer)` selv når filen faktisk var endret. Dette skjedde uavhengig av
  modell.
- Formaliserte dette som et eksplisitt, avgrenset unntak i
  `planlegger.agent.md` ("Mikro-endring-unntak"): kun på enkel sti, kun for
  mekaniske få-linjers endringer uten sikkerhetstriggere, og alltid med samme
  brief- og reviewer-plikt som ved delegering til `koder`.
- Reviewer-triggeren er nå basert på faktisk `git status`/`git diff`, ikke bare
  `koder`s returstatus, og instruksjonene presiserer eksplisitt at "endring
  innenfor scope" ikke er det samme som "ingen endring".
- Dette reduserte feilraten merkbart i manuell testing, men eliminerte den ikke
  helt — dokumentert som ny "Kjent flakiness"-note i README, samme kategori som
  den eksisterende for scenario id 2.

## [0.4.0]

### Lagt til
- Ny bruker-invokerbar agent `pr-reviewer` (`plugin/agents/pr-reviewer.agent.md`,
  modell `gpt-5.4`) — frittstående fra `planlegger`→`koder`→`reviewer`-kjeden.
  Brukes til å reviewe **andres** PR-er/branches på forespørsel, i motsetning
  til den interne `reviewer` som kun sjekker vårt eget arbeid i én økt.
- Diff-strategi: `gh pr diff <nr>` hvis PR-nummer oppgis og `gh`-CLI er
  tilgjengelig/autentisert, ellers `git diff` mot detektert default-branch
  eller oppgitt branch (inkl. uncommittede endringer). MCP (f.eks. IntelliJ
  sin PR-integrasjon) kan berike konteksten, men er aldri en forutsetning —
  samme prinsipp som `planlegger`s eksisterende MCP-policy.
- `pr-reviewer` er read-only: gjør aldri filendringer/commits, og poster ikke
  PR-kommentarer (bevisst utsatt til senere). Skriver kun ut en strukturert
  review i terminalen (sikkerhetskritisk / infrastruktur / kodekvalitet) og
  flagger for et menneske — blokkerer aldri.
- Ny eval `scripts/eval_pr_review.py` + `eval/pr-reviewer-tests.json` (2
  scenarier: ren endring, og et plantet sikkerhetsproblem som må flagges).
  Kjerneassertion: `git diff` er identisk før/etter kjøring (read-only-kravet
  verifisert direkte, ikke bare antatt).

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
