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

Dette er bevisst for å holde pluginen liten og enkel å bygge videre på.
