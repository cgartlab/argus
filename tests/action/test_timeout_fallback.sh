#!/usr/bin/env bash
# Regression guard: the fallback-queue logic in action.yml.
#
# Covers the model-invocation contract:
#   1. a primary-model TIMEOUT with NO review posted must reach the fallback
#      queue (PR #203 background: `timeout` kills a hung `opencode github run`,
#      `$primary_output` is empty, and the retryable gate used to skip the
#      queue entirely — two separate defects hid this);
#   2. a primary-model TIMEOUT with the review ALREADY POSTED must be treated
#      as success — no second model burn, no duplicate review (#185 shape:
#      the review is posted, then the process hangs);
#   3. a primary NON-retryable failure must also reach the fallback queue
#      (a different model may succeed where the primary cannot);
#   4. a fallback TIMEOUT with the review ALREADY POSTED is success too.
#
# The test extracts the real `review_already_posted` + `run_with_fallback_queue`
# from action.yml and runs them against a fake `opencode` on PATH.
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

# The old test extracted `dismiss_stale_reviews`; that function was removed and
# replaced by `review_already_posted` (it queried /pulls/{n}/reviews for
# PENDING/COMMENTED reviews, but Argus output is an issue comment, so it was a
# silent no-op). Fail loudly if the extraction breaks again.
extract review_already_posted > "$TMP/review_already.sh"
extract run_with_fallback_queue > "$TMP/fn.sh"

if [ ! -s "$TMP/review_already.sh" ]; then
  echo "FAIL: could not extract review_already_posted from $ACTION" >&2
  exit 2
fi
if [ ! -s "$TMP/fn.sh" ]; then
  echo "FAIL: could not extract run_with_fallback_queue from $ACTION" >&2
  exit 2
fi

# Neutralise GitHub expressions; `${{ github.event.pull_request.number }}`
# becomes empty, so pin it to a test value afterwards.
sed -i 's/\${{[^}]*}}//g' "$TMP/review_already.sh" "$TMP/fn.sh"
sed -i 's/^\([[:space:]]*local pr_number="\)"/\1123"/' "$TMP/review_already.sh"

# Fake `opencode` on PATH — `timeout` runs it as a child process, so a shell
# function cannot stand in. Invocation behaviour is driven by env:
#   FAKE_PRIMARY_MODE  hang|error|success   (invocation 1)
#   FAKE_FALLBACK_MODE hang|success         (invocation 2+)
# A "hang" that "posts" first writes `yes` to $FAKE_REVIEW_FILE, mirroring the
# #185 shape (review lands, then the process hangs).
mkdir -p "$TMP/bin"
cat > "$TMP/bin/opencode" <<'EOS_FAKE'
#!/usr/bin/env bash
n=$(cat "$FAKE_OC_COUNT" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" > "$FAKE_OC_COUNT"
if [ "$n" -eq 1 ]; then
  case "${FAKE_PRIMARY_MODE:-hang}" in
    hang)
      echo "pretend the model thinks forever" >&2
      sleep 30
      ;;
    error)
      echo "model returned a non-retryable error" >&2
      exit 1
      ;;
  esac
else
  if [ "${FAKE_FALLBACK_MODE:-success}" = "hang" ]; then
    echo "yes" > "$FAKE_REVIEW_FILE"
    echo "pretend the fallback posted then hung" >&2
    sleep 30
  fi
fi
echo "[stub] review ran OK (invocation $n)"
exit 0
EOS_FAKE
chmod +x "$TMP/bin/opencode"
export PATH="$TMP/bin:$PATH"
export FAKE_OC_COUNT="$TMP/count"
export FAKE_REVIEW_FILE="$TMP/review_posted"
export GITHUB_RUN_ID=12345

# gh stub: `review_already_posted` runs
#   gh api repos/<repo>/issues/<n>/comments --paginate --jq '...'
# We ignore the args and return a comment list whose bodies carry the run-URL
# footer and the review summary header when $FAKE_REVIEW_FILE says so.
export FAKE_GH_COMMENT="$TMP/gh_comment"
cat > "$TMP/gh_stub.sh" <<'GH_STUB'
gh() {
  if [ "$(cat "$FAKE_REVIEW_FILE" 2>/dev/null || echo no)" = "yes" ]; then
    cat "$FAKE_GH_COMMENT"
  else
    echo '[]'
  fi
}
GH_STUB
# A comment body that belongs to this run and carries the Argus summary header.
printf '%s' '[{"body":"## Argus Design Review Summary\n- Total Issues: 0\n[github run](/r/a/actions/runs/'"$GITHUB_RUN_ID"')"}]' > "$FAKE_GH_COMMENT"

