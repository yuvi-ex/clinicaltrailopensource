#!/usr/bin/env bash
# STEP 0 — is this machine ready to demo? Answers GO / NO-GO, nothing else.
source "$(dirname "$0")/lib/common.sh"
SHOW_SQL=0
fail=0
chk() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else warn "$1 — FAILED"; fail=$((fail+1)); fi; }

say "Preflight"
chk "database answers on 8563"        "exa_sql 'SELECT 1;'"
chk "PYTHON3 SLC installed"           "exasol slc list | grep -qE 'python-3.*yes'"
chk "snapshot present in repo"        "test -s '$DATA/trials_snapshot.json.gz'"
chk "CT.TRIALS loaded"                "exa_sql 'SELECT 1 FROM CT.TRIALS LIMIT 1;'"
chk "CT.ELIG_CHUNKS loaded"           "exa_sql 'SELECT 1 FROM CT.ELIG_CHUNKS LIMIT 1;'"
chk "CT.ELIG_VECTORS loaded"          "exa_sql 'SELECT 1 FROM CT.ELIG_VECTORS LIMIT 1;'"
chk "semantic layer views resolve"    "exa_sql 'SELECT 1 FROM CT.V_LANDSCAPE LIMIT 1;'"
chk "model in BucketFS"               "test -s '$BFS_DIR/ct/elig_model.pkl'"
# The UDF is the one thing a healthcheck cannot infer: the tables can be perfect
# and the query path still dead if the pickle will not unpickle in the SLC.
chk "EMBED_QUERY returns 96 dims"     "exa_sql \"SELECT 1 FROM (SELECT CT.EMBED_QUERY('test') FROM DUAL) HAVING COUNT(*)=$DIMS;\""
chk "QUERY_TERMS returns terms"       "exa_sql \"SELECT 1 FROM (SELECT CT.QUERY_TERMS('brain metastases') FROM DUAL) LIMIT 1;\""

# The clock is checked and FIXED BEFORE the lake, not after. It signs every S3
# request, so a skewed clock fails all three lake checks below -- and checking it
# last meant preflight printed NO-GO and then silently repaired the cause, so the
# honest result only appeared on a second run. Overnight sleep is enough: 28,230s
# of drift was measured after one night with the lid closed.
RUNTIME="$DEPLOY_DIR/local/runtime"
LAUNCHER=$(ls -t "$HOME/Library/Caches/.exasol/personal/runtime-artifacts/artifacts/exasol-local-runner"/*/*/*/unpack/launcher 2>/dev/null | head -1 || true)
if [ -n "$LAUNCHER" ] && [ -f "$RUNTIME/vm-runtime.json" ]; then
  VM=$( (cd "$RUNTIME" && "$LAUNCHER" run -- date -u '+%s') 2>/dev/null | tail -1 )
  case "$VM" in ''|*[!0-9]*) VM="" ;; esac
  if [ -n "$VM" ]; then
    SKEW=$(( VM > $(date -u +%s) ? VM - $(date -u +%s) : $(date -u +%s) - VM ))
    if [ "$SKEW" -gt 300 ]; then
      warn "VM clock ${SKEW}s off — S3 would 403 (reads like bad credentials, is not). Resyncing…"
      (cd "$RUNTIME" && "$LAUNCHER" run -- hwclock -s) >/dev/null 2>&1 || true
      VM=$( (cd "$RUNTIME" && "$LAUNCHER" run -- date -u '+%s') 2>/dev/null | tail -1 )
      SKEW=$(( VM > $(date -u +%s) ? VM - $(date -u +%s) : $(date -u +%s) - VM ))
      if [ "$SKEW" -le 300 ]; then ok "VM clock resynced (${SKEW}s)"; else
        warn "  still off — run: (cd $RUNTIME && '$LAUNCHER' run -- hwclock -s)"
        fail=$((fail+1)); fi
    else
      ok "VM clock within ${SKEW}s of host"
    fi
  fi
fi

# --- the lake ---------------------------------------------------------------
# Step 7 reads publications straight out of object storage, so the lake is part
# of the demo, not an optional extra. Checked in the order a failure cascades:
# containers, then the engine, then an actual read -- because the first two can
# both pass while the read fails. The clock was already fixed above.
chk "lake containers healthy"        "test \$(docker ps --filter name=ct-lake- --filter health=healthy -q | wc -l) -ge 2"
chk "lakehouse engine loads"         "exa_sql 'SELECT LAKEHOUSE.LAKEHOUSE_VERSION();'"
chk "CT_LAKE virtual schema resolves" "exa_sql 'SELECT 1 FROM CT_LAKE.PUBLICATIONS LIMIT 1;'"
chk "native+lake join runs"          "exa_sql 'SELECT COUNT(*) FROM CT.V_LANDSCAPE t LEFT JOIN CT_LAKE.TRIAL_PUBLICATIONS p ON p.NCT_ID=t.NCT_ID;'"

free_connections
say $([ $fail -eq 0 ] && echo "GO — $fail failures" || echo "NO-GO — $fail failures")
exit $fail
