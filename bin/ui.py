#!/usr/bin/env python3
"""A small local UI for poking the retrieval. Stdlib only -- no pip, no venv.

Runs the SAME code path as bin/search.py and the eval harness, so what you see
here is what the numbers were measured on. Its one opinion: it can run a query
BOTH ways at once -- text alone, and with the structured section filter -- because
the difference between those two is the entire point of the demo.
"""
import html, json, os, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import search  # noqa: E402

PORT = int(os.environ.get("PORT", "8899"))

PRESETS = [
    ("The stopword failure", "prior treatment with an anti-PD-1 or anti-PD-L1 antibody",
     "EXCLUSION", ""),
    ("The antonymy failure", "EGFR mutation positive", "INCLUSION",
     "AND t.INDICATION='NSCLC'"),
    ("Worst recall in the eval", "no prior systemic chemotherapy for metastatic disease",
     "INCLUSION", ""),
    ("Structured + text", "EGFR mutation positive", "INCLUSION",
     "AND t.INDICATION='NSCLC' AND t.PHASE='PHASE3' AND t.STATUS_GROUP='Open'"),
    ("Easy case", "interstitial lung disease or pneumonitis", "EXCLUSION", ""),
]

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>Trial retrieval probe</title><style>
:root{--bg:#fbfaf8;--fg:#1a1a19;--mut:#6b6a66;--line:#e2e0da;--card:#fff;
      --bad:#b4232a;--badbg:#fdf0ef;--good:#1f6f43;--accent:#2f5fd0}
@media(prefers-color-scheme:dark){:root{--bg:#161614;--fg:#eceae5;--mut:#9a978f;
  --line:#302d28;--card:#1e1c19;--badbg:#33201f;--bad:#f0837f;--good:#6cc48d;--accent:#8fb2ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:22px 20px 60px}
h1{font-size:17px;margin:0 0 3px}
.sub{color:var(--mut);font-size:12.5px;margin-bottom:18px}
form{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
label{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
 color:var(--mut);margin-bottom:5px}
input[type=text],select{width:100%;padding:8px 10px;font:inherit;color:var(--fg);
 background:var(--bg);border:1px solid var(--line);border-radius:6px}
.row{display:flex;gap:12px;flex-wrap:wrap;margin-top:11px}
.row>div{flex:1;min-width:150px}
button{font:inherit;padding:8px 15px;border-radius:6px;border:1px solid var(--line);
 background:var(--card);color:var(--fg);cursor:pointer}
button.go{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.presets{margin:12px 0 0;display:flex;gap:7px;flex-wrap:wrap}
.presets button{font-size:12px;padding:5px 10px;color:var(--mut)}
table{width:100%;border-collapse:collapse;margin-top:9px;font-size:12.5px}
th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;
 color:var(--mut);border-bottom:1px solid var(--line);padding:6px 7px;font-weight:600}
td{padding:6px 7px;border-bottom:1px solid var(--line);vertical-align:top}
tr.wrong{background:var(--badbg)}
tr.wrong td.sec{color:var(--bad);font-weight:700}
.sec{white-space:nowrap;font-size:11px}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--mut)}
.nct{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;white-space:nowrap}
.panes{display:grid;grid-template-columns:1fr;gap:16px;margin-top:20px}
@media(min-width:900px){.panes{grid-template-columns:1fr 1fr}}
.pane{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px;
 overflow-x:auto}
.pane h2{font-size:13px;margin:0 0 2px}
.pane .note{font-size:11.5px;color:var(--mut);margin-bottom:4px}
.flag{margin-top:10px;padding:9px 11px;border-radius:7px;font-size:12.5px;
 background:var(--badbg);color:var(--bad);border:1px solid currentColor}
.ok{background:transparent;color:var(--good)}
details{margin-top:14px}summary{cursor:pointer;color:var(--mut);font-size:12px}
pre{background:var(--card);border:1px solid var(--line);border-radius:7px;padding:11px;
 overflow-x:auto;font-size:11.5px;line-height:1.45}
.spin{color:var(--mut);font-size:12.5px;margin-top:14px}
</style></head><body><div class="wrap">
<h1>Trial retrieval probe</h1>
<div class="sub">12,404 trials &middot; 268,912 eligibility chunks &middot; 25.8M vector rows.
Same code path as <code>bin/search.py</code> and the eval harness.</div>

<form id="f" onsubmit="go(event)">
  <label for="q">Question</label>
  <input type="text" id="q" name="q" value="prior treatment with an anti-PD-1 or anti-PD-L1 antibody">
  <div class="row">
    <div><label for="section">Intended section</label>
      <select id="section"><option value="EXCLUSION">EXCLUSION</option>
      <option value="INCLUSION">INCLUSION</option></select></div>
    <div><label for="topk">Rows</label>
      <select id="topk"><option>6</option><option selected>10</option><option>20</option></select></div>
    <div style="flex:2"><label for="filter">Structured filter (on <code>t</code> = V_LANDSCAPE)</label>
      <input type="text" id="filter" placeholder="AND t.PHASE='PHASE3' AND t.STATUS_GROUP='Open'"></div>
  </div>
  <div class="row" style="align-items:flex-end">
    <div style="flex:0 0 auto"><button class="go" type="submit">Run both ways</button></div>
  </div>
  <div class="presets" id="presets"></div>
</form>

<div id="out"></div>
<script>
const PRESETS = __PRESETS__;
const pc = document.getElementById('presets');
PRESETS.forEach(p => { const b=document.createElement('button'); b.type='button';
  b.textContent=p[0]; b.onclick=()=>{document.getElementById('q').value=p[1];
  document.getElementById('section').value=p[2];
  document.getElementById('filter').value=p[3]; go();}; pc.appendChild(b); });

function esc(s){return (s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}

function table(rows, want){
  if(!rows.length) return '<div class="spin">no rows</div>';
  let h='<table><thead><tr><th>Sec</th><th class="num">Cos</th><th class="num">BM25</th>'
    +'<th class="num">RRF</th><th>NCT ID</th><th>Phase</th><th>Criterion</th></tr></thead><tbody>';
  for(const r of rows){
    const wrong = want && r.CRITERION_SECTION !== want;
    h+='<tr class="'+(wrong?'wrong':'')+'"><td class="sec">'+esc(r.CRITERION_SECTION)+'</td>'
      +'<td class="num">'+esc(r.VEC_SIM)+'</td><td class="num">'+esc(r.BM25)+'</td>'
      +'<td class="num">'+esc(r.RRF)+'</td><td class="nct">'+esc(r.NCT_ID)+'</td>'
      +'<td class="sec">'+esc(r.PHASE)+'</td><td>'+esc(r.CRITERION)+'</td></tr>';
  }
  return h+'</tbody></table>';
}

async function go(ev){
  if(ev) ev.preventDefault();
  const q=document.getElementById('q').value,
        section=document.getElementById('section').value,
        filter=document.getElementById('filter').value,
        topk=document.getElementById('topk').value;
  const out=document.getElementById('out');
  out.innerHTML='<div class="spin">scanning 25.8M vector rows, twice&hellip;</div>';
  try{
    const r=await fetch('/search?'+new URLSearchParams({q,section,filter,topk}));
    const d=await r.json();
    if(d.error){out.innerHTML='<div class="flag">'+esc(d.error)+'</div>';return}
    const bad=d.text_only.rows.filter(x=>x.CRITERION_SECTION!==section).length;
    out.innerHTML=
      '<div class="panes">'
      +'<div class="pane"><h2>Text alone</h2><div class="note">vector + BM25, fused with RRF</div>'
      + table(d.text_only.rows, section)
      + (bad? '<div class="flag"><b>'+bad+' of '+d.text_only.rows.length
             +'</b> top rows are from the wrong section &mdash; the ranking cannot see polarity.</div>'
            : '<div class="flag ok">All top rows already in the intended section.</div>')
      +'</div>'
      +'<div class="pane"><h2>With the section column</h2><div class="note">structured filter applied BEFORE scoring</div>'
      + table(d.with_section.rows, section)
      +'<div class="flag ok">Section purity 100% by construction. Whether the right rows '
      +'rose is the question the eval answers.</div></div></div>'
      +'<details><summary>The SQL it ran (text-only variant)</summary><pre>'
      +esc(d.text_only.sql)+'</pre></details>';
  }catch(e){out.innerHTML='<div class="flag">'+esc(e)+'</div>'}
}
go();
</script></div></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        b = body.encode("utf8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self._send(200, PAGE.replace("__PRESETS__", json.dumps(PRESETS)),
                              "text/html; charset=utf-8")
        if u.path != "/search":
            return self._send(404, "not found", "text/plain")
        p = parse_qs(u.query)
        q = (p.get("q") or [""])[0]
        section = (p.get("section") or [None])[0]
        filt = (p.get("filter") or [""])[0]
        topk = int((p.get("topk") or ["10"])[0])
        try:
            out = {}
            for name, sec in (("text_only", None), ("with_section", section)):
                sql = search.build(q, sec, filt, topk)
                out[name] = {"sql": sql, "rows": search.run(sql)}
            return self._send(200, json.dumps(out), "application/json")
        except Exception as e:                                   # noqa: BLE001
            return self._send(200, json.dumps({"error": str(e)[:600]}),
                              "application/json")


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"  probe UI -> http://127.0.0.1:{PORT}/")
    print("  ctrl-c to stop")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}/")).start()
    srv.serve_forever()
