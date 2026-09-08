#!/usr/bin/env bash
# Deterministisk enhetstest av shimene i scripts/readonly-guard/
# (kubectl, gcloud og nais).
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
GUARD_DIR="$REPO_ROOT/scripts/readonly-guard"

FAKE_REAL_DIR="$(mktemp -d)"
for tool in kubectl gcloud nais; do
	cat >"$FAKE_REAL_DIR/$tool" <<'EOS'
#!/usr/bin/env bash
echo "PASSTHROUGH: $*"
exit 0
EOS
	chmod +x "$FAKE_REAL_DIR/$tool"
done

cleanup() { rm -rf "$FAKE_REAL_DIR"; }
trap cleanup EXIT

export PATH="$GUARD_DIR:$FAKE_REAL_DIR:$PATH"

passed=0
failed=0

# Generiske varianter der første argument er verktøynavnet.
allowed() {
	local tool="$1"
	shift
	local output
	output="$("$tool" "$@" 2>&1)"
	if [[ "$output" == PASSTHROUGH:* ]]; then
		passed=$((passed + 1))
	else
		failed=$((failed + 1))
		echo "[FAIL ] skulle vært TILLATT, ble blokkert: $tool $*"
		echo "        output: $(head -1 <<<"$output")"
	fi
}

blocked() {
	local tool="$1"
	shift
	local output
	output="$("$tool" "$@" 2>&1)"
	if [[ "$output" == PASSTHROUGH:* ]]; then
		failed=$((failed + 1))
		echo "[FAIL ] skulle vært BLOKKERT, slapp gjennom: $tool $*"
	else
		passed=$((passed + 1))
	fi
}

expect_allowed() { allowed kubectl "$@"; }
expect_blocked() { blocked kubectl "$@"; }

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

# =====================================================================
# gcloud-shimen (allowlist)
# =====================================================================

# --- Lesende kommandoer ---
allowed gcloud projects list
allowed gcloud sql instances list --project teamdagpenger-dev
allowed gcloud compute instances describe min-vm --zone europe-north1-a
allowed gcloud container clusters list
allowed gcloud logging read 'resource.type=k8s_container' --limit 10
allowed gcloud info
allowed gcloud version
allowed gcloud config get-value project
allowed gcloud projects get-iam-policy teamdagpenger-dev

# --- Destruktivt, uansett posisjon ---
blocked gcloud sql instances delete min-db
blocked gcloud --project teamdagpenger-prod sql instances delete min-db
blocked gcloud compute instances create min-vm
blocked gcloud projects add-iam-policy-binding p --member=user:x --role=roles/owner
blocked gcloud sql instances patch min-db --database-flags=x
blocked gcloud app deploy
blocked gcloud secrets versions destroy 1

# --- Credential-eksponering og kubeconfig-mutasjon ---
blocked gcloud auth print-access-token
blocked gcloud auth print-identity-token
blocked gcloud container clusters get-credentials dev-gcp --region europe-north1
blocked gcloud auth login
blocked gcloud auth revoke

# --- Lese-verb som ressursnavn skal ikke gjøre kommandoen lesende ---
# Uten WRITE_VERBS-sjekken ville allowlisten sett "list"/"describe" og sluppet
# gjennom, fordi den kun leter etter tokens. Dette er casen som gjør den
# sjekken load-bearing.
blocked gcloud compute instances delete list --zone europe-north1-a
blocked gcloud sql instances delete describe

# --- Ukjent kommando skal feile lukket, ikke slippe gjennom ---
blocked gcloud beta some-new-surface do-something
blocked gcloud

# =====================================================================
# nais-shimen (allowlist per kommandogruppe)
# =====================================================================

# --- Lesende kommandoer ---
allowed nais status
allowed nais app list -t teamdagpenger
allowed nais app log min-app -t teamdagpenger -e dev-gcp
allowed nais app status min-app
allowed nais job list -t teamdagpenger
allowed nais validate .nais/nais.yaml
allowed nais postgres list -t teamdagpenger

# --- Destruktivt ---
blocked nais app delete min-app
blocked nais app restart min-app
blocked nais app stop min-app
blocked nais app set min-app replicas=0
blocked nais job trigger min-jobb
blocked nais apply .nais/nais.yaml
blocked nais debug min-app
blocked nais kubeconfig
blocked nais postgres migrate min-db
blocked nais postgres psql min-db
blocked nais postgres grant min-db

# --- Hemmeligheter skal ikke inn i agentens kontekst ---
blocked nais secret list -t teamdagpenger
blocked nais app env min-app
blocked nais app files min-app

# --- Globale flagg før kommandogruppen skal ikke gi falsk blokkering ---
allowed nais -t teamdagpenger status
allowed nais -e dev-gcp app list

# --- Flaggverdier skal ikke forveksles med kommandoer ---
# "-t delete" ville sluppet gjennom hvis flaggverdien ble tolket som gruppe.
allowed nais app list -t teamdagpenger -e dev-gcp
blocked nais -t teamdagpenger app delete min-app

# --- Hjelpetekst er tillatt, men skal ikke kunne smugle med destruktive verb ---
allowed nais --help
allowed gcloud --help
blocked nais app delete min-app --help
blocked gcloud sql instances delete min-db --help

# --- Ukjent gruppe skal feile lukket ---
blocked nais some-new-command
blocked nais

echo
echo "Summary: $passed passed, $failed failed"
[[ "$failed" -eq 0 ]]
