# Shared settings for the clinical-trials retrieval demo.
set -euo pipefail

KIT_ROOT="${KIT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
WORK="${WORK:-$KIT_ROOT/.work}"
DATA="${DATA:-$KIT_ROOT/data}"
mkdir -p "$WORK" "$DATA"

SCHEMA="${SCHEMA:-CT}"
# Retrieval width. 96 dims x ~10 chunks x ~10k trials is ~10M rows in the long
# vector table -- comfortable for Exasol, and small enough to rebuild in a break.
DIMS="${DIMS:-96}"
MAX_CHUNKS="${MAX_CHUNKS:-10}"
# The training image pins sklearn to whatever the SLC ships, or the pickle the
# UDF loads will refuse to unpickle. Verified: py 3.12.3 / numpy 1.26.4 / sklearn 1.7.2.
SK_VERSION="${SK_VERSION:-1.7.2}"
NP_VERSION="${NP_VERSION:-1.26.4}"
ML_IMAGE="${ML_IMAGE:-ct-vectors:local}"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
ok()   { printf '    \033[0;32mok\033[0m  %s\n' "$*"; }
warn() { printf '    \033[0;33m!!\033[0m  %s\n' "$*"; }
die()  { printf '\n\033[0;31merror: %s\033[0m\n' "$*" >&2; exit 1; }

# The question in English before the SQL -- the room reads this, the SQL is the proof.
ask() {
  printf '\n\033[7;1m  THE QUESTION                                                  \033[0m\n'
  while IFS= read -r line; do printf '\033[7m \033[0m  \033[1m%s\033[0m\n' "$line"; done
  printf '\033[7m \033[0m\n'
}

SHOW_SQL="${SHOW_SQL:-1}"
# Echo the statement before running it, to stderr: stdout is exapump's own output
# and callers pipe it.
xsql() {
  if [ "$SHOW_SQL" = "1" ]; then
    local body
    if [ "${1:-}" = "-f" ]; then body="$(cat "$2")"; else body="$1"; fi
    printf '\n\033[0;90m--- SQL ---\033[0m\n%s\n\033[0;90m-----------\033[0m\n' "$body" >&2
  fi
  # exapump reads a script from stdin; -f is its OUTPUT format flag, not a file.
  if [ "${1:-}" = "-f" ]; then exapump sql < "$2"; else exapump sql "$1"; fi
}

# Exasol Personal licenses 20 parallel connections and dash-server parks ~3 per
# board, idle, forever. Reclaim them or a later step dies one connection short
# and reports it as a credential failure.
free_connections() {
  local n
  n=$(exapump sql "SELECT COUNT(*) FROM EXA_ALL_SESSIONS;" 2>/dev/null | grep -oE '^[0-9]+$' | head -1 || echo 0)
  [ "${n:-0}" -gt 12 ] && warn "$n sessions open of 20 — consider: exakit restart" || true
}

# --- BucketFS on Exasol Personal -------------------------------------------
# The BucketFS HTTP port is not exposed on Personal (2581 refuses, and writes
# want a bfs_write_password nobody set). It IS a plain directory on the node,
# reachable as root over SSH -- but the SSH port is reassigned on every restart,
# so always read it from deployment.json rather than remembering it.
DEPLOY_DIR="${DEPLOY_DIR:-$HOME/.exasol/personal/deployments/default}"
BFS_DIR="${BFS_DIR:-/var/lib/exa/bucketfs/bfsdefault/default}"
# Path as the UDF sandbox sees it.
BFS_UDF="${BFS_UDF:-/buckets/bfsdefault/default}"

ssh_port() { jq -r '.connection.sshPort' "$DEPLOY_DIR/deployment.json"; }
node_ssh() {
  ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      -i "$DEPLOY_DIR/local/node_access.pem" -p "$(ssh_port)" root@127.0.0.1 "$@"
}
node_scp() {
  scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      -i "$DEPLOY_DIR/local/node_access.pem" -P "$(ssh_port)" "$1" "root@127.0.0.1:$2"
}
