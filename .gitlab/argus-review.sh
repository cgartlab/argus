#!/usr/bin/env bash
# Argus MR review runner for GitLab CI.
#
# Called by .gitlab/argus-review.yml (the include template). Resolves the
# changed frontend files of a merge request, runs the Argus local review CLI
# (cloned from cgartlab/argus), and posts the review as an MR note via the
# GitLab API.
#
# Environment (GitLab CI provides most; the template sets the rest):
#   ARGUS_RULES_DIR             cgartlab/argus checkout (set by the template)
#   ARGUS_MODE                  auto | static | llm  (complexity routing)
#   ARGUS_STACK                 auto | antd5 | material3 | polaris | custom
#   ARGUS_MR_TOKEN              token with api scope for MR notes; falls back
#                               to CI_JOB_TOKEN (same-project MRs)
#   ARGUS_DRY_RUN               1 = print the note instead of posting (local testing)
#   CI_PROJECT_ID / CI_MERGE_REQUEST_IID
#   CI_MERGE_REQUEST_DIFF_BASE_SHA / CI_COMMIT_SHA
set -euo pipefail

ARGUS_RULES_DIR="${ARGUS_RULES_DIR:?ARGUS_RULES_DIR must point to a cgartlab/argus checkout}"
CLI="$ARGUS_RULES_DIR/tools/argus_review.py"
MODE="${ARGUS_MODE:-auto}"
STACK="${ARGUS_STACK:-auto}"

# 1. Changed frontend files (MR diff vs its base; fallback: last commit).
if [ -n "${CI_MERGE_REQUEST_DIFF_BASE_SHA:-}" ] && [ -n "${CI_COMMIT_SHA:-}" ]; then
  changed=$(git diff --name-only "$CI_MERGE_REQUEST_DIFF_BASE_SHA" "$CI_COMMIT_SHA" \
              -- '*.css' '*.html' '*.htm' '*.js' '*.ts' '*.jsx' '*.tsx' || true)
else
  changed=$(git diff --name-only HEAD~1..HEAD \
              -- '*.css' '*.html' '*.htm' '*.js' '*.ts' '*.jsx' '*.tsx' || true)
fi

filelist=()
while IFS= read -r f; do
  [ -n "${f:-}" ] && [ -f "$f" ] && filelist+=("$f")
done <<< "$changed"

if [ "${#filelist[@]}" -eq 0 ]; then
  echo "Argus: no changed frontend files to review"
  exit 0
fi

# 2. Run the review (complexity routing via --mode).
echo "Argus: reviewing ${#filelist[@]} changed frontend file(s) (mode=$MODE, stack=$STACK)"
report="$ARGUS_RULES_DIR/dist/mr-report.json"
mkdir -p "$(dirname "$report")"
review_text="$(python3 "$CLI" "${filelist[@]}" --mode "$MODE" --stack "$STACK" --json "$report" 2>&1 || true)"

# 3. Build the MR note (markdown).
note_file="$(mktemp)"
{
  echo "## Argus Design Review"
  echo ""
  echo '```'
  echo "$review_text"
  echo '```'
} > "$note_file"

# 4. Post the note (or dry-run).
if [ "${ARGUS_DRY_RUN:-0}" = "1" ]; then
  echo "--- dry-run: MR note ---"
  cat "$note_file"
  rm -f "$note_file"
  exit 0
fi

if [ -z "${CI_PROJECT_ID:-}" ] || [ -z "${CI_MERGE_REQUEST_IID:-}" ]; then
  echo "Argus: not an MR pipeline (CI_PROJECT_ID/CI_MERGE_REQUEST_IID missing); skipping note"
  rm -f "$note_file"
  exit 0
fi

TOKEN="${ARGUS_MR_TOKEN:-${CI_JOB_TOKEN:-}}"
if [ -z "$TOKEN" ]; then
  echo "Argus: no token (ARGUS_MR_TOKEN / CI_JOB_TOKEN); skipping MR note"
  rm -f "$note_file"
  exit 0
fi

payload_file="$(mktemp)"
python3 - "$note_file" > "$payload_file" <<'PYEOF'
import json, sys
note = open(sys.argv[1], encoding="utf-8").read()
print(json.dumps({"body": note}))
PYEOF

GITLAB_HOST="${CI_SERVER_URL:-https://gitlab.com}"
curl -sS --fail \
  -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$payload_file" \
  "$GITLAB_HOST/api/v4/projects/${CI_PROJECT_ID}/merge_requests/${CI_MERGE_REQUEST_IID}/notes" >/dev/null
echo "Argus: MR note posted"
rm -f "$note_file" "$payload_file"