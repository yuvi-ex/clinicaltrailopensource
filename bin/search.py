#!/usr/bin/env python3
"""Render and run the hybrid-search template. Shared by the demo and the eval.

Deliberately thin: the SQL is the artefact, this only substitutes placeholders
and prints what it ran, so nothing about the retrieval hides in Python.
"""
import argparse, csv, io, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMPL = os.path.join(ROOT, "sql", "05_hybrid_search.sql.tmpl")


def esc(s):
    return s.replace("'", "''")


def build(query, section=None, trial_filter="", topk=10):
    sql = open(TMPL).read()
    sec = ""
    if section:
        # The structured rescue: restrict to a criteria section BEFORE scoring.
        sec = "AND c.CRITERION_SECTION = '%s'" % esc(section)
    return (sql.replace("{{QUERY}}", esc(query))
               .replace("{{SECTION_FILTER}}", sec)
               .replace("{{TRIAL_FILTER}}", trial_filter or "")
               .replace("{{TOPK}}", str(int(topk))))


def run(sql, show=False):
    if show:
        print(sql, file=sys.stderr)
    p = subprocess.run(["exapump", "sql", "-f", "csv"], input=sql,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    # exapump prints a header line, the CSV, then a summary line.
    lines = [l for l in p.stdout.splitlines()]
    try:
        i = next(i for i, l in enumerate(lines) if l.startswith("NCT_ID,"))
    except StopIteration:
        return []
    body = [l for l in lines[i:] if l and not l.endswith("failed")]
    return list(csv.DictReader(io.StringIO("\n".join(body))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--section", choices=["INCLUSION", "EXCLUSION", "UNKNOWN"])
    ap.add_argument("--filter", default="", help="extra SQL on CT.V_LANDSCAPE t")
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--show-sql", action="store_true")
    a = ap.parse_args()
    rows = run(build(a.query, a.section, a.filter, a.topk), show=a.show_sql)
    if not rows:
        print("(no rows)")
        return
    w = [("SEC", 9), ("VEC_SIM", 8), ("BM25", 7), ("RRF", 9), ("NCT_ID", 12), ("PHASE", 14)]
    print("  ".join(h.ljust(n) for h, n in w) + "  CRITERION")
    for r in rows:
        print("  ".join([r["CRITERION_SECTION"][:9].ljust(9),
                         (r["VEC_SIM"] or "-").ljust(8),
                         (r["BM25"] or "-").ljust(7),
                         (r["RRF"] or "-").ljust(9),
                         r["NCT_ID"].ljust(12),
                         r["PHASE"][:14].ljust(14),
                         r["CRITERION"][:100]]))


if __name__ == "__main__":
    main()
