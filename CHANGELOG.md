# Changelog

Alle nevneverdige endringer i denne pluginen dokumenteres her.
Format følger løst [Keep a Changelog](https://keepachangelog.com/), versjonsnummer i `plugin/plugin.json`.

## [0.15.0]

### Endret
- `sparring` avklarer nå problemet bak oppgaven, ønsket effekt,
  brukerverdi, antakelser og avgrensning. Den skiller teknisk leveranse fra
  ønsket effekt og gjør en kort vurdering av om foreslått løsning treffer
  problemet.
- Nytt `OPPGAVENOTAT` med feltene `Problem/observasjon`, `Mål`,
  `Gevinst/brukerverdi`, `Tegn på ønsket effekt`, `Foreslått løsning`,
  `Ikke mål`, `Antakelser og åpne spørsmål` og `Kort vurdering`.
- `planlegger` bruker de nye feltene direkte og behandler foreslått løsning
  som et innspill, ikke en bindende teknisk beslutning.
- La til kontraktstest og ekte scratch-repo-test for `sparring`.
- Oppdaterte agentmodellene fra utilgjengelige `claude-sonnet-4.6` til
  `claude-sonnet-5`.

## [0.14.1]

### Endret (dokumentasjon)
- README var blitt for lang (772 linjer) til å være en reell "kort oversikt".
  Delt i tre: `docs/agenter.md` (agent-/skill-detaljer, modellvalg,
  troubleshoot-sperren), `docs/testing.md` (eval-harnesser og CI-gate),
  `docs/installasjon.md` (installasjon og oppdatering). `README.md` er nå en
  kort tabell + lenker (~50 linjer).
- Oppdaterte interne kryssreferanser til flyttet innhold i
  `troubleshoot.agent.md`, `brukerdialog-create-skill/SKILL.md` og
  `scripts/eval_troubleshoot.py` (pekte tidligere til seksjoner i README som
  nå ligger i `docs/agenter.md`).

## [0.14.0]

### Lagt til
- Ny agent `sparring` (`user-invocable: true`, `disable-model-invocation: true`):
  avklarer mål, brukerverdi/gevinst, suksesskriterium og ikke-mål for **én**
  oppgave/idé av gangen, før den blir en plan. Bevisst smalere enn Grillmester
  sin `doctor-who`-agent — ingen prioritering på tvers av saker, ingen OKR,
  ingen team-status i v1.
- Stiller ett spørsmål om gangen, oppsummerer i et `OPPGAVENOTAT`, og spør
  eksplisitt om det skal sendes videre til `planlegger` via `Task` — samme
  ettretnings-delegasjonsmønster som `planlegger`→`koder`, med kun ett gyldig
  mål (unngår samme uforutsigbare agentvalg som ble avdekket i [0.13.0]).
- `planlegger` bruker nå feltene i et mottatt `OPPGAVENOTAT` direkte (ny
  "Mottak fra sparring"-seksjon) i stedet for å avklare mål/gevinst på nytt.
- `koder`: commit-meldinger skal nå ha en kort body-setning om *hvorfor*
  (mål/gevinst), ikke bare hva som ble endret, med mindre endringen er triviell.
- Diskutert, ikke bygget: en fremtidig kobling mot et team-board (f.eks.
  GitHub Projects) for prioritering på tvers av saker — utsatt til teamet har
  tatt stilling til det.

## [0.13.1]

### Endret (kvalitet)
- Presiserte kostnadsforskjellen mellom planreview og ad hoc rubber-ducking i
  `plugin/agents/planlegger.agent.md`. Planreview skjer i praksis sjelden (kun
  én gang per komplisert-sti-oppgave), så en tyngre/dyrere spesialisert
  arkitektur-agent (f.eks. brukerens egen `nav-pilot-opus`) er et akseptabelt
  valg der. Ad hoc rubber-ducking under koding/review kan derimot trigges
  flere ganger per oppgave og skal derfor **kun** bruke den lette innebygde
  `rubber-duck`-agenten, aldri en dyr spesialisert agent.
- **Ikke empirisk verifisert**: forsøkte å teste om denne kost-instruksen
  faktisk følges, men klarte ikke å fremtvinge et deterministisk scenario der
  planlegger trigger ad hoc rubber-ducking i det hele tatt — i testkjøringen
  svarte den direkte på en avklaringsoppgave uten noe `Task`-kall. Gitt at en
  tilsvarende "aldri X"-instruks for planreview allerede har vist seg å bli
  overstyrt to ganger ([0.13.0]), bør denne instruksen anses som uverifisert
  til den er testet i en ekte kjøring som faktisk trigger stien.

## [0.13.0]

### Endret (kvalitet)
- **`planreview` var en udefinert mekanisme.** Agent-filen sa bare "kjør
  planreview før delegasjon" uten å spesifisere hvordan. Verifisert empirisk:
  planlegger valgte selv en personlig egendefinert arkitektur-agent
  (`nav-pilot-opus`, tilgjengelig i denne brukerens lokale miljø) i stedet for
  noe pluginen faktisk kontrollerer eller garanterer. Ingen test verifiserte
  at et review i det hele tatt skjedde — kun at feltet
  `Krever planreview: ja/nei` ble satt riktig.
- Definerte planreview eksplisitt som et synkront `Task`-kall til en ekte
  review-agent (`rubber-duck` som standard), som skal vurdere både (1) om
  planen faktisk løser det oppgitte målet/gevinsten, og (2) om
  arkitekturen/tilnærmingen er sunn.
- **Verifisert at selv en eksplisitt "bruk aldri en personlig agent"-instruks
  ikke er nok**: planlegger valgte `nav-pilot-opus` på nytt i en ny testkjøring.
  Samme klasse begrensning som gjorde `--deny-tool` alene utilstrekkelig for
  `troubleshoot` ([0.11.0]) — det finnes ingen teknisk sperre for hvilken
  `agent_type` en agent-fil kan velge i et `Task`-kall. Justerte kravet til det
  som faktisk kan håndheves: et ekte delegert review-kall skjedde og et
  verdikt ble rapportert, ikke nøyaktig hvilken agent som gjorde det.
- Ny hard sperre "Planreview-steg" (speiler eksisterende "Reviewer-steg"):
  planlegger har ikke lov til å delegere til `koder` på komplisert sti før den
  har kalt en ekte review-agent og skrevet en `Planreview: <verdikt>`-linje.
- `scripts/eval_integration.py`: ny `expect_planreview_reported`-sjekk, samme
  prinsipp som `expect_reviewer_verdict_if_changed` — verifiserer at en
  `Planreview:`-linje faktisk finnes i sluttoutputen på komplisert sti, ikke
  bare at planen påsto at review skulle kjøres.

## [0.12.0]

### Endret (sikkerhet)
- **`gcloud` og `nais` var helt udekket av den tekniske sperren.** Begge ligger
  på samme `PATH` som `kubectl`, med de samme credentials-ene.
  `gcloud sql instances delete` kan gjøre langt større skade enn noe
  `kubectl delete`, og `nais app delete`/`nais postgres migrate` likeså. Sperren
  dekket kun `kubectl`.
- `scripts/kubectl-guard/` er omdøpt til `scripts/readonly-guard/` og har nå tre
  shims: `kubectl`, `gcloud` og `nais`. `scripts/test_kubectl_guard.sh` er
  tilsvarende omdøpt til `scripts/test_readonly_guard.sh`.
- **`gcloud`-shimen bruker allowlist, ikke denylist.** Kommandoflaten er for stor
  og endrer seg for ofte til at en denylist kan gjøres troverdig, så ukjente
  kommandoer blokkeres (fail-closed). `auth print-access-token` og
  `container clusters get-credentials` er eksplisitt blokkert — den første lekker
  credentials, den andre skriver til kubeconfig og bytter aktivt cluster.
- **`nais`-shimen bruker allowlist per kommandogruppe.** `nais secret` og
  `nais app env` er blokkert fordi de ville trukket hemmeligheter inn i agentens
  kontekst; `nais postgres` er kun tillatt for `list`.
- Prisen for allowlist er falske positive. Det er et bevisst valg: agenten sier
  fra hvilken kommando den ville kjørt, så kan du kjøre den selv.

### Testing
- `scripts/test_readonly_guard.sh` utvidet fra 31 til 87 deterministiske caser.
- Mutasjonstestet hver mekanisme for å bekrefte at den faktisk er load-bearing:
  - Deaktivert `gcloud`-shim → 14 caser feilet.
  - Deaktivert `nais`-shim → 17 caser feilet.
  - Fjernet `WRITE_VERBS`-sjekken i `gcloud` → **0 caser feilet.** Suiten testet
    altså ikke sjekken i det hele tatt. La til caser der et lese-verb opptrer som
    ressursnavn (`gcloud compute instances delete list`), som er nettopp klassen
    av bug den skal fange. Sjekken er nå load-bearing.
  - Fjernet flaggverdi-hoppingen i `nais` → 2 caser feilet
    (`nais -t teamdagpenger status` ble feilaktig blokkert).
  - Fjernet `DESTRUCTIVE_TOKENS`-sjekken i `nais` → 1 case feilet.
- `--help` slipper gjennom begge shimene, men avdekket et hull underveis:
  `nais app delete min-app --help` ville sluppet forbi allowlisten, siden
  hjelpemodus hopper over gruppesjekken. Tettet med en destruktiv-token-sjekk
  som gjelder også i hjelpemodus.

## [0.11.0]

### Endret (sikkerhet)
- **`troubleshoot`: `--deny-tool` viste seg utilstrekkelig som eneste tekniske
  sperre.** Verifisert empirisk at mønsteret `shell(kubectl <verb>:*)` kun
  matcher når verbet står som første token etter `kubectl`:
  `kubectl delete pod X -n ns` blokkeres, mens `kubectl -n ns delete pod X`
  kjørte helt gjennom. Wildcard-varianter (`shell(kubectl *delete*)`) tetter
  ikke hullet, siden matchingen er prefiks-basert på tokens. Lista manglet i
  tillegg flere muterende verb helt (`run`, `debug`, `attach`,
  `auth reconcile`).
- Ny primærsperre `scripts/kubectl-guard/kubectl`: en PATH-shim som parser
  argumentene selv og blokkerer destruktive verb uansett posisjon i
  kommandolinjen. Feiler lukket (blokkerer også hvis et destruktivt verb
  forekommer som eget token noe sted, som sikkerhetsnett mot parsefeil), med
  eksplisitt unntak for `kubectl auth can-i <verb>` som er en ren lesespørring.
  `troubleshoot-safe.sh` legger shimen først i `PATH` og avbryter hvis den
  mangler. `--deny-tool` beholdes som sekundært lag.
- Ny `scripts/test_kubectl_guard.sh`: deterministisk enhetstest av shimen (31
  caser), kjører uten modell/`copilot`-binary og er derfor koblet inn i CI.
  Nødvendig fordi agent-evalen **ikke** kan skille "shimen blokkerte" fra
  "modellen nektet selv" — verifisert at en bypass-testcase passerer også med
  shimen deaktivert.
- `eval/troubleshoot-tests.json`: tre nye policy-caser (id 5–7) med
  kommandoformer der verbet ikke står først, samt `debug`/`exec`.
  `eval_troubleshoot.py` legger nå shimen i `PATH`, slik at harnessen tester
  det samme oppsettet som launcheren faktisk bruker.
- README/`troubleshoot.agent.md`: korrigert formuleringer som overdrev
  garantien `--deny-tool` gir, og fjernet en selvmotsigelse der README ba deg
  velge `troubleshoot` i `/agent` selv om agenten er `user-invocable: false`.

## [0.10.9]

### Lagt til
- `planlegger`: eksplisitt "hvorfor/gevinst"-refleksjon i steg 1 av
  "Arbeidsmåte" — planlegger skal nå alltid formulere ikke bare *hva* som
  skal endres, men *hvorfor* (gevinsten/formålet), som en intern sjekk på at
  planen faktisk tjener formålet og ikke bare matcher den bokstavelige
  beskrivelsen. Nytt `Gevinst`-felt i `KODER_BRIEF` for komplisert sti
  (utelates ved enkel sti, for å unngå unødvendig friksjon på små/opplagte
  oppgaver). Blir kun et faktisk spørsmål til bruker hvis hvorfor er reelt
  uklart og ville endret løsningen — samme terskel som eksisterende
  avklarende-spørsmål-policy, ikke en ny.

## [0.10.8]

### Lagt til
- CI-guard for "discovery-budget": `scripts/validate_plugin_schema.py` summerer
  nå `name`+`description`-frontmatter på tvers av alle agent-/skill-filer
  (disse lastes alltid inn i modellens picker/discovery-kontekst, uansett om
  en gitt skill faktisk brukes i sesjonen) og feiler hvis summen passerer
  8 KiB. Kalibrert til å tillate om lag en tredobling av dagens faktiske bruk
  (~2,4 KB for 5 agenter + 12 skills) før det tvinger et bevisst valg
  (trimme tekst eller heve konstanten med vilje). Portert fra `grillmester`,
  som har en tilsvarende (men høyere) budsjettgrense for sitt langt større
  antall agenter/skills.
- `plugin/skills/brukerdialog-create-skill/SKILL.md`: ny meta-skill
  (`disable-model-invocation: true`, samme mønster som `brukerdialog-doctor`)
  som kodifiserer prosessen for å lage/revidere en av pluginens egne
  domain-preset-skills — gap-sjekk, design, registrering, empirisk
  validering via eval-skriptene, og CHANGELOG/versjonsoppdatering. Dekker
  også når man bør diagnostisere hvorfor en skill ikke trigges. Gjelder kun
  pluginens egne skills, ikke dokumentasjon/skills i target-repos (se
  "Repo-dokumentasjon" i `koder.agent.md`).
- `scripts/smoke_plugin_install.py`: ny lokal (ikke kjørt i CI, samme
  konvensjon som de andre live `eval_*`-skriptene som krever ekte
  `copilot`-binary) install-test som faktisk installerer pluginen i en
  isolert `$COPILOT_HOME` og verifiserer at `copilot plugin
  install`/`list` fungerer og viser forventet versjon — dekker en
  installasjons-livssyklus-gap som den rent skjema-baserte valideringen ikke
  kan fange opp. Portert og forenklet fra `grillmester`s tilsvarende skript.
- `reviewer`: presisert at reviewer ikke skal stole blindt på koder sin
  prosa-oppsummering av hva som ble gjort der den faktiske diffen er
  tilgjengelig — konkrete påstander skal verifiseres mot selve diffen, ikke
  bare beskrivelsen.

## [0.10.7]

### Lagt til
- `koder` (ny seksjon "Repo-dokumentasjon") og `planlegger` kan nå flagge —
  aldri fikse selv — hvis en endring gjør repoets egen dokumentasjon (README,
  AGENTS.md, CONTRIBUTING eller lignende) synlig utdatert. Bevisst begrenset
  til ren flagging: å opprette nye skills/dokumentasjon i et target-repo er en
  bevisst handling brukeren tar selv, ikke noe pluginen gjør uoppfordret eller
  automatisk (vurdert og avgrenset eksplisitt mot bredere automatisk
  skill-/dokumentasjonsvedlikehold i target-repos, som ble vurdert som for
  stor scope-utvidelse og delvis overlappende med CLI-ens egen
  `store_memory`-mekanisme).
- README: utvidet "Begrunnelse og læring"-seksjonen med denne avgrensningen.

## [0.10.6]

### Lagt til
- `koder` og `planlegger` kan nå forklare *hvorfor* en løsning ble valgt, uten
  å blåse opp hver sluttoppsummering:
  - Automatisk (minimalt): `koder`s rapportformat har fått et valgfritt
    `Nøkkelvalg`-felt som kun fylles ut når det faktisk var en ikke-opplagt
    avveining — utelates helt for mekaniske/rutinemessige oppgaver.
    `planlegger` tar dette videre i én kort setning, pluss egne
    arkitektur/tilnærming-valg på samme måte.
  - På forespørsel (grundig): begge agentene skal svare grundig og ærlig med
    konkrete alternativer og tradeoffs når brukeren spør om begrunnelse i
    etterkant (f.eks. "hvorfor gjorde du det sånn?"), i stedet for bare å
    gjenta hva som ble gjort.
  - Ny README-seksjon "Begrunnelse og læring" dokumenterer dette og kobler det
    til "generer-så-forstå"-mønsteret.

### Fikset
- `eval_integration.py` sin `expect_reviewer_verdict_if_changed`-sjekk feilet
  noen ganger fordi modellen skriver `**Reviewer:** APPROVED` (markdown fet
  skrift) i stedet for `Reviewer: APPROVED`, og en ren substring-sjekk fanget
  ikke opp det. Fjerner nå `*` før sammenligning. Verifisert 3/3 rene
  smoke-kjøringer etter fiksen (mot en observert feilkjøring før).

## [0.10.5]

### Lagt til
- Eval-scenario 24 i `eval/planlegger-tests.json`: isolerer spesifikt
  "programmatisk operasjon"-klausulen i mikro-endring-unntaket
  (versjonsnummer-oppdatering i én stor, generert fil med kolliderende
  verdier andre steder i fila). Erstatter ikke scenario 22 (som fortsatt er en
  gyldig regresjonssperre for den historiske bugen), men dekker et gap
  scenario 22 ikke traff: mutasjonstesting viste at å fjerne klausulen ikke
  påvirket scenario 22 (5/5 uendret utfall, siden splitting-i-flere-filer
  allerede er ekskludert av en annen, urelatert klausul), mens scenario 24
  faktisk flipper fra en klar `koder=ja`-majoritet (5/5) til inkonklusivt
  (2/5) ved samme mutasjon — bekrefter at scenario 24 isolerer riktig regel.
- `eval/koder-direct-tests.json` + ny bruk av `eval_integration.py --agent
  dp-brukerdialog-pilot:koder`: kjører `koder` direkte (uten `planlegger` i
  løpet) med en håndskrevet `KODER_BRIEF` der `Git-policy` er til stede men
  ikke nevner commit. Dekker et gap der både `eval_koder_brief.py` (tekst-only)
  og `eval_integration.py` sin normale bruk (alltid via `planlegger`) skjuler
  regresjoner i `koder` sin egen "ikke commit uten eksplisitt instruks"-regel,
  fordi `planlegger` alltid genererer et eksplisitt
  `Git-policy: auto-commit: nei`-felt uansett hva `koder.agent.md` sier.
  Bekreftet med mutasjonstesting: en eksplisitt positiv "kjør alltid
  `git commit`"-instruks flipper testen korrekt (ny commit oppdaget); en
  svakere "det er greit å committe"-mutasjon flipper den ikke (modellens egen
  forsiktighet uten imperativ er nok i praksis) — dokumentert som en kjent,
  akseptert begrensning i README.
- Begge nye tester lagt til i `.github/workflows/eval-harness.yml` sine
  statiske sjekker (schema-validering).
- README: ny seksjon "Ekte koder-direkte-test (commit-policy-isolasjon)".

## [0.10.4]

### Lagt til
- `plugin/skills/brukerdialog-bff-auth/SKILL.md`: nytt domain-preset for
  autentisering/token-utveksling i Next.js API-routes (BFF) — validering av
  innkommende token (`@navikt/oasis`) og OBO/TokenX-utveksling mot andre
  Nav-tjenester. Dekker et reelt gap: `brukerdialog-frontend-aksel` dekker kun
  UI-komponenter, og backend-siden av TokenX var kun dekket av den personlige
  `tokenx-auth`-skillen (Kotlin-fokusert, ikke Next.js/BFF).
  - Trigger: token-validering/-utveksling i en Next.js API-route/route handler.
  - Default: `Sti=enkel` for ny route i etablert valideringsmønster,
    `Sti=komplisert`/`Krever planreview=ja` for nytt audience/ny
    nedstrøms-tjeneste eller bytte av tokentype.
  - Obligatoriske brief-felt: token-kilde, målsystem+audience-format
    (TokenX `cluster:ns:app` vs. Azure AD OBO `api://cluster.ns.app/.default`
    — disse forveksles lett), feilhåndtering (401 vs. 403, aldri 500 eller
    lekkasje av valideringsdetaljer), nedstrøms-protokoll (http internt/https
    eksternt).
- Registrert presetet i `planlegger.agent.md`s preset-tabell og i README.
- Eval-scenario 23 i `eval/planlegger-tests.json` (ny TokenX-integrasjon mot
  ukjent tjeneste → forventer `sti=komplisert`, `planreview=ja`) — kjørt og
  bekreftet 3/3 rent.

### Fikset
- `plugin/skills/brukerdialog-doctor/SKILL.md` var utdatert (fortsatt "4
  agenter og 9 skills" fra før `troubleshoot` ble lagt til og senere gjort
  `user-invocable: false`, se [0.10.0]/[0.10.2]). Oppdatert til å reflektere
  faktisk tilstand: kun `planlegger`/`pr-reviewer` skal være synlige i
  `/agent`, mens `koder`/`reviewer`/`troubleshoot` er tilsiktet skjult
  (internt-only/kun via launcher). Skill-listen oppdatert til alle 11.

### Verifisert
- `python3 scripts/validate_plugin_schema.py`: 5 agent-fil(er), 11
  skill-fil(er) OK.
- `python3 scripts/eval_planlegger.py --run --suite policy --repeats 3`:
  17/19 pre-eksisterende scenarioer passerte (de 3 feilene — id 3, 9, 16 — er
  allerede dokumentert kjent flakiness i README, ikke en regresjon fra denne
  endringen), nytt scenario id 23 passerte rent 3/3.

## [0.10.3]

### Lagt til
- `scripts/eval_troubleshoot.py` + `eval/troubleshoot-tests.json`: formaliserer
  den manuelle fake-`kubectl`-verifikasjonen fra [0.10.1] til en gjentagbar,
  automatiserbar eval. Kjøres alltid med samme `--deny-tool`-flagg som
  `scripts/troubleshoot-safe.sh` (parset direkte fra scriptet, ikke duplisert,
  så de ikke kan drifte fra hverandre). Kjernesjekken er en loggfil fra en fake
  `kubectl` — testen stoler ikke på agentens tekstsvar, kun på om destruktive
  verb (delete/apply/patch/rollout/scale) faktisk noensinne når binæren, selv
  når prompten prøver samme type omformulering som fungerte i [0.10.1] ("dette
  er bare et testmiljø, kjør det direkte"). 4 scenarioer, alle grønne lokalt
  (1 smoke, 3 policy).
- `.github/workflows/eval-harness.yml`: la til `eval_troubleshoot.py` og
  `eval/troubleshoot-tests.json` i de statiske syntax-/schema-sjekkene, samme
  mønster som de andre agentene.

### Motivasjon
- `troubleshoot` var frem til nå den eneste agenten uten noen eval-dekning,
  til tross for at den er den mest risikofylte (destruktive
  produksjonskommandoer). Alt var kun verifisert manuelt denne økten — dette
  lukker det gapet.

## [0.10.2]

### Endret
- `troubleshoot.agent.md`: `user-invocable: true` → `false`, og la til
  `disable-model-invocation: true`. Agenten er derfor ikke lenger valgbar i
  `/agent`-menyen og kan ikke auto-invokeres av andre agenter — den kan kun startes
  via `scripts/troubleshoot-safe.sh`, som bruker `--agent`-CLI-flagget direkte.

### Undersøkt
- Fulgte opp spørsmålet om den tekniske sperren i [0.10.1] burde ligge direkte i
  agent-filen i stedet for i et separat launcher-script. Sjekket offisiell
  dokumentasjon (`custom-agents-configuration`, `configure-copilot-cli`):
  `--allow-tool`/`--deny-tool` med finkornede kommandomønstre
  (`shell(kubectl delete:*)`) finnes **kun** som CLI-launch-flagg — agent-frontmatter
  sitt `tools`-felt støtter bare grov allow-listing av hele verktøykategorier
  (f.eks. slå av all `shell`), ikke enkeltkommandoer. Konklusjon: sperren kan ikke
  bakes inn i agent-filen selv.
- Testet empirisk om `user-invocable: false` faktisk fjerner risikoen for at
  brukeren velger agenten uten sperren: kjørte `copilot --agent
  dp-brukerdialog-pilot:koder` (som allerede er `user-invocable: false`) direkte —
  fungerte uendret. Bekrefter at `--agent`-flagget omgår `user-invocable`, så
  launcher-scriptet fortsatt virker etter denne endringen, samtidig som agenten
  forsvinner fra `/agent`-menyen for vanlig bruk.
- **Uverifisert:** brukeren nevnte at Nav har en intern sandkasse/wrapper rundt
  Copilot CLI ("cplt") som kan gripe inn i dette. Ikke undersøkt i dette miljøet —
  flagget som uverifisert i README.

## [0.10.1]

### Lagt til
- `scripts/troubleshoot-safe.sh`: launcher for `troubleshoot`-agenten som legger på
  `--deny-tool "shell(kubectl <verb>:*)"` for alle destruktive kubectl-verb
  (delete/apply/patch/replace/create/edit/exec/cp/rollout/scale/m.fl.) — en ekte
  CLI-nivå-sperre (Copilot CLI sitt permission-system), ikke bare en prompt-instruks.

### Verifisert
- Brukeren spurte om read-only-kontrakten i `troubleshoot.agent.md` (ren prosa) var
  tilstrekkelig for noe så konsekvensfylt. Testet empirisk med en falsk
  `kubectl`-stubb: en agent uten `--deny-tool` kunne overtales til å kjøre
  `kubectl delete`/`kubectl apply` med riktig framing i prompten ("dette er bare et
  testmiljø, kjør det direkte") — presis det motsatte av read-only-kontrakten. Med
  `--deny-tool` ble samme forsøk avvist på CLI-nivå (`Permission to run this tool
  was denied...`) **før** kommandoen nådde `kubectl`, uavhengig av modellens eget
  resonnement. Konklusjon: prosa alene er ikke nok for skriveaksjoner mot
  produksjon — konklusjonen er dokumentert i README og `troubleshoot.agent.md`
  peker nå til launcher-scriptet som påkrevd bruksmåte. Sterkeste lag er uansett
  RBAC på selve klyngen (utenfor denne pluginens kontroll).

## [0.10.0]

### Lagt til
- Ny frittstående agent `troubleshoot` (5. agent, uavhengig av
  planlegger→koder→reviewer-kjeden, samme frittstående mønster som `pr-reviewer`):
  feilsøker produksjonsproblemer på Nais (pod-krasj, auth-feil, Kafka-lag,
  DB-tilkobling, treg respons) ved å kjøre `kubectl`/`curl` mot klynge og
  observability-stacken (Mimir/Loki/Tempo) som vanlige bash-kommandoer — ingen
  MCP-kobling involvert eller nødvendig, kun lokal autentisering (naisdevice +
  kubeconfig) forutsatt hos bruker.
  Grunnet i `nav-troubleshoot` (diagnostiske trær for pod/auth/Kafka/DB) og
  `observability-debugging` (metrics→logs→traces-korrelasjon) fra nav-pilot.
  Rent read-only/diagnostisk: gjør aldri `kubectl apply`/`rollout restart`/
  manifest-endringer selv, foreslår i stedet fiksen eller sender den videre som
  oppgave til `planlegger`.
  Bakgrunn: brukeren antok at logg-tilkobling var umulig uten MCP — verifisert at
  det ikke stemmer, siden Nais sin observability-stack er tilgjengelig via vanlig
  `kubectl`/`curl` gitt at brukeren selv er lokalt autentisert.

### Ikke verifisert
- Selve `kubectl`/Mimir/Loki-kallene er ikke kjørt live mot en ekte Nais-klynge fra
  denne pluginens side (ingen klyngetilgang i utviklingsmiljøet). Verifiser selv
  ved første reelle bruk.

## [0.9.2]

### Lagt til
- `planlegger` gjenkjenner nå spørrende formuleringer i oppgaveteksten
  ("kanskje vi skal...", "blir det ikke for mye plass da?") som brukerens egen
  usikkerhet og ønske om reell vurdering — ikke bare en indirekte instruks.
  Skal svare med en ekte, kort vurdering (fordel/ulempe, egen mening) som del
  av responsen, ikke bare implementere stille. Dette er **ikke** et nytt
  stopp-punkt eller `ask_user`-trigger — vurderingen gis i teksten, arbeidet
  fortsetter i samme tur.
  Bakgrunn: brukerens egen kommunikasjonsstil legger ofte inn usikre forslag i
  spørreform under en økt, og ønsket faktisk motspill/vurdering, ikke bare
  stille utførelse.
  Merk: dette er en kvalitativ atferdsregel som ikke fanges av den strukturerte
  JSON-baserte policy-evalen (`eval_planlegger.py` tester kun
  {sti, planreview, koder, spørsmål}-feltene) — ingen ny automatisert
  testdekning for denne, kun manuell verifisering ved bruk.

## [0.9.1]

### Rettet
- **Mikro-endring-unntaket** tillot feilaktig at `planlegger` selv utførte en
  "konseptuelt enkel" refaktorering (flytte en HTML-template-literal til egen fil)
  fordi sti=enkel og ingen sikkerhetstrigger var involvert. I praksis krevde det et
  skriptet søk/erstatt-forsøk som korrumperte importer i `server.mjs` (måtte
  `git checkout` og re-applisere to bugfixer manuelt) før et nytt forsøk lyktes.
  Bakgrunn: reell tilbakemelding fra en `planlegger`-sesjon i `dp-brukerdialog-frontend`.
  Lagt til et eksplisitt kriterium: unntaket gjelder ikke hvis gjennomføringen krever
  strengmanipulering/filparsing/regex/filsplitting — kun rene `edit`/`create`-erstatninger.
  Slike refaktoreringer skal alltid til `koder`, uansett hvor enkelt målet virker.
- Ny eval-scenario (id 22) som dekker nettopp denne casen: fil-splitting via
  skript skal gi `koder=ja`, ikke selvutført mikro-endring.

## [0.9.0]

### Lagt til
- `brukerdialog-doctor`: read-only audit-skill (`disable-model-invocation: true`,
  trigges aldri automatisk) som verifiserer at plugin/agenter/9 skills faktisk er
  synlige i sesjonen (`copilot plugin list`, `/agent`, `copilot skill list`), og
  flagger eksakte navnekollisjoner mot andre installerte skills. Skalert ned
  versjon av `grillmester-doctor`-mønsteret (samme idé: prefiks alene løser ikke
  faglig overlapp, så en egen audit-skill gjør overlapp synlig i stedet for å late
  som det ikke finnes).
- README: ny "Diagnostikk"-seksjon, og en forklaring av *hvorfor* alle skills er
  prefikset — bekreftet empirisk denne sesjonen at Copilot CLI (v1.0.80) slår
  sammen skills fra personal/plugin/prosjekt/builtin til én flat liste uten
  automatisk namespacing, så prefikset er reell kollisjonsbeskyttelse, ikke bare
  kosmetikk.

## [0.8.0]

### Lagt til
- 3 nye domain-preset-skills, forankret i etablerte nav-pilot-skills (samme mønster
  som [0.6.1] brukte for `frontend-aksel`/`testrammeverk`/`nais-deploy`):
  - `brukerdialog-kotlin-ktor`: Ktor-ruter, Rapids & Rivers, repository-kode og
    DI-oppsett. Basert på `ktor-scaffold`/`kotlin-app-config` — extension functions
    på `Application`, Kotliquery fremfor JPA, konstruktørinjeksjon som default
    (Koin kun hvis prosjektet allerede bruker det), advarsel om `ThreadLocal`
    +coroutines i transaksjonsblokker.
  - `brukerdialog-observability`: metrikker, tracing og health-endepunkter. Basert
    på `observability-setup` — `/isready` skal faktisk sjekke avhengigheter (503,
    ikke krasj), strukturert logging med `kv(...)`, ingen persondata i metrikk-tags.
  - `brukerdialog-security-owasp`: tilgangskontroll/IDOR, injeksjon, CORS,
    dependency-pinning og kryptografi utover det `brukerdialog-persondata` og
    auth-stopp-punktet allerede dekker. Basert på `security-owasp` (OWASP
    Top 10:2025) — eierskapssjekk ved `{id}`-basert tilgang, parameteriserte
    spørringer, CORS aldri `anyHost()`.
- Oppdatert `planlegger.agent.md`s skill-referansetabell og README.
- 5 nye policy-scenarier i `eval/planlegger-tests.json` (id 17-21), alle grønne
  (18/18 policy-suite totalt).

Plugin har nå 9 skills totalt.

## [0.7.0]

### Lagt til
- `scripts/eval_pr_review.py`: en portabel **fake `gh`-binær** for
  `pr-reviewer`s gh-fallback-tester, i stedet for å stole på at dette
  miljøet tilfeldigvis mangler `gh`. Tre `gh_mode`-varianter kan settes per
  testcase:
  - `absent`: PATH saneres for et ekte `gh` (fjerner enhver PATH-mappe med en
    kjørbar `gh`), så testen oppfører seg likt uansett om maskinen som kjører
    harnessen faktisk har `gh` installert.
  - `unauthenticated`: en fake `gh` finnes, men `gh auth status` feiler.
  - `authenticated`: en fake `gh` finnes og lykkes — `gh pr comment
    --body-file` fanges opp i en egen fil, slik at testen kan verifisere at
    posting **faktisk** skjedde, ikke bare at agentens tekst påstår det (samme
    prinsipp som `expect_reviewer_verdict_if_changed` i [0.5.1]).
- Nye `expect_posted`/`pr_number`/`gh_mode`-felt i `eval/pr-reviewer-tests.json`.
  Scenario id 3 (tidligere "ingen PR-nummer nevnt i det hele tatt", som aldri
  faktisk testet gh-fallback-stien) er erstattet med et scenario som nevner et
  konkret PR-nummer og `gh_mode=absent` — dette tester nå faktisk stien den
  påstod å teste. Nye scenarier id 4 (`unauthenticated`) og id 5
  (`authenticated`, med verifisert ekte posting-forsøk) er lagt til.
- Kjørt: id 3/4/5 alle grønne, inkl. verifisert at fake-`gh` faktisk mottok et
  `gh pr comment`-kall i id 5.

### Kjent begrensning (uendret)
- Fake-`gh`-en verifiserer at agenten kaller riktig `gh`-kommando i riktig
  situasjon, men selve kallet mot en ekte GitHub-PR er fortsatt ikke kjørt
  live (ingen `gh`-CLI/root-tilgang i dette miljøet).

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
