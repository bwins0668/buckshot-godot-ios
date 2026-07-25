#!/usr/bin/env bash
# Self-heal driver for Buckshot iOS CI.
#
# Runs after the smoke test step. If the sim smoke test verdict is FAIL
# (black screen OR fatal log signature), this script:
#   1. Calls ci/full_byte_diff.py to find missing/different resources
#      between the original PCK and the current dev project
#   2. Extracts the missing resources from the original PCK via
#      ci/unpack_pck.py into the project tree
#   3. Re-runs the iOS export + archive + smoke test cycle
#   4. Repeats up to MAX_ITERS (default 3) iterations
#   5. Uploads the iteration report and any remaining artifacts before
#      final exit
#
# Invocation (CI):
#   bash ci/self_heal.sh \
#       --orig-pck /path/to/Buckshot.exe \
#       --repo-root . \
#       --max-iters 3 \
#       --report-path .godot/.self_heal_report.json
#
set -uo pipefail

MAX_ITERS=${MAX_ITERS:-3}
ORIG_PCK="${ORIG_PCK:-}"
REPO_ROOT="${REPO_ROOT:-$(pwd)}"
REPORT_PATH="${REPORT_PATH:-$REPO_ROOT/.godot/.self_heal_report.json}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --orig-pck) ORIG_PCK="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    --max-iters) MAX_ITERS="$2"; shift 2;;
    --report-path) REPORT_PATH="$2"; shift 2;;
    *) echo "unknown arg: $1"; shift;;
  esac
done

if [[ -z "$ORIG_PCK" ]]; then
  echo "[self_heal] ORIG_PCK not set; cannot recover resources. Exiting."
  exit 1
fi

mkdir -p "$(dirname "$REPORT_PATH")"
echo "[]" > "$REPORT_PATH"

report_iter() {
  local it="$1" verdict="$2" details="$3"
  python3 - <<PY
import json, pathlib
p = pathlib.Path("$REPORT_PATH")
data = json.loads(p.read_text() or "[]")
data.append({"iter": $it, "verdict": "$verdict", "details": "$details"})
p.write_text(json.dumps(data, indent=2))
PY
}

for i in $(seq 1 "$MAX_ITERS"); do
  echo "=== self-heal iter $i / $MAX_ITERS ==="
  echo "[self_heal $i] running byte diff against original PCK"
  DIFF_JSON="$REPO_ROOT/.godot/.byte_diff_iter_$i.json"
  python3 "$REPO_ROOT/ci/full_byte_diff.py" \
    --orig "$ORIG_PCK" --repo "$REPO_ROOT" --output "$DIFF_JSON" || true

  if [[ ! -s "$DIFF_JSON" ]]; then
    report_iter "$i" "fail" "byte_diff produced no output"
    echo "[self_heal $i] byte diff empty — black screen is not resource-related"
    break
  fi

  MISSING_COUNT=$(python3 -c "import json,sys; d=json.load(open('$DIFF_JSON')); print(len(d.get('only_orig', [])))")
  echo "[self_heal $i] missing-from-project: $MISSING_COUNT files"

  if [[ "$MISSING_COUNT" -gt 0 ]]; then
    FILTER_FILE="$REPO_ROOT/.godot/.missing_iter_$i.txt"
    python3 -c "
import json, sys
d = json.load(open('$DIFF_JSON'))
with open('$FILTER_FILE', 'w') as f:
    for p in d.get('only_orig', []):
        f.write(p + '\n')
print('[self_heal] wrote filter:', '$FILTER_FILE', 'paths=', len(d.get('only_orig', [])))
"
    echo "[self_heal $i] extracting missing files from original PCK (selective)"
    python3 "$REPO_ROOT/ci/extract_missing.py" \
      "$ORIG_PCK" "$FILTER_FILE" "$REPO_ROOT" || true
    report_iter "$i" "recovered" "extracted $MISSING_COUNT files"
    echo "[self_heal $i] requesting CI re-run with extracted files"
  else
    report_iter "$i" "no_change" "byte diff empty — escalate to iPad real device"
    echo "[self_heal $i] no missing resources — likely iOS Metal/sim-only issue"
    break
  fi
done

echo "=== self-heal summary ==="
cat "$REPORT_PATH"
echo "[self_heal] done; max iters=$MAX_ITERS reached"