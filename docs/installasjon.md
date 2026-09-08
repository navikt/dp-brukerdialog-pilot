# Installasjon

Se [README](../README.md) for kort oversikt over pluginen.

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

Etter en versjonsbump (eller når du er usikker på om manifestene faktisk er
installerbare, ikke bare schema-gyldige) kan du kjøre en ekte install-test i
en isolert `$COPILOT_HOME` — den rører aldri din faktiske installasjon:

```bash
python3 scripts/smoke_plugin_install.py
```

Dette dekker et gap `validate_plugin_schema.py` ikke kan: at schema-gyldig
JSON faktisk composerer til noe `copilot plugin install` aksepterer, og at
`copilot plugin list` etterpå rapporterer riktig versjon. Krever den ekte
`copilot`-binæren i `PATH`, så den kjøres lokalt (som de andre
live-CLI-testene), ikke i CI.

