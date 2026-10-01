#!/usr/bin/env bash
# Everything, in order, from a fresh clone. Safe to re-run: each step is idempotent.
#
# 01_snapshot.sh is deliberately NOT here. It refetches from ClinicalTrials.gov,
# and the snapshot is committed, so the default path needs no network and gives
# everyone the same numbers. Run it yourself if you want fresher data.
set -euo pipefail
cd "$(dirname "$0")"

# A fresh or rebuilt Exasol Personal deployment ships with no script language
# container, and every UDF here unpickles a scikit-learn model, so this is a
# prerequisite rather than a nicety. Installing one restarts the database.
if ! exasol slc list 2>/dev/null | grep -qE 'python-3.*yes'; then
  echo "==> PYTHON3 SLC missing — installing it (this restarts the database)"
  exasol slc install PYTHON3
fi

for s in 02_load_exasol 03_semantic_layer 04_build_vectors 05_search 06_eval; do
  ./$s.sh
done

# The lake is a second system, so it is brought up explicitly rather than assumed.
./lake/up.sh
./lake/install_engine.sh
.work/lakeenv/bin/python lake/load_iceberg.py
./07_lake.sh

./00_preflight.sh
