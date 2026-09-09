# Clinical-trials hybrid retrieval on Exasol Personal Local

A semantic layer plus hybrid retrieval over ClinicalTrials.gov, built so that
the interesting part is **where it fails**.

```
./01_snapshot.sh        # the snapshot ships with the repo; this only refreshes it
./02_load_exasol.sh     # shred to tables, including 268,912 eligibility chunks
./03_semantic_layer.sh  # indication, sponsor, phase, status, endpoint, geography
./04_build_vectors.sh   # embed offline, load 25.8M vector rows, install the UDFs
./05_search.sh          # the payoff, and the failure
./06_eval.sh            # where it fails, measured
./00_preflight.sh       # GO / NO-GO
```

## The one design idea

Exasol has no vector type and no vector index. So vectors are stored **long and
narrow** — one row per dimension — and cosine similarity is an ordinary join and
`GROUP BY`:

```sql
SELECT v.NCT_ID, v.CHUNK_ID, SUM(v.VAL * q.VAL) AS SIM
FROM CT.ELIG_VECTORS v JOIN QV q ON q.DIM = v.DIM
GROUP BY v.NCT_ID, v.CHUNK_ID
```

Vectors are L2-normalised at build time, so a dot product *is* cosine. 25.8M
rows scan in about 5 seconds. Everything expensive — the TF-IDF fit, the SVD —
happens offline in Docker with sklearn pinned to the version the Exasol SLC
ships, because otherwise the pickle will not unpickle inside the UDF.

## What the data will and will not tell you

Measured on the loaded snapshot (12,404 trials), not quoted from documentation:

| Dimension | Reality |
|---|---|
| sponsor, status, geography, indication | Structured and reliable |
| **phase** | 34.4% say `NA` — "not applicable". `WHERE PHASE='PHASE3'` silently drops a third of the landscape, so the view exposes `PHASE_IS_STATED`. |
| **endpoint** | Free text only (`measure` + `timeFrame`). Derived by pattern into 18 categories; **35.7% still land in "Other / unclassified"** and that number is reported, not hidden. |
| **comparator** | Half structured: `armGroup.type` codes whether a control exists, but *which* drug it is sits in the arm label as prose. |
| **eligibility** | One free-text blob. There is **no** structured inclusion/exclusion field — the split is recovered here from prose headings, and 97.3% of chunks resolve to a definite section. |

## The failure, which is the point

Ask for trials that *exclude* prior PD-1 exposure and the fourth hit is
`NCT02595866`, whose criterion reads **"No prior treatment with anti-PD-1 or
anti-PD-L1"** — in the INCLUSION section. The opposite of the question.

Cosine cannot separate it: **0.9987 against 0.9990**. BM25 scores it *higher*
than two correct rows. The reason is one query away:

```sql
SELECT TERM FROM (SELECT CT.QUERY_TERMS('No prior treatment with anti-PD-1') FROM DUAL);
SELECT TERM FROM (SELECT CT.QUERY_TERMS('Prior treatment with anti-PD-1') FROM DUAL);
```

Identical. `no` is an English stopword, so the analyzer deletes the negation
before any scoring happens. Both rankers are blind, and fusing two blind
rankers does not restore sight.

What fixes it is not a bigger model. It is the recovered `CRITERION_SECTION`
column, applied before scoring:

| | recall@20 | section purity |
|---|---|---|
| text alone | 0.675 | 0.763 |
| with the structured section filter | **0.858** | **1.000** |
| — hybrid questions | 0.713 → 0.925 | 0.769 → 1.000 |
| — polarity questions | 0.600 → **0.725** | 0.750 → 1.000 |

The worst single case is `pol-02`, *"no prior systemic chemotherapy for
metastatic disease"* — **recall 0.15**, because the negation this time is in the
**query**, and the analyzer deletes it there too.

## A second failure the section filter cannot fix

Ask for `EGFR mutation positive` and the top hit is *"EGFR mutation **negative**
and ALK fusion negative"*. Here `negative` is **not** a stopword — it survives
tokenisation intact. The vector space simply does not encode that it inverts the
meaning, and BM25 sees a term match. Both the right and wrong criteria sit in
INCLUSION, so **the structured section filter offers no rescue at all**: recall
stays at 0.65 even with it applied (`pol-04`).

So there are two distinct polarity failures, not one:

| | mechanism | fixable by the section column? |
|---|---|---|
| "no prior treatment with X" | stopword deletion — `no` is removed before scoring | Yes, partly |
| "EGFR mutation negative" | antonymy — the token survives, the meaning does not | **No** |

Polarity is the category the structured filter helps *least*, because the
retrieval still cannot tell the two sentences apart; the filter only stops it
looking in the wrong half.

## Honesty

- All eval gold sets are `snapshot-sql`: reproducible predicates over the loaded
  data, **not** an independent ground truth. Review-derived questions are
  outstanding and tracked in `eval/REVIEW_QUESTIONS.md`.
- The vector side is TF-IDF + 96-dim SVD, not a transformer. It explains only
  18% of variance and its similarities are compressed into a narrow band near
  1.0, so *relative* order carries the signal and absolute scores mean little.
  A transformer would retrieve better and would be **just as blind to `no`**.
- The API advertises no rate limits, and the snapshot is committed anyway: a
  booth demo must never depend on the venue network.
