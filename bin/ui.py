#!/usr/bin/env python3
"""A local page that explains itself: dataset, model, architecture, and results,
alongside the live search probe.

Stdlib only -- no pip, no venv, and no second Exasol connection pool parked
against the 20-connection ceiling. It imports bin/search.py rather than
reimplementing anything, so the page, the CLI and the eval harness cannot
disagree about what the retrieval does.
"""
import json, os, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import search                      # noqa: E402
import stats as statsmod           # noqa: E402
from ui_page import PAGE           # noqa: E402

PORT = int(os.environ.get("PORT", "8899"))

PRESETS = [
    ["The stopword failure", "prior treatment with an anti-PD-1 or anti-PD-L1 antibody",
     "EXCLUSION", ""],
    ["The antonymy failure", "EGFR mutation positive", "INCLUSION",
     "AND t.INDICATION='NSCLC'"],
    ["Worst recall in the eval", "no prior systemic chemotherapy for metastatic disease",
     "INCLUSION", ""],
    ["Structured + text", "EGFR mutation positive", "INCLUSION",
     "AND t.INDICATION='NSCLC' AND t.PHASE='PHASE3' AND t.STATUS_GROUP='Open'"],
    ["An easy case", "interstitial lung disease or pneumonitis", "EXCLUSION", ""],
]

# The stats query set takes a couple of seconds; the page asks for it once on
# load, so cache it and let a reload past the TTL pick up new data.
_cache = {"at": 0.0, "val": None}
_TTL = 120.0


def cached_stats():
    import time
    now = time.time()
    if _cache["val"] is None or now - _cache["at"] > _TTL:
        v = statsmod.collect()
        v["presets"] = PRESETS
        _cache.update(at=now, val=v)
    return _cache["val"]


def query_terms(text):
    """Ask the database for the terms, so the page shows the SAME tokenisation
    the scoring uses rather than a JavaScript approximation of it."""
    sql = ("SELECT TERM FROM (SELECT CT.QUERY_TERMS('%s') FROM DUAL) ORDER BY TERM"
           % text.replace("'", "''"))
    return [r["TERM"] for r in statsmod.q(sql)]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        b = body.encode("utf8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        try:
            self.wfile.write(b)
        except BrokenPipeError:
            pass

    def _json(self, obj):
        self._send(200, json.dumps(obj), "application/json")

    def do_GET(self):
        u = urlparse(self.path)
        p = parse_qs(u.query)
        try:
            if u.path == "/":
                return self._send(200, PAGE, "text/html; charset=utf-8")
            if u.path == "/stats":
                return self._json(cached_stats())
            if u.path == "/tokens":
                a = query_terms((p.get("a") or [""])[0])
                b = query_terms((p.get("b") or [""])[0])
                sa, sb = set(a), set(b)
                return self._json({"a": a, "b": b,
                                   "shared": sorted(sa & sb),
                                   "only_a": sorted(sa - sb),
                                   "only_b": sorted(sb - sa)})
            if u.path == "/search":
                q = (p.get("q") or [""])[0]
                section = (p.get("section") or [None])[0]
                filt = (p.get("filter") or [""])[0]
                topk = int((p.get("topk") or ["10"])[0])
                out = {}
                for name, sec in (("text_only", None), ("with_section", section)):
                    sql = search.build(q, sec, filt, topk)
                    out[name] = {"sql": sql, "rows": search.run(sql)}
                return self._json(out)
            return self._send(404, "not found", "text/plain")
        except Exception as e:                                   # noqa: BLE001
            return self._json({"error": str(e)[:600]})


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"  probe UI -> http://127.0.0.1:{PORT}/")
    print("  tabs: Probe / Dataset / Model / Architecture / Results")
    print("  ctrl-c to stop")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}/")).start()
    srv.serve_forever()
