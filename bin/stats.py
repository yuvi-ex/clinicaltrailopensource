#!/usr/bin/env python3
"""Live facts for the UI. Every number on the page comes from the database on
request, so the page cannot drift from the data the way a hand-written figure
in a slide does."""
import csv, io, json, os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def q(sql):
    p = subprocess.run(["exapump", "sql", "-f", "csv"], input=sql,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip()[:300])
    # exapump frames results as: a "[1/1] <sql> N rows" banner, the CSV
    # (header first), then a "N statements executed" footer. Do NOT sniff for a
    # comma to find the header -- a single-column result like TERM has none,
    # which silently yielded zero rows.
    lines = p.stdout.splitlines()
    start = next((i + 1 for i, l in enumerate(lines) if l.startswith("[")), 0)
    body = [l for l in lines[start:]
            if l.strip() and "statement executed" not in l]
    if not body:
        return []
    return list(csv.DictReader(io.StringIO("\n".join(body))))


def dist(sql, label="LABEL", value="N"):
    rows = q(sql)
    out = [{"label": r[label], "n": int(float(r[value]))} for r in rows]
    tot = sum(r["n"] for r in out) or 1
    for r in out:
        r["pct"] = round(100 * r["n"] / tot, 1)
    return out


def collect():
    s = {}
    r = q("""SELECT (SELECT COUNT(*) FROM CT.TRIALS) AS TRIALS,
                    (SELECT COUNT(*) FROM CT.ELIG_CHUNKS) AS CHUNKS,
                    (SELECT COUNT(*) FROM CT.ELIG_VECTORS) AS VECTOR_ROWS,
                    (SELECT COUNT(*) FROM CT.CHUNK_TOKENS) AS TOKEN_ROWS,
                    (SELECT COUNT(*) FROM CT.TERM_IDF) AS VOCAB,
                    (SELECT COUNT(*) FROM CT.TRIAL_OUTCOMES) AS OUTCOMES,
                    (SELECT COUNT(DISTINCT COUNTRY) FROM CT.TRIAL_COUNTRIES) AS COUNTRIES,
                    (SELECT COUNT(DISTINCT LEAD_SPONSOR) FROM CT.TRIALS) AS SPONSORS
             FROM DUAL""")[0]
    s["totals"] = {k.lower(): int(float(v)) for k, v in r.items()}
    s["sections"] = dist("SELECT CRITERION_SECTION AS LABEL, COUNT(*) AS N "
                         "FROM CT.ELIG_CHUNKS GROUP BY 1 ORDER BY N DESC")
    s["phase"] = dist("SELECT PHASE AS LABEL, COUNT(*) AS N FROM CT.V_TRIALS "
                      "GROUP BY 1 ORDER BY N DESC")
    s["region"] = dist("SELECT REGION AS LABEL, COUNT(DISTINCT NCT_ID) AS N "
                       "FROM CT.V_TRIAL_GEOGRAPHY GROUP BY 1 ORDER BY N DESC")
    s["status"] = dist("SELECT STATUS_GROUP AS LABEL, COUNT(*) AS N FROM CT.V_TRIALS "
                       "GROUP BY 1 ORDER BY N DESC")
    s["sponsor"] = dist("SELECT SPONSOR_TYPE AS LABEL, COUNT(*) AS N FROM CT.V_TRIALS "
                        "GROUP BY 1 ORDER BY N DESC")
    s["indication"] = dist("SELECT INDICATION AS LABEL, COUNT(*) AS N FROM CT.TRIALS "
                           "GROUP BY 1 ORDER BY N DESC")
    s["endpoint"] = dist("SELECT ENDPOINT_CATEGORY AS LABEL, COUNT(*) AS N "
                         "FROM CT.V_TRIAL_ENDPOINTS WHERE OUTCOME_KIND='PRIMARY' "
                         "GROUP BY 1 ORDER BY N DESC")
    s["comparator"] = dist("SELECT COMPARATOR_DESIGN AS LABEL, COUNT(*) AS N "
                           "FROM CT.V_LANDSCAPE GROUP BY 1 ORDER BY N DESC")
    s["top_countries"] = dist("SELECT COUNTRY AS LABEL, COUNT(DISTINCT NCT_ID) AS N "
                              "FROM CT.TRIAL_COUNTRIES GROUP BY 1 ORDER BY N DESC LIMIT 10")
    meta = os.path.join(ROOT, ".work", "art", "elig_model.meta.json")
    s["model_meta"] = json.load(open(meta)) if os.path.exists(meta) else {}
    ev = os.path.join(ROOT, "eval", "results.json")
    s["eval"] = json.load(open(ev)) if os.path.exists(ev) else None
    snap = os.path.join(ROOT, "data", "trials_snapshot.json.gz")
    if os.path.exists(snap):
        import gzip
        s["snapshot"] = json.load(gzip.open(snap, "rt"))["_meta"]
        s["snapshot"]["bytes"] = os.path.getsize(snap)
    return s


if __name__ == "__main__":
    print(json.dumps(collect(), indent=2)[:1500])
