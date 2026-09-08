#!/bin/bash
# Launcher for `troubleshoot`-agenten med to lag teknisk sperre mot destruktive
# kommandoer, i tillegg til den prosa-baserte "read-only kontrakt" i
# plugin/agents/troubleshoot.agent.md.
#
# Hvorfor dette finnes: prosa-instruksjoner alene er IKKE tilstrekkelig for noe
# så konsekvensfylt som produksjonsendringer. Verifisert empirisk (se
# CHANGELOG [0.10.1]) at en agent uten teknisk sperre kan overtales til å kjøre
# "kubectl delete"/"kubectl apply" med riktig framing i prompten.
#
# Lag 1 - readonly-guard (scripts/readonly-guard/), primærsperren:
#   PATH-shims for `kubectl`, `gcloud` og `nais` som parser argumentene og
#   blokkerer destruktive kommandoer uansett hvor i kommandolinjen de står.
#   kubectl bruker denylist over destruktive verb; gcloud og nais bruker
#   allowlist, fordi kommandoflatene deres er for store og for bevegelige til
#   at en denylist kan gjøres troverdig.
#
# Lag 2 - `--deny-tool`, sekundært:
#   blokkerer på CLI-nivå før kallet når shimen, men KUN når verbet står som
#   første token etter `kubectl`. Verifisert empirisk (CHANGELOG [0.11.0]):
#     kubectl delete pod X -n ns   -> blokkert av --deny-tool
#     kubectl -n ns delete pod X   -> IKKE blokkert (mønsteret matcher ikke)
#   Wildcards ("shell(kubectl *delete*)") hjelper ikke; matchingen er
#   prefiks-basert på tokens. Derfor er --deny-tool alene utilstrekkelig, og
#   beholdes kun som ekstra dybde for den enkleste kommandoformen.
#
# Ingen av lagene erstatter RBAC på klyngen: en kubeconfig med kun lesetilgang
# er den eneste beskyttelsen som gjelder uansett verktøy og prosess.
#
# Bruk:
#   ./scripts/troubleshoot-safe.sh
#   ./scripts/troubleshoot-safe.sh -p "Appen min krasjer i dev-gcp, namespace teamdagpenger"
#
# Alle ekstra argumenter sendes videre til `copilot` uendret.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARD_DIR="$SCRIPT_DIR/readonly-guard"

for shim in kubectl gcloud nais; do
	if [[ ! -x "$GUARD_DIR/$shim" ]]; then
		echo "FEIL: fant ikke $GUARD_DIR/$shim (readonly-guard-shimen)." >&2
		echo "Uten den er sperren mot destruktive kommandoer vesentlig svakere." >&2
		exit 1
	fi
done

DENY_VERBS=(
	delete apply patch replace create edit exec cp
	annotate label taint cordon uncordon drain autoscale expose set rollout scale
)

DENY_FLAGS=()
for verb in "${DENY_VERBS[@]}"; do
	DENY_FLAGS+=(--deny-tool "shell(kubectl ${verb}:*)")
done

# Shimene legges FØRST i PATH slik at alle kall fra agenten går gjennom dem,
# uansett hvordan kommandolinjen er satt sammen.
export PATH="$GUARD_DIR:$PATH"

exec copilot --agent dp-brukerdialog-pilot:troubleshoot "${DENY_FLAGS[@]}" "$@"
