#!/usr/bin/env bash
# STEP 5 — the payoff, and the failure. Run this one slowly.
source "$(dirname "$0")/lib/common.sh"

ask <<'Q'
Find me trials that EXCLUDE patients who already had a PD-1 inhibitor.

  Exasol holds  the structured layer  — phase, sponsor, status, geography
  Exasol holds  the criteria text too — 268,912 chunks, embedded offline
  Vector search here is a JOIN and a GROUP BY. There is no vector index.
Q
say "5a. Text alone — vector + BM25, fused with RRF"
python3 "$KIT_ROOT/bin/search.py" "prior treatment with an anti-PD-1 or anti-PD-L1 antibody" --topk 6

cat <<'NOTE'

    Look at the SECTION column. One of those rows says INCLUSION, and its text
    is "No prior treatment with anti-PD-1 or anti-PD-L1" -- the OPPOSITE of what
    was asked. The vector score cannot separate it: 0.9987 against 0.9990.
    BM25 scores it HIGHER than two correct rows.
NOTE

ask <<'Q'
Why does that happen? Because the negation is gone before scoring starts.
Q
say "5b. Tokenise the two opposite sentences and compare"
xsql "SELECT 'No prior treatment...' AS VARIANT, TERM FROM (SELECT CT.QUERY_TERMS('No prior treatment with anti-PD-1') FROM DUAL)
      UNION ALL
      SELECT 'Prior treatment...', TERM FROM (SELECT CT.QUERY_TERMS('Prior treatment with anti-PD-1') FROM DUAL)
      ORDER BY 2,1;"

cat <<'NOTE'

    'no' is an English stopword. The analyzer deletes it. Two sentences that mean
    opposite things become the same bag of terms -- so BOTH rankers are blind,
    and fusing two blind rankers does not restore sight.
NOTE

ask <<'Q'
So what fixes it? Not a better model. A column.
Q
say "5c. Same query, with the recovered CRITERION_SECTION applied before scoring"
python3 "$KIT_ROOT/bin/search.py" "prior treatment with an anti-PD-1 or anti-PD-L1 antibody" --section EXCLUSION --topk 6

say "5d. And the structured layer still does the structured half"
python3 "$KIT_ROOT/bin/search.py" "EGFR mutation positive" --section INCLUSION \
  --filter "AND t.INDICATION='NSCLC' AND t.PHASE='PHASE3' AND t.STATUS_GROUP='Open'" --topk 6
say "STEP 5 DONE — the structured field did what a bigger model would not have"
