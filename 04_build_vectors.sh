#!/usr/bin/env bash
# STEP 4 — retrieval artefacts. Everything expensive happens OUTSIDE the database;
# the database is left with arithmetic it can parallelise.
source "$(dirname "$0")/lib/common.sh"

say "4a. Build the training image (sklearn pinned to the SLC's version)"
docker build -q -t "$ML_IMAGE" \
  --build-arg SK_VERSION="$SK_VERSION" --build-arg NP_VERSION="$NP_VERSION" "$KIT_ROOT/ml" \
  || die "docker build failed — is Docker running?"
ok "$ML_IMAGE"

say "4b. Embed the eligibility chunks (TF-IDF -> SVD -> L2 normalise)"
mkdir -p "$WORK/art"
docker run --rm -v "$WORK/csv:/data:ro" -v "$WORK/art:/out" "$ML_IMAGE" \
  --chunks /data/elig_chunks.csv --out /out --dims "$DIMS"

say "4c. Retrieval tables"
xsql -f "$KIT_ROOT/sql/02_retrieval_tables.sql" | tail -2
for pair in "chunk_len.parquet:CT.CHUNK_LEN" "term_idf.parquet:CT.TERM_IDF" \
            "chunk_tokens.parquet:CT.CHUNK_TOKENS" "elig_vectors.parquet:CT.ELIG_VECTORS"; do
  f="${pair%%:*}"; t="${pair##*:}"
  printf '    %-24s -> %s\n' "$f" "$t"
  exapump upload --table "$t" "$WORK/art/$f" >/dev/null
done

say "4d. Model -> BucketFS"
# BucketFS HTTP is not exposed on Personal (2581 refuses; writes want a password
# nobody set). It is a directory on the node, and the SSH port moves on every
# restart, so it is always read from deployment.json.
node_ssh "mkdir -p $BFS_DIR/ct"
node_scp "$WORK/art/elig_model.pkl" "$BFS_DIR/ct/elig_model.pkl"
node_ssh "ls -lh $BFS_DIR/ct/elig_model.pkl"

say "4e. The query-side UDFs"
xsql -f "$KIT_ROOT/sql/04_udfs.sql" | tail -2
xsql "SELECT COUNT(*) AS DIMS, ROUND(SQRT(SUM(VAL*VAL)),4) AS NORM
      FROM (SELECT CT.EMBED_QUERY('test query') FROM DUAL);"
ok "norm 1.0 means a dot product IS cosine"

say "4f. How big the vector table is"
xsql "SELECT COUNT(*) AS VECTOR_ROWS, COUNT(DISTINCT NCT_ID) AS TRIALS FROM CT.ELIG_VECTORS;"
say "STEP 4 DONE"