cat > "$TMP/harness.sh" <<EOF
set -uo pipefail
print_auth_guidance() { echo 'stub: auth guidance' ; }
. "$TMP/gh_stub.sh"
REVIEW_TIMEOUT=1
retry_re="rate limit|model not found"
auth_re="401 unauthorized|invalid api key"
. "$TMP/review_already.sh"
. "$TMP/fn.sh"
run_with_fallback_queue "opencode/hung-model-free" "opencode/good-fallback-free"
rc=\$?
echo "HARNESS_RC=\$rc"
EOF

run_case() {
  local name="$1" primary_mode="$2" fallback_mode="$3" expect_calls="$4" expect_rc="$5"
  local expect_tried_fallback="$6" expect_completed="$7" expect_already="$8" initial_review="$9"
  rm -f "$FAKE_OC_COUNT" "$FAKE_REVIEW_FILE"
  if [ "$initial_review" = "yes" ]; then
    echo "yes" > "$FAKE_REVIEW_FILE"
  else
    : > "$FAKE_REVIEW_FILE"   # default: no review posted
  fi
  FAKE_PRIMARY_MODE="$primary_mode" FAKE_FALLBACK_MODE="$fallback_mode" \
    bash "$TMP/harness.sh" > "$TMP/out_$name.txt" 2>&1
  local harness_rc=$?
  local rc calls tried completed already
  rc=$(grep '^HARNESS_RC=' "$TMP/out_$name.txt" | tail -1 | cut -d= -f2)
  calls=$(cat "$FAKE_OC_COUNT" 2>/dev/null || echo 0)
  tried=$(grep -c 'Trying fallback' "$TMP/out_$name.txt")
  completed=$(grep -c 'Review completed with fallback model' "$TMP/out_$name.txt")
  already=$(grep -c 'already posted by the timed-out' "$TMP/out_$name.txt")

  echo "=== $name ==="
  echo "  opencode calls:     $calls (expect $expect_calls)"
  echo "  return code:        $rc   (expect $expect_rc)"
  echo "  fallback attempted: $tried (expect >=$expect_tried_fallback)"
  echo "  fallback completed: $completed (expect >=$expect_completed)"
  echo "  already-posted hit: $already (expect >=$expect_already)"

  local fail=0
  [ "$harness_rc" = "0" ] || { echo "  FAIL: harness exited $harness_rc"; fail=1; }
  [ "$calls" = "$expect_calls" ] || { echo "  FAIL: opencode calls $calls != $expect_calls"; fail=1; }
  [ "$rc" = "$expect_rc" ] || { echo "  FAIL: return code $rc != $expect_rc"; fail=1; }
  [ "$tried" -ge "$expect_tried_fallback" ] || { echo "  FAIL: 'Trying fallback' $tried < $expect_tried_fallback"; fail=1; }
  [ "$completed" -ge "$expect_completed" ] || { echo "  FAIL: fallback completed $completed < $expect_completed"; fail=1; }
  [ "$already" -ge "$expect_already" ] || { echo "  FAIL: already-posted $already < $expect_already"; fail=1; }
  if [ "$fail" -eq 0 ]; then
    echo "  PASS"
  else
    printf '%s\n' "$(cat "$TMP/out_$name.txt")" | sed 's/^/    | /'
    return 1
  fi
  return 0
}

fail=0

# Case 1: primary timeout, NO review posted -> fallback must run and succeed.
run_case "timeout_no_review" "hang" "success" 2 0 1 1 0 no || fail=1

# Case 2: primary timeout, review ALREADY posted -> success, no fallback, no dup.
run_case "timeout_review_posted" "hang" "success" 1 0 0 0 1 yes || fail=1

# Case 3: primary NON-retryable error -> still tries fallback (was: skipped).
run_case "primary_nonretryable" "error" "success" 2 0 1 1 0 no || fail=1

# Case 4: fallback timeout with review posted (primary failed fast) -> success.
run_case "fallback_timeout_review_posted" "error" "hang" 2 0 1 0 1 no || fail=1

echo ""
if [ "$fail" -eq 0 ]; then
  echo "ALL FALLBACK-QUEUE TESTS PASSED"
  exit 0
fi
echo "RESULT: FAIL"
exit 1
