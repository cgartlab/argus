#!/usr/bin/env bash
# Regression guard: a primary-model timeout must reach the fallback queue.
#
# Background (PR #203): `timeout` kills a hung `opencode github run`, so
# `$primary_output` is empty and the retryable-regex gate never matches. Two
# separate defects hid this:
#   1. #189 called `dismiss_stale_reviews` above its definition -> exit 127.
#   2. After that was fixed, the empty-output retry gate still hit
#      `return 124` before the fallback loop.
#
# This test extracts the real `run_with_fallback_queue` from action.yml and
# runs it against a fake `opencode` whose first invocation hangs. It asserts
# the fallback model is actually attempted.
#
# Usage: bash tests/action/test_timeout_fallback.sh   (needs bash + coreutils)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-$SCRIPT_DIR/../../.github/actions/argus-review/action.yml}"
if [ ! -f "$ACTION" ]; then
  echo "FAIL: action.yml not found at $ACTION" >&2
  exit 2
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Extract a top-level (8-space indented) function from the YAML. `run: |`
# blocks are plain bash; the function ends at the matching 8-space `}`.
extract() {
  local name="$1"
  awk -v name="$name" '
    index($0, "        " name "() {") == 1 { depth = 0; inside = 1 }
    inside {
      print
      depth += gsub(/\{/, "{") - gsub(/\}/, "}")
      if (depth == 0) exit
    }
  ' "$ACTION"
}
extract dismiss_stale_reviews > "$TMP/dismiss.sh"
extract run_with_fallback_queue > "$TMP/fn.sh"

if [ ! -s "$TMP/fn.sh" ]; then
  echo "FAIL: could not extract run_with_fallback_queue from $ACTION" >&2
  exit 2
fi

# GitHub expressions are not valid bash; neutralise them.
sed -i 's/\${{[^}]*}}//g' "$TMP/dismiss.sh" "$TMP/fn.sh"

# Fake `opencode` on PATH — `timeout` runs it as a child process, so a shell
# function cannot stand in. Invocation 1 hangs, later ones succeed.
mkdir -p "$TMP/bin"
cat > "$TMP/bin/opencode" <<'EOS_FAKE'
#!/usr/bin/env bash
n=$(cat "$FAKE_OC_COUNT" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" > "$FAKE_OC_COUNT"
if [ "$n" -eq 1 ]; then
  echo "pretend the model thinks forever" >&2
  sleep 30        # killed by the timeout wrapper
fi
echo "[stub] review ran OK (invocation $n)"
exit 0
EOS_FAKE
chmod +x "$TMP/bin/opencode"
export PATH="$TMP/bin:$PATH"
export FAKE_OC_COUNT="$TMP/count"

cat > "$TMP/harness.sh" <<EOF
set -uo pipefail
print_auth_guidance() { echo 'stub: auth guidance' ; }
gh() { echo '[]' ; }
REVIEW_TIMEOUT=1
retry_re="rate limit|model not found"
auth_re="401 unauthorized|invalid api key"
. "$TMP/dismiss.sh"
. "$TMP/fn.sh"
# run_with_fallback_queue returns, so capture its status explicitly.
run_with_fallback_queue "opencode/hung-model-free" "opencode/good-fallback-free"
rc=$?
echo "HARNESS_RC=\$rc"
EOF

set +e
out=$(bash "$TMP/harness.sh" 2>&1)
harness_rc=$?
rc=$(printf '%s\n' "$out" | grep '^HARNESS_RC=' | tail -1 | cut -d= -f2)
calls=$(cat "$FAKE_OC_COUNT" 2>/dev/null || echo 0)
tried_fallback=$(printf '%s' "$out" | grep -c 'Trying fallback')
completed=$(printf '%s' "$out" | grep -c 'Review completed with fallback model')
set -e
: "${rc:=missing}"

echo "=== timeout -> fallback regression ==="
echo "  return code:        $rc    (expect 0)"
echo "  opencode calls:     $calls (expect 2: primary + fallback)"
echo "  fallback attempted: $tried_fallback (expect >=1)"
echo "  fallback completed: $completed (expect 1)"

fail=0
[ "$rc" = "0" ] || { echo "  FAIL: timed-out primary did not end in success"; fail=1; }
[ "$calls" -ge 2 ] || { echo "  FAIL: fallback model was never invoked"; fail=1; }
[ "$tried_fallback" -ge 1 ] || { echo "  FAIL: 'Trying fallback' never printed"; fail=1; }
[ "$completed" -ge 1 ] || { echo "  FAIL: fallback run did not complete"; fail=1; }

if [ "$fail" -eq 0 ]; then
  echo "  PASS"
  exit 0
fi
echo "  RESULT: FAIL"
printf '%s\n' "$out" | sed 's/^/    | /'
exit 1
