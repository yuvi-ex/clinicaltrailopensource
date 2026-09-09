#!/usr/bin/env bash
# STEP 0 — is this machine ready to demo? Answers GO / NO-GO, nothing else.
source "$(dirname "$0")/lib/common.sh"
SHOW_SQL=0
fail=0
chk() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else warn "$1 — FAILED"; fail=$((fail+1)); fi; }

say "Preflight"
chk "database answers on 8563"        "exapump sql 'SELECT 1;'"
chk "PYTHON3 SLC installed"           "exasol slc list | grep -qE 'python-3.*yes'"
chk "snapshot present in repo"        "test -s '$DATA/trials_snapshot.json.gz'"
chk "CT.TRIALS loaded"                "exapump sql 'SELECT 1 FROM CT.TRIALS LIMIT 1;'"
chk "CT.ELIG_CHUNKS loaded"           "exapump sql 'SELECT 1 FROM CT.ELIG_CHUNKS LIMIT 1;'"
chk "CT.ELIG_VECTORS loaded"          "exapump sql 'SELECT 1 FROM CT.ELIG_VECTORS LIMIT 1;'"
chk "semantic layer views resolve"    "exapump sql 'SELECT 1 FROM CT.V_LANDSCAPE LIMIT 1;'"
chk "model in BucketFS"               "node_ssh test -s $BFS_DIR/ct/elig_model.pkl"
# The UDF is the one thing a healthcheck cannot infer: the tables can be perfect
# and the query path still dead if the pickle will not unpickle in the SLC.
chk "EMBED_QUERY returns 96 dims"     "exapump sql \"SELECT 1 FROM (SELECT CT.EMBED_QUERY('test') FROM DUAL) HAVING COUNT(*)=$DIMS;\""
chk "QUERY_TERMS returns terms"       "exapump sql \"SELECT 1 FROM (SELECT CT.QUERY_TERMS('brain metastases') FROM DUAL) LIMIT 1;\""

free_connections
say $([ $fail -eq 0 ] && echo "GO — $fail failures" || echo "NO-GO — $fail failures")
exit $fail
