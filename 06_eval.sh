#!/usr/bin/env bash
# STEP 6 — the deliverable. Being able to say where it fails beats any one query
# working nicely, so this is the part that gets shown, not skipped.
source "$(dirname "$0")/lib/common.sh"
ask <<'Q'
Where does this retrieval fail, and by how much?

  Every question runs TWICE — text alone, then with the structured section
  filter. The delta is the argument.
Q
python3 "$KIT_ROOT/eval/run_eval.py" --k "${K:-20}"
say "STEP 6 DONE — results in eval/results.json"
