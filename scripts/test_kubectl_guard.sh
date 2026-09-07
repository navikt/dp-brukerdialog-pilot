#!/usr/bin/env bash
# Deterministisk enhetstest av scripts/kubectl-guard/kubectl.
#
# HVORFOR DENNE FINNES I TILLEGG TIL eval_troubleshoot.py:
# Agent-evalen kjører en ekte modell og kan ikke skille mellom "shimen
# blokkerte kallet" og "modellen nektet av seg selv". Verifisert empirisk: en
# testcase med "kubectl -n ns delete pod X" passerer også når shimen er
# deaktivert, fordi prosa-kontrakten i agent-filen holdt i den kjøringen.
# Den sier altså ingenting om at den tekniske sperren faktisk virker.
#
# Denne testen kjører shimen direkte, uten modell: rask, deterministisk, og
# krever ingen `copilot`-binary eller auth (kan derfor kjøres i CI).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUARD_DIR="$REPO_ROOT/scripts/kubectl-guard"

FAKE_REAL_DIR="$(mktemp -d)"
cat >"$FAKE_REAL_DIR/kubectl" <<'EOS'
#!/usr/bin/env bash
echo "PASSTHROUGH: $*"
exit 0
EOS
chmod +x "$FAKE_REAL_DIR/kubectl"

cleanup() { rm -rf "$FAKE_REAL_DIR"; }
trap cleanup EXIT

export PATH="$GUARD_DIR:$FAKE_REAL_DIR:$PATH"

passed=0
failed=0

expect_allowed() {
	local output
	output="$(kubectl "$@" 2>&1)"
	if [[ "$output" == PASSTHROUGH:* ]]; then
		passed=$((passed + 1))
	else
		failed=$((failed + 1))
		echo "[FAIL ] skulle vært TILLATT, ble blokkert: kubectl $*"
		echo "        output: $(head -1 <<<"$output")"
	fi
}

expect_blocked() {
	local output
	output="$(kubectl "$@" 2>&1)"
	if [[ "$output" == PASSTHROUGH:* ]]; then
		failed=$((failed + 1))
		echo "[FAIL ] skulle vært BLOKKERT, slapp gjennom: kubectl $*"
	else
		passed=$((passed + 1))
	fi
}

# --- Lesende kommandoer agenten faktisk trenger ---
expect_allowed get pods -n teamdagpenger
expect_allowed -n teamdagpenger get pods
expect_allowed get pods -l app=min-app -o wide -n teamdagpenger
expect_allowed describe pod min-app -n teamdagpenger
expect_allowed logs -n teamdagpenger min-app --previous --tail=50
expect_allowed top pods -n teamdagpenger
expect_allowed config current-context
expect_allowed version --client
expect_allowed wait --for=condition=Ready pod/min-app
# `auth can-i <verb>` er en ren lesespørring selv når verbet er destruktivt.
expect_allowed auth can-i get pods -n teamdagpenger
expect_allowed auth can-i delete pods -n teamdagpenger
expect_allowed -n teamdagpenger auth can-i create pods

# --- Destruktivt, verb først (dekkes også av --deny-tool) ---
expect_blocked delete pod min-app -n teamdagpenger
expect_blocked apply -f manifest.yaml
expect_blocked patch deployment min-app -p '{}'
expect_blocked rollout restart deployment/min-app
expect_blocked scale deployment/min-app --replicas=3
expect_blocked exec min-app -- sh
expect_blocked cp min-app:/tmp/x ./x

# --- Destruktivt, verb IKKE først: dette er formene --deny-tool IKKE fanger ---
expect_blocked -n teamdagpenger delete pod min-app
expect_blocked --namespace teamdagpenger delete pod min-app
expect_blocked --namespace=teamdagpenger delete pod min-app
expect_blocked --context dev-gcp -n teamdagpenger rollout restart deployment/min-app
expect_blocked --kubeconfig /tmp/kc apply -f manifest.yaml
expect_blocked -v 6 --context dev-gcp delete namespace teamdagpenger

# --- Verb som manglet helt i --deny-tool-lista ---
expect_blocked run min-pod --image=nginx
expect_blocked -n teamdagpenger debug pod/min-app --image=busybox
expect_blocked attach min-app -c container
expect_blocked auth reconcile -f rbac.yaml
expect_blocked -n teamdagpenger auth reconcile -f rbac.yaml
expect_blocked port-forward pod/min-app 8080:8080

echo
echo "Summary: $passed passed, $failed failed"
[[ "$failed" -eq 0 ]]
