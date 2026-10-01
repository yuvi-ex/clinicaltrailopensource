# Clinical trial intelligence on Exasol

Ask a clinical-trial question in English. An agent writes the SQL, runs it against
Exasol, and answers citing the trial IDs it used. Ask for a landscape instead and
the same data produces a structured report you can send on.

The point the demo makes is not that the engine is fast. It is that **"pembrolizumab
in the US" is 538 trials, or 304** — depending on judgements nobody usually writes
down — and that a semantic layer is where those judgements belong. A third reading,
*US-led*, is the sharper point: the registry records no sponsor country, so it
cannot be derived at all, and the layer says so rather than guessing.

**First:** you need **Exasol Personal running locally** and Docker. A clone alone
will not show the UI — see [What it needs](#what-it-needs).

A fresh or rebuilt deployment ships with **no script language container**, and
the UDFs will not run without one. Check with `exasol slc list`; if `python-3.12`
says `no`, install it first — this restarts the database:

```
exasol slc install PYTHON3
```

**The whole thing, one command** — it installs the SLC if it is missing, runs
every step in order, and finishes with preflight. Roughly 20 minutes, most of it
the embedding:

```
./run_all.sh
./app/run.sh             # then the demo, on http://127.0.0.1:8503
```

Or step by step, which is the same sequence:

```
./02_load_exasol.sh                      # shred the committed snapshot into tables
./03_semantic_layer.sh                   # the views, and the resolution layer
./04_build_vectors.sh                    # embed offline, 25.8M rows, the UDFs (~15 min)

./lake/up.sh                             # OPTIONAL from here: MinIO + Iceberg catalog
./lake/install_engine.sh                 # the lakehouse engine into Exasol
.work/lakeenv/bin/python lake/load_iceberg.py   # write the publications to the lake
./07_lake.sh                             # the native-plus-lake query

./00_preflight.sh        # GO / NO-GO, 15 checks — LAST, because it verifies the result
./app/run.sh             # the demo, on http://127.0.0.1:8503
```

There is no `01` step on purpose: `01_snapshot.sh` refetches from
ClinicalTrials.gov, and the snapshot is committed, so the default path needs no
network and gives everyone the same numbers. Skip the four `lake/` lines if you
do not want the lakehouse — those sections of the page hide themselves rather
than erroring. Do not skip `load_iceberg.py` if you *do* want it: without it the
catalog has no tables.

## What it does

**Three pages.** The challenge, the demo, and how Exasol does it.

**An agent, over MCP.** Claude reaches the database through
[`exasol-mcp-server`](https://github.com/exasol-labs/exasol-mcp-server): it reads
the schema, writes its own SQL, runs it, and cites NCT ids. No query is written
for it, and it reaches Iceberg tables in object storage the same way it reaches
native ones, because a virtual schema is just a schema.

**Report generation.** A keyword such as *"What is the current trial landscape for
Pembrolizumab in US"* produces a structured report — scope, trials, sponsors,
phase, status, geography, endpoints, publication linkage — downloadable as
Markdown, and convertible with `bin/md2pdf.py`. The sections and their SQL are
fixed, so the same keyword always produces the same document; the model writes
only the summary, over numbers already computed.

**A resolution layer** (`sql/07_resolution.sql`) that publishes its judgements
instead of burying them:

| Judgement | Measured on pembrolizumab |
|---|---|
| Which names are the same drug | 732 by literal name, **760** with aliases — 28 trials say only Keytruda or MK-3475 |
| Which sponsors are one company | 4 strings roll up to Merck & Co.; **Merck KGaA is a different company** and stays separate |
| What "in the US" means | **538** has-a-US-site · **304** US-only · *US-led is not derivable — the registry has no sponsor country* |

Every report opens by stating which reading it took and what the alternatives
would have given.

## The second source, and the second storage tier

Trials are in the warehouse. The evidence that a trial ever produced a *result*
is not, so PubMed publications live in a **lakehouse** — Iceberg tables on
object storage — and are never loaded into Exasol. They are read at query time
by `exasol-labs/lakehouse-engine-rs`, a Rust UDF running DataFusion inside the
database, and joined to native tables in one statement:

```sql
SELECT t.PHASE, COUNT(DISTINCT t.NCT_ID) - COUNT(DISTINCT p.NCT_ID) AS NO_PUBLICATION
FROM CT.V_LANDSCAPE t                                    -- native Exasol
LEFT JOIN CT_LAKE.TRIAL_PUBLICATIONS p ON p.NCT_ID = t.NCT_ID  -- Parquet on S3
WHERE t.STATUS_GROUP = 'Completed' AND t.PHASE_IS_STATED
GROUP BY t.PHASE;
```

The join key is real: PubMed carries the registry number as a DataBank
accession, so this is an equi-join on `NCT_ID`, not title matching.

**93 of 242 completed Phase 3 trials — 38.4% — have no linked publication.** Say
the caveat with the number: a paper that never cites its NCT number is invisible
to this join, so this is a lower bound on reporting, not proof a trial went
unpublished.

> **An earlier version of this README said 65.8%, and that was wrong.** The query
> used `COUNT(*)` after the `LEFT JOIN`. `TRIAL_PUBLICATIONS` holds one row per
> trial–paper link, so a trial with three papers contributed three rows, and the
> inflated count landed in both the numerator and the denominator. Counting
> `DISTINCT t.NCT_ID` gives 242 trials where `COUNT(*)` gave 436 — so the real
> figure is **38.4%, not 65.8%**. A fan-out bug in one `SELECT` moved the
> headline number by 27 percentage points.

Cost of the second tier, measured on the machine in Tested on: a native count is
~58ms and the same count joined to the lake ~225ms, both including client connect
time — so reaching the lake costs about **170ms**, not 225.

### How the lakehouse is installed here

`lake/install_engine.sh` places the engine and its language container into the
database's storage directory and registers the four scripts it needs. On the
local backend the Exasol node shares that directory with the host, so the engine
is installed with a file copy rather than an upload.

`lake/docker-compose.yml` runs MinIO for object storage and
`apache/iceberg-rest-fixture` for the Iceberg catalog — two containers, the same
REST interface a managed catalog exposes.

`lake/up.sh` starts them and verifies that the database can reach both, and
`00_preflight.sh` checks the same path as part of its GO / NO-GO report.

## What it needs

**Cloning this repo is not enough to see the UI.** The snapshots ship with it,
but the database does not — the app opens on *"Exasol is not answering"* until
you have loaded the data locally.

To get from a clone to a running demo you need:

| | Needed for |
|---|---|
| **Exasol Personal**, running locally (`exasol status` says `database_ready`) with the PYTHON3 SLC | everything |
| **Docker** | the offline embedding step, and the two lakehouse containers |
| Steps `02` → `04` | the tables, the views and the 25.8M vector rows. Roughly 15 minutes, most of it the embedding |
| `lake/up.sh` + `lake/install_engine.sh` | the lakehouse sections only. Skip them and those sections hide themselves |
| `ANTHROPIC_API_KEY` in `.env` | the agent and the report summary. Everything else works without it |

`app/run.sh` builds its own virtualenv from `requirements.txt` on first run, so
Python dependencies need no separate step.

### What the agent connects as

Query execution is **off by default** in `exasol-mcp-server`. The app turns it on
by passing `EXA_MCP_SETTINGS={"enable_read_query": true, "default_row_limit": 50}`;
without it the agent can describe the schema but never query it.

**Be aware that this demo connects as `sys`, the Exasol superuser.** The only
thing keeping the agent read-only is that MCP setting — a client-side toggle, not
a database grant. That is fine for a local demo on a disposable deployment and
**is not a pattern to copy into anything shared**: create a user with `SELECT`
on the `CT` schema and connect as that instead.

| | |
|---|---|
| Model | `claude-opus-5` |
| Rough cost | a few cents per question; a full landscape report is one extra call over precomputed numbers |
| Row limit | 50 per tool call |
| Without `ANTHROPIC_API_KEY` | every page still works except the agent tab and the report's written summary |

Everything reaches the database through the Exasol CLI: `exasol connect` for SQL,
`IMPORT FROM LOCAL CSV FILE` for bulk load, and a plain `cp` into the storage
directory the VM shares with the host. There is no separate load tool and no SSH
to the node.

## The sample data

Both datasets ship **in this repo**, so a clone has everything it needs and no
step depends on network access or an API key.

| File | Contents | Size |
|---|---|---|
| `data/trials_snapshot.json.gz` | **12,404** interventional trials from ClinicalTrials.gov, started 2015 or later | 15 MB |
| `data/pubmed_snapshot.json.gz` | **3,796** PubMed publications carrying **4,627** trial citations. Those name 3,233 distinct trials, **2,644** of which are in the snapshot above | 2.7 MB |

Each snapshot carries its own provenance — when it was fetched, the exact query
filter and the field list — inside a `_meta` block, so what you load is
reproducible and auditable:

```
AREA[StudyType]INTERVENTIONAL AND AREA[StartDate]RANGE[2015-01-01,MAX]
```

Publications are joined to trials by the NCT number the paper itself cites as a
DataBank accession. A paper that never cites its trial is invisible to that join,
which is why publication linkage is reported as a **lower bound** and never as
proof that a trial went unpublished.

`01_snapshot.sh` and `ingest/fetch_pubmed.py` refetch these from the public APIs
if you want fresher data. You do not need to run them — `02_load_exasol.sh`
reads the committed snapshots directly.

## The one design idea

Exasol has no vector type and no vector index (**as of Exasol 2026.2**, the
version below). So vectors are stored **long and narrow** — one row per dimension — and cosine similarity is an ordinary join and
`GROUP BY`:

```sql
SELECT v.NCT_ID, v.CHUNK_ID, SUM(v.VAL * q.VAL) AS SIM
FROM CT.ELIG_VECTORS v JOIN QV q ON q.DIM = v.DIM
GROUP BY v.NCT_ID, v.CHUNK_ID
```

Vectors are L2-normalised at build time, so a dot product *is* cosine. 25.8M
rows scan in about 5 seconds **on the machine in Tested on** — that figure is
hardware- and VM-bound, so treat it as an order of magnitude, not a benchmark. Everything expensive — the TF-IDF fit, the SVD —
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

Ask `bin/search.py "exclude prior anti-PD-1"` and the top five come back like
this — four of them carrying the *same criterion text*, filed by different
sponsors into opposite sections:

| rank | section | cosine | BM25 | criterion |
|---|---|---|---|---|
| 2 | **INCLUSION** | 0.9842 | 24.00 | "Any toxicity that led to permanent discontinuation of prior anti-PD-1/PD-L1 immunotherapy" |
| 3 | EXCLUSION | 0.9842 | 24.00 | the same sentence |
| 4 | EXCLUSION | 0.9842 | 24.00 | the same sentence |
| 5 | **INCLUSION** | 0.9842 | 24.00 | the same sentence |

Neither ranker can separate them, and that is not a tuning problem: the cosine
is **identical to four decimal places** and the BM25 score is identical too,
because the text *is* identical. Nothing in the sentence says which half of the
eligibility criteria it was filed under. Only `CRITERION_SECTION` does. The reason is one query away:

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
| text alone | 0.679 | 0.767 |
| with the structured section filter | **0.858** | 1.000 |
| — hybrid questions (8) | 0.719 → 0.925 | 0.775 → 1.000 |
| — polarity questions (4) | 0.600 → **0.725** | 0.750 → 1.000 |

**Read the recall column, not the purity column.** Purity of 1.000 is true by
construction: once the query filters to one section, every hit comes from that
section by definition. It is reported only to show the filter does what it says.
The finding is recall — 0.679 → 0.858 across 12 questions, without retraining
anything.

The worst single case is `pol-02`, *"no prior systemic chemotherapy for
metastatic disease"* — **recall 0.15**, because the negation this time is in the
**query**, and the analyzer deletes it there too.

## A second failure the section filter cannot fix

Ask for `EGFR mutation positive`, filtered to INCLUSION, and at **rank 13**
comes *"EGFR mutation or ALK mutation was **negative**"* — cosine 0.9455, in
INCLUSION, the section that was asked for. A more clearly opposite example — *"EGFR mutation
negative and ALK fusion negative"* in `NCT07633873`, where both terms are negated —
sits further down at rank 57. These ranks
are recomputed on every run rather than quoted, because a rank changes whenever
the corpus does. Here `negative` is **not** a
stopword — it survives tokenisation intact. The vector space simply does not encode that it inverts the
meaning, and BM25 sees a term match. Both the right and wrong criteria sit in
INCLUSION, so **the structured section filter offers no rescue at all**: recall
stays at 0.65 even with it applied (`pol-04`).

So there are two distinct polarity failures, not one:

| Failure | mechanism | fixable by the section column? |
|---|---|---|
| "no prior treatment with X" | stopword deletion — `no` is removed before scoring | Yes, partly |
| "EGFR mutation negative" | antonymy — the token survives, the meaning does not | **No** |

Polarity is the category the structured filter helps *least*, because the
retrieval still cannot tell the two sentences apart; the filter only stops it
looking in the wrong half.

## Honesty

- **The eval is circular, and the recall gain is overstated because of it.** All
  12 gold sets are `snapshot-sql` — predicates over the loaded data — and all 12
  select on `CRITERION_SECTION`, the very column whose use is being credited with
  the improvement. A gold set defined by a column will reward filtering on that
  column. The measurement is reproducible and auditable; it is **not** independent
  evidence, and the true gain against a gold set built without that column is
  unknown. Questions derived from published landscape reviews — ground truth
  assembled by people who never saw this pipeline — would settle it, and are not
  included.
- The vector side is TF-IDF + 96-dim SVD, not a transformer. It explains only
  18% of variance and its similarities are compressed into a narrow band near
  1.0, so *relative* order carries the signal and absolute scores mean little.
  A transformer would retrieve better and would be **just as blind to `no`**.
- ClinicalTrials.gov's API publishes no rate limits, but the snapshot is committed
  to this repo regardless, so a demonstration never depends on the network.

# The demo screen

```
./app/run.sh            # http://127.0.0.1:8503
```

Three pages, built as an *argument* rather than a tool, so it works with nobody
standing next to it:

| Page | What it covers |
|---|---|
| 1 · The challenge | the four shapes the answer is spread across, and what one engine changes |
| 2 · The demo | ask a question (agent writes the SQL) **or** generate a landscape report |
| 3 · How Exasol does it | the architecture, vectors as rows, the virtual schema, and the limits |

Every number is queried live when the page loads — nothing is typed in. A
**Walkthrough** mode reduces the same argument to six full-screen steps for
presenting to a room.

Two of the pages end by admitting a limit, which is deliberate: the stopword
proof is computed by `CT.QUERY_TERMS` on the spot, and the antonymy blind spot
reports its *current* rank rather than a remembered one.

## Tested on

Every figure in this README was produced on this configuration. Timings in
particular will move with hardware and VM size.

| | |
|---|---|
| Exasol | Personal **2.3.0**, engine **2026.2**, single node |
| VM | 2 vCPU, Apple Virtualization framework |
| Host | macOS 26.6.1, Apple silicon |
| Python | 3.12+, dependencies pinned in `requirements.txt` |
| Containers | Docker Desktop, for the offline embedding step and the two lake containers |
| Model | `claude-opus-5` via `exasol-mcp-server` |

## Licence

MIT — see [LICENSE](LICENSE).

The data in `data/` is not covered by this licence:

- `trials_snapshot.json.gz` — [ClinicalTrials.gov](https://clinicaltrials.gov), a
  public registry of the US National Library of Medicine. See their
  [terms and conditions](https://clinicaltrials.gov/about-site/terms-conditions).
- `pubmed_snapshot.json.gz` — [PubMed](https://pubmed.ncbi.nlm.nih.gov/), also NLM,
  under its own [copyright and reuse terms](https://www.ncbi.nlm.nih.gov/home/about/policies/).
  Records are bibliographic metadata; individual abstracts may carry publisher
  copyright, and reuse beyond this demo is your responsibility to check.
