#!/bin/bash
# Launcher for the `troubleshoot`-agenten med en EKTE teknisk sperre mot
# destruktive kubectl-verb, i tillegg til den prosa-baserte "read-only
# kontrakt" i plugin/agents/troubleshoot.agent.md.
#
# Hvorfor dette finnes: prosa-instruksjoner alene er IKKE tilstrekkelig for noe
# så konsekvensfylt som produksjonsendringer. Verifisert empirisk (se
# CHANGELOG [0.10.1]) at en agent uten disse flaggene kan overtales til å kjøre
# "kubectl delete"/"kubectl apply" med riktig framing i prompten, mens
# `--deny-tool` blokkerer kallet på CLI-nivå før det når kubectl i det hele
# tatt - uavhengig av hva modellen "bestemmer seg for".
#
# Bruk:
#   ./scripts/troubleshoot-safe.sh
#   ./scripts/troubleshoot-safe.sh -p "Appen min krasjer i dev-gcp, namespace teamdagpenger"
#
# Alle ekstra argumenter sendes videre til `copilot` uendret.

set -euo pipefail

DENY_VERBS=(
	delete apply patch replace create edit exec cp
	annotate label taint cordon uncordon drain autoscale expose set rollout scale
)

DENY_FLAGS=()
for verb in "${DENY_VERBS[@]}"; do
	DENY_FLAGS+=(--deny-tool "shell(kubectl ${verb}:*)")
done

exec copilot --agent dp-brukerdialog-pilot:troubleshoot "${DENY_FLAGS[@]}" "$@"
