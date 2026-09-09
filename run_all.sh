#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
for s in 01_snapshot 02_load_exasol 03_semantic_layer 04_build_vectors 05_search 06_eval; do
  ./$s.sh
done
./00_preflight.sh
