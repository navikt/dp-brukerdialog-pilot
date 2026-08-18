# dp-brukerdialog-pilot

En enkel AI-pilot/orkestrator som **ren Copilot-plugin** med to agenter:
- `orkestrator` (synlig for bruker)
- `koder` (intern, delegert av orkestrator)

## Copilot-plugin-struktur

Plugin-filer:

```text
package-manifest.json
plugin/plugin.json
plugin/agents/orkestrator.agent.md
plugin/agents/koder.agent.md
```

Målet i første versjon er en bevisst liten plugin med:
- 1 orkestrator-agent som delegerer
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

Du skal kun se `orkestrator` som bruker-valg.

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
