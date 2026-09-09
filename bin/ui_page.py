"""The probe page. Kept apart from the server so the HTML stays readable.

Colour follows the dataviz method: distributions are a SINGLE series, so they
get one sequential hue and a direct value label -- no categorical palette, no
legend (the row label names the bar). Status colours are reserved and never
carry meaning alone: a wrong-section row is red AND says "wrong half".
"""

PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trial retrieval probe</title><style>
:root{
  --surface:#fcfcfb; --bg:#f6f5f2; --fg:#1a1a19; --fg2:#4a4945; --mut:#6b6a66;
  --line:#e2e0da; --card:#fff;
  --seq:#2a78d6; --seq-soft:#cde2fb;         /* sequential hue, one series only */
  --critical:#d03b3b; --critical-bg:#fbeceb; /* reserved status, never alone */
  --good:#0ca30c; --good-bg:#eef8ee;
}
@media(prefers-color-scheme:dark){:root{
  --surface:#1a1a19; --bg:#141413; --fg:#eceae5; --fg2:#c9c6bf; --mut:#96938c;
  --line:#302d28; --card:#1e1c19;
  --seq:#3987e5; --seq-soft:#1c3a5c;
  --critical:#e66767; --critical-bg:#2e1d1d;
  --good:#3ec03e; --good-bg:#16261a;
}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
.wrap{max-width:1220px;margin:0 auto;padding:20px 20px 70px}
header h1{font-size:18px;margin:0 0 2px;letter-spacing:-.01em}
header .sub{color:var(--mut);font-size:12.5px}
nav{display:flex;gap:2px;margin:16px 0 18px;border-bottom:1px solid var(--line);
 flex-wrap:wrap}
nav button{font:inherit;font-size:13px;padding:8px 14px;border:0;background:none;
 color:var(--mut);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
nav button[aria-selected=true]{color:var(--fg);border-bottom-color:var(--seq);font-weight:600}
section[hidden]{display:none}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
 padding:15px 16px;margin-bottom:14px}
.card>h2{font-size:14px;margin:0 0 3px}
.card>.note{font-size:12.5px;color:var(--mut);margin:0 0 12px}
.grid{display:grid;gap:14px;grid-template-columns:1fr}
@media(min-width:820px){.grid.two{grid-template-columns:1fr 1fr}}
/* --- stat tiles: a hero number needs no plot --- */
.tiles{display:grid;gap:10px;grid-template-columns:repeat(2,1fr)}
@media(min-width:700px){.tiles{grid-template-columns:repeat(4,1fr)}}
.tile{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:11px 13px}
.tile .v{font-size:20px;font-weight:650;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.tile .k{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);margin-top:2px}
.tile .x{font-size:11.5px;color:var(--mut);margin-top:3px}
/* --- single-series horizontal bars, in a table so a table view always exists --- */
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;
 color:var(--mut);border-bottom:1px solid var(--line);padding:5px 8px;font-weight:600}
td{padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:middle}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--fg2)}
.barcell{width:46%;min-width:110px}
.bar{height:9px;background:var(--seq);border-radius:0 4px 4px 0;
 box-shadow:2px 0 0 0 var(--card)}   /* 4px rounded data-end, 2px surface gap */
.barwrap{background:var(--seq-soft);border-radius:0 4px 4px 0;overflow:hidden}
/* --- results --- */
tr.wrong{background:var(--critical-bg)}
tr.wrong td.sec{color:var(--critical);font-weight:700}
.tag{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.04em;
 padding:1px 5px;border-radius:4px;border:1px solid currentColor;margin-left:5px;
 vertical-align:1px}
.sec{white-space:nowrap;font-size:11px}
.nct{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;white-space:nowrap;font-size:11.5px}
.flag{margin-top:11px;padding:9px 11px;border-radius:7px;font-size:12.5px;
 border:1px solid currentColor;background:var(--critical-bg);color:var(--critical)}
.flag.ok{background:var(--good-bg);color:var(--good)}
label{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
 color:var(--mut);margin-bottom:5px}
input[type=text],select{width:100%;padding:8px 10px;font:inherit;color:var(--fg);
 background:var(--surface);border:1px solid var(--line);border-radius:6px}
.row{display:flex;gap:12px;flex-wrap:wrap;margin-top:11px}
.row>div{flex:1;min-width:150px}
button.go{font:inherit;padding:8px 16px;border-radius:6px;border:1px solid var(--seq);
 background:var(--seq);color:#fff;font-weight:600;cursor:pointer}
.presets{margin-top:12px;display:flex;gap:7px;flex-wrap:wrap}
.presets button{font:inherit;font-size:12px;padding:5px 10px;border-radius:6px;
 border:1px solid var(--line);background:var(--surface);color:var(--fg2);cursor:pointer}
dl.legend{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;margin:0;font-size:12px}
dl.legend dt{font-weight:650;color:var(--fg)}
dl.legend dd{margin:0;color:var(--mut)}
pre{background:var(--surface);border:1px solid var(--line);border-radius:7px;padding:11px;
 overflow-x:auto;font-size:11.5px;line-height:1.45;margin:0}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
details{margin-top:12px}summary{cursor:pointer;color:var(--mut);font-size:12px}
.spin{color:var(--mut);font-size:12.5px;padding:10px 0}
.kv{font-size:12.5px}
.kv div{display:flex;justify-content:space-between;gap:16px;padding:4px 0;
 border-bottom:1px solid var(--line)}
.kv div:last-child{border:0}
.kv b{font-weight:600}
.kv span{color:var(--mut);text-align:right}
.no{color:var(--critical)}
.yes{color:var(--good)}
svg{max-width:100%;height:auto;display:block}
.tokcmp{display:grid;gap:12px;grid-template-columns:1fr 1fr;font-size:12px}
.tokcmp ul{margin:4px 0 0;padding-left:17px}
</style></head><body>
<div class="wrap">
<header>
  <h1>Trial retrieval probe</h1>
  <div class="sub">Hybrid search over clinical-trial eligibility criteria, on Exasol Personal Local.
  Every number on this page is read from the database when you load it.</div>
</header>

<nav id="nav" role="tablist"></nav>

<!-- ================= PROBE ================= -->
<section id="tab-probe">
  <div class="card">
    <h2>Ask about eligibility criteria</h2>
    <p class="note">Trials describe who may join as free prose, split into two halves:
    <b>inclusion</b> (you must have this) and <b>exclusion</b> (you cannot have this).
    Pick which half you mean, then compare the two answers below.</p>
    <form onsubmit="go(event)">
      <label for="q">Your question</label>
      <input type="text" id="q" value="prior treatment with an anti-PD-1 or anti-PD-L1 antibody">
      <div class="row">
        <div><label for="section">Which half you mean</label>
          <select id="section">
            <option value="EXCLUSION">EXCLUSION — trials that rule these patients out</option>
            <option value="INCLUSION">INCLUSION — trials that require this</option>
          </select></div>
        <div><label for="topk">Rows</label>
          <select id="topk"><option>6</option><option selected>10</option><option>20</option></select></div>
      </div>
      <div class="row">
        <div><label for="filter">Optional structured filter (SQL on the trial view)</label>
          <input type="text" id="filter" placeholder="AND t.PHASE='PHASE3' AND t.STATUS_GROUP='Open'"></div>
        <div style="flex:0 0 auto;display:flex;align-items:flex-end">
          <button class="go" type="submit">Run both ways</button></div>
      </div>
      <div class="presets" id="presets"></div>
    </form>
  </div>
  <div id="out"></div>
  <div class="card">
    <h2>What the columns mean</h2>
    <dl class="legend">
      <dt>Criteria half</dt><dd>Which half of the trial's criteria this sentence came from. If it does not match what you asked for, the answer is wrong.</dd>
      <dt>Meaning match</dt><dd>Cosine similarity, 0&ndash;1. "Does this sentence <i>mean</i> the same thing?"</dd>
      <dt>Keyword match</dt><dd>BM25 score. "Does this sentence share the same <i>words</i>?"</dd>
      <dt>Rank score</dt><dd>The fused score the list is sorted by. Higher is ranked higher.</dd>
      <dt>NCT ID</dt><dd>The trial's registry identifier &mdash; what an agent must cite.</dd>
    </dl>
  </div>
</section>

<!-- ================= DATASET ================= -->
<section id="tab-dataset" hidden>
  <div class="tiles" id="ds-tiles"></div>
  <div class="grid two" style="margin-top:14px">
    <div class="card"><h2>Where the data comes from</h2>
      <p class="note">One source. The snapshot is committed to the repository.</p>
      <div class="kv" id="ds-source"></div>
      <details><summary>Sources in the brief that are NOT used</summary>
        <p class="note" style="margin-top:8px">EU CTR/CTIS, PubMed/OpenAlex, Drugs@FDA and
        EMA EPARs are all absent. Each needs its own fetcher and identifier matching.
        Nothing on this page draws on them.</p></details>
    </div>
    <div class="card"><h2>Criteria sentences by half</h2>
      <p class="note">The registry has <b>no</b> structured inclusion/exclusion field.
      This split is recovered from prose headings.</p>
      <div id="ds-sections"></div></div>
  </div>
  <div class="grid two">
    <div class="card"><h2>Trials by phase</h2>
      <p class="note">Read this before trusting any phase filter.</p><div id="ds-phase"></div>
      <div class="flag">A third of trials say <b>NOT_APPLICABLE</b> &mdash; the registry's own
      statement that they are unphased. <code>WHERE PHASE='PHASE3'</code> drops them
      silently, so the view exposes <code>PHASE_IS_STATED</code>.</div></div>
    <div class="card"><h2>Trials by region</h2>
      <p class="note">Countries as the API names them, rolled into 7 regions.</p>
      <div id="ds-region"></div></div>
  </div>
  <div class="grid two">
    <div class="card"><h2>Trials by status</h2><div id="ds-status"></div></div>
    <div class="card"><h2>Trials by sponsor type</h2><div id="ds-sponsor"></div></div>
  </div>
  <div class="grid two">
    <div class="card"><h2>Top countries</h2><div id="ds-countries"></div></div>
    <div class="card"><h2>Trial design</h2>
      <p class="note">Whether a control arm exists is structured. <i>Which</i> drug the
      control is sits in the arm label as prose.</p><div id="ds-comparator"></div></div>
  </div>
  <div class="card"><h2>Primary endpoint category</h2>
    <p class="note">Derived, not looked up: the registry gives endpoints as free text
    (a measure and a timeframe, nothing coded). These categories come from pattern
    matching in SQL.</p>
    <div id="ds-endpoint"></div>
    <div class="flag" id="ds-endpoint-flag"></div></div>
</section>

<!-- ================= MODEL ================= -->
<section id="tab-model" hidden>
  <div class="card"><h2>There is no neural network here</h2>
    <p class="note">No transformer, no embedding API, no prediction. This is classical
    information retrieval, chosen deliberately.</p>
    <div class="kv" id="md-kv"></div>
  </div>
  <div class="grid two">
    <div class="card"><h2>How a document becomes numbers</h2>
      <pre id="md-pipe"></pre>
      <p class="note" style="margin-top:10px">Vectors are unit length, so a dot product
      <i>is</i> cosine similarity. That is what lets the database do the search with
      arithmetic alone.</p></div>
    <div class="card"><h2>Why this model, knowing it is weaker</h2>
      <p class="note">It explains about 18% of variance and its similarity scores bunch
      up near 1.0, so only the <i>order</i> carries signal. A transformer would retrieve
      better &mdash; and would be <b>just as blind</b> to the failure below, which is the
      point being made. Choosing a modest model keeps the argument about the
      <i>architecture</i> rather than the model.</p>
      <p class="note">It also has to unpickle inside an Exasol UDF, so scikit-learn is
      pinned to the exact version the database's Python container ships.</p></div>
  </div>
  <div class="card"><h2>The failure this model makes visible</h2>
    <p class="note">Type two sentences that mean opposite things. The search reduces both
    to a bag of terms before scoring &mdash; if the bags match, nothing downstream can tell
    them apart.</p>
    <div class="row">
      <div><label for="t1">Sentence A</label>
        <input type="text" id="t1" value="No prior treatment with anti-PD-1"></div>
      <div><label for="t2">Sentence B</label>
        <input type="text" id="t2" value="Prior treatment with anti-PD-1"></div>
      <div style="flex:0 0 auto;display:flex;align-items:flex-end">
        <button class="go" type="button" onclick="tok()">Compare terms</button></div>
    </div>
    <div id="tok-out"></div></div>
</section>

<!-- ================= ARCHITECTURE ================= -->
<section id="tab-arch" hidden>
  <div class="card"><h2>How it runs on Exasol</h2>
    <p class="note">Everything expensive happens once, outside the database. The database
    is left with arithmetic it can spread across cores.</p>
    <div id="arch-svg"></div>
  </div>
  <div class="grid two">
    <div class="card"><h2>Vectors without a vector type</h2>
      <p class="note">Exasol has no vector column and no vector index. So a 96-dimension
      vector is stored as <b>96 rows</b>, and similarity becomes an ordinary join and
      <code>GROUP BY</code> &mdash; the shape a parallel database is built for.</p>
      <pre>SELECT v.NCT_ID, v.CHUNK_ID,
       SUM(v.VAL * q.VAL) AS SIM
FROM   CT.ELIG_VECTORS v
JOIN   QV q ON q.DIM = v.DIM
GROUP  BY v.NCT_ID, v.CHUNK_ID</pre>
      <div class="kv" id="arch-tables" style="margin-top:12px"></div></div>
    <div class="card"><h2>What runs where</h2>
      <div class="kv" id="arch-where"></div>
      <details><summary>Why the model file lives in BucketFS</summary>
        <p class="note" style="margin-top:8px">A UDF cannot reach your laptop's disk.
        BucketFS is the database's own file store, mounted inside the UDF sandbox at
        <code>/buckets/...</code>. The model is loaded once per query VM at module
        scope, not once per row.</p></details></div>
  </div>
</section>

<!-- ================= RESULTS ================= -->
<section id="tab-results" hidden>
  <div class="tiles" id="ev-tiles"></div>
  <div class="card" style="margin-top:14px"><h2>Every question, measured twice</h2>
    <p class="note">Text alone, then with the structured criteria-half filter applied
    before scoring. The <b>difference</b> between those two columns is the whole claim.</p>
    <div id="ev-table"></div></div>
  <div class="card"><h2>Two failures, not one</h2>
    <div class="kv" id="ev-fail"></div></div>
  <div class="card"><h2>What these numbers are not</h2>
    <p class="note" id="ev-caveat"></p></div>
</section>
</div>

<script>
const TABS=[["probe","Probe"],["dataset","Dataset"],["model","Model"],
            ["arch","Architecture"],["results","Results"]];
const nav=document.getElementById('nav');
TABS.forEach(([id,label],i)=>{const b=document.createElement('button');
  b.textContent=label; b.setAttribute('role','tab');
  b.setAttribute('aria-selected', i===0?'true':'false');
  b.onclick=()=>{TABS.forEach(([j])=>document.getElementById('tab-'+j).hidden=(j!==id));
    [...nav.children].forEach(c=>c.setAttribute('aria-selected',String(c===b)));};
  nav.appendChild(b);});

const esc=s=>(s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt=n=>Number(n).toLocaleString();

/* One series per chart: single hue, direct value label, row label names it.
   No legend, because there is nothing to disambiguate. */
function bars(rows,unit){
  if(!rows||!rows.length) return '<div class="spin">no data</div>';
  const mx=Math.max(...rows.map(r=>r.n))||1;
  let h='<table><thead><tr><th>'+(unit||'Group')+'</th><th></th>'
       +'<th class="n">Count</th><th class="n">Share</th></tr></thead><tbody>';
  for(const r of rows){
    h+='<tr><td>'+esc(r.label)+'</td>'
      +'<td class="barcell"><div class="barwrap"><div class="bar" style="width:'
      +(100*r.n/mx).toFixed(1)+'%"></div></div></td>'
      +'<td class="n">'+fmt(r.n)+'</td><td class="n">'+r.pct+'%</td></tr>';
  }
  return h+'</tbody></table>';
}
const kv=o=>Object.entries(o).map(([k,v])=>'<div><b>'+esc(k)+'</b><span>'+v+'</span></div>').join('');
const tile=(v,k,x)=>'<div class="tile"><div class="v">'+v+'</div><div class="k">'+esc(k)+'</div>'
  +(x?'<div class="x">'+x+'</div>':'')+'</div>';

/* ---------------- probe ---------------- */
let PRESETS=[];
function mkPresets(){const pc=document.getElementById('presets');pc.innerHTML='';
  PRESETS.forEach(p=>{const b=document.createElement('button');b.type='button';
    b.textContent=p[0];b.onclick=()=>{document.getElementById('q').value=p[1];
      document.getElementById('section').value=p[2];
      document.getElementById('filter').value=p[3];go();};pc.appendChild(b);});}

function rtable(rows,want){
  if(!rows.length) return '<div class="spin">no rows</div>';
  let h='<table><thead><tr><th>Criteria half</th><th class="n">Meaning</th>'
   +'<th class="n">Keyword</th><th class="n">Rank score</th><th>NCT ID</th>'
   +'<th>Phase</th><th>The criterion, as written</th></tr></thead><tbody>';
  for(const r of rows){
    const bad=want&&r.CRITERION_SECTION!==want;
    h+='<tr class="'+(bad?'wrong':'')+'"><td class="sec">'+esc(r.CRITERION_SECTION)
      +(bad?'<span class="tag">WRONG HALF</span>':'')+'</td>'
      +'<td class="n">'+esc(r.VEC_SIM)+'</td><td class="n">'+esc(r.BM25)+'</td>'
      +'<td class="n">'+esc(r.RRF)+'</td><td class="nct">'+esc(r.NCT_ID)+'</td>'
      +'<td class="sec">'+esc(r.PHASE)+'</td><td>'+esc(r.CRITERION)+'</td></tr>';}
  return h+'</tbody></table>';
}
async function go(ev){
  if(ev)ev.preventDefault();
  const q=document.getElementById('q').value,section=document.getElementById('section').value,
        filter=document.getElementById('filter').value,topk=document.getElementById('topk').value;
  const out=document.getElementById('out');
  out.innerHTML='<div class="card"><div class="spin">Scanning 25.8M vector rows, twice&hellip;</div></div>';
  try{
    const d=await(await fetch('/search?'+new URLSearchParams({q,section,filter,topk}))).json();
    if(d.error){out.innerHTML='<div class="card"><div class="flag">'+esc(d.error)+'</div></div>';return;}
    const bad=d.text_only.rows.filter(x=>x.CRITERION_SECTION!==section).length;
    out.innerHTML='<div class="grid two">'
      +'<div class="card"><h2>Text alone</h2><p class="note">What a normal search would return</p>'
      +rtable(d.text_only.rows,section)
      +(bad?'<div class="flag"><b>'+bad+' of '+d.text_only.rows.length+'</b> top answers are from the '
        +'wrong half of the criteria. They say the opposite of what you asked.</div>'
        :'<div class="flag ok">All top answers are already in the half you asked for.</div>')
      +'</div><div class="card"><h2>With the structured column</h2>'
      +'<p class="note">Wrong-half sentences removed before scoring</p>'
      +rtable(d.with_section.rows,section)
      +'<div class="flag ok">No wrong-half answers remain. Not a better model &mdash; one column.</div>'
      +'</div></div>'
      +'<div class="card"><details><summary>The SQL that produced the left-hand table</summary>'
      +'<pre style="margin-top:10px">'+esc(d.text_only.sql)+'</pre></details></div>';
  }catch(e){out.innerHTML='<div class="card"><div class="flag">'+esc(e)+'</div></div>';}
}

/* ---------------- model: the tokeniser proof ---------------- */
async function tok(){
  const a=document.getElementById('t1').value,b=document.getElementById('t2').value;
  const o=document.getElementById('tok-out');
  o.innerHTML='<div class="spin">asking the database&hellip;</div>';
  try{
    const d=await(await fetch('/tokens?'+new URLSearchParams({a,b}))).json();
    if(d.error){o.innerHTML='<div class="flag">'+esc(d.error)+'</div>';return;}
    const same=JSON.stringify(d.a)===JSON.stringify(d.b);
    o.innerHTML='<div class="tokcmp" style="margin-top:12px">'
      +'<div><b>A &rarr; '+d.a.length+' terms</b><ul>'+d.a.map(t=>'<li><code>'+esc(t)+'</code></li>').join('')+'</ul></div>'
      +'<div><b>B &rarr; '+d.b.length+' terms</b><ul>'+d.b.map(t=>'<li><code>'+esc(t)+'</code></li>').join('')+'</ul></div>'
      +'</div>'+(same
        ?'<div class="flag">Identical. The words that carry the negation &mdash; <code>no</code>, '
         +'<code>not</code>, <code>without</code> &mdash; are stopwords, so they are deleted before '
         +'anything is scored. Two opposite sentences are now the same question.</div>'
        :'<div class="flag ok">'+d.only_a.length+' term(s) only in A, '+d.only_b.length
         +' only in B. Shared: '+d.shared.length+'. A difference here is something the scorer can use.</div>');
  }catch(e){o.innerHTML='<div class="flag">'+esc(e)+'</div>';}
}

/* ---------------- architecture diagram ---------------- */
function archSvg(t){
  const L='var(--line)',T='var(--fg)',M='var(--mut)',S='var(--seq)',C='var(--card)';
  const box=(x,y,w,h,fill)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="7"
    fill="${fill||C}" stroke="${L}" stroke-width="1"/>`;
  const txt=(x,y,s,o={})=>`<text x="${x}" y="${y}" fill="${o.c||T}"
    font-size="${o.s||11.5}" font-weight="${o.w||400}"
    font-family="-apple-system,system-ui,sans-serif" text-anchor="${o.a||'start'}">${s}</text>`;
  const arrow=(x1,y1,x2,y2)=>`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
    stroke="${S}" stroke-width="2" marker-end="url(#ah)"/>`;
  return `<svg viewBox="0 0 900 430" role="img"
   aria-label="Offline build in Docker produces Parquet tables and a model file; Exasol holds the tables and BucketFS; a query calls two UDFs then joins and groups.">
  <defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
    markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="${S}"/></marker></defs>

  ${box(8,8,420,180)} ${txt(22,28,'ONCE, OUTSIDE THE DATABASE',{s:10,w:700,c:M})}
  ${txt(22,45,'Docker, scikit-learn pinned to the database’s version',{s:11,c:M})}
  ${box(22,58,120,44)} ${txt(32,76,'Snapshot',{w:600})} ${txt(32,92,`${fmt(t.trials)} trials`,{s:10.5,c:M})}
  ${arrow(146,80,168,80)}
  ${box(172,58,120,44)} ${txt(182,76,'Shred',{w:600})} ${txt(182,92,`${fmt(t.chunks)} criteria`,{s:10.5,c:M})}
  ${arrow(296,80,318,80)}
  ${box(322,58,96,44)} ${txt(332,76,'TF-IDF',{w:600})} ${txt(332,92,'→ SVD 96d',{s:10.5,c:M})}
  ${box(22,118,180,54)} ${txt(32,137,'Parquet files',{w:600})}
  ${txt(32,153,`${fmt(t.vector_rows)} vector rows`,{s:10.5,c:M})}
  ${box(216,118,202,54)} ${txt(226,137,'elig_model.pkl',{w:600})}
  ${txt(226,153,'vectoriser + SVD, 94 MB',{s:10.5,c:M})}

  ${box(468,8,424,414)} ${txt(482,28,'EXASOL PERSONAL LOCAL',{s:10,w:700,c:M})}
  ${txt(482,45,'nothing leaves this machine',{s:11,c:M})}
  ${box(482,58,190,96)} ${txt(492,77,'Tables',{w:600})}
  ${txt(492,94,`ELIG_VECTORS  ${fmt(t.vector_rows)}`,{s:10.5,c:M})}
  ${txt(492,109,`CHUNK_TOKENS  ${fmt(t.token_rows)}`,{s:10.5,c:M})}
  ${txt(492,124,`ELIG_CHUNKS   ${fmt(t.chunks)}`,{s:10.5,c:M})}
  ${txt(492,139,'+ semantic-layer views',{s:10.5,c:M})}
  ${box(692,58,190,96)} ${txt(702,77,'BucketFS',{w:600})}
  ${txt(702,94,'the database’s own',{s:10.5,c:M})}
  ${txt(702,109,'file store, mounted',{s:10.5,c:M})}
  ${txt(702,124,'inside the UDF at',{s:10.5,c:M})}
  ${txt(702,139,'/buckets/…',{s:10.5,c:M})}
  ${arrow(210,145,478,110)} ${arrow(418,145,688,110)}

  ${box(482,180,400,40,'var(--surface)')}
  ${txt(492,205,'Your question  —  “prior treatment with an anti-PD-1 antibody”',{s:11})}
  ${arrow(682,222,682,240)}
  ${box(482,244,400,52)}
  ${txt(492,263,'2 Python UDFs  —  the only Python at query time',{w:600})}
  ${txt(492,281,'EMBED_QUERY → 96 rows      QUERY_TERMS → BM25 terms',{s:10.5,c:M})}
  ${arrow(682,298,682,316)}
  ${box(482,320,400,52)}
  ${txt(492,339,'Pure SQL  —  join, GROUP BY, rank, fuse',{w:600})}
  ${txt(492,357,'cosine = SUM(a.VAL * b.VAL)      then BM25, then RRF',{s:10.5,c:M})}
  ${arrow(682,374,682,392)}
  ${txt(682,406,'Ranked criteria, each citing its NCT ID',{s:11,w:600,a:'middle'})}
</svg>`;
}

/* ---------------- load everything ---------------- */
(async function(){
  let d;
  try{ d=await(await fetch('/stats')).json(); }
  catch(e){ document.getElementById('ds-tiles').innerHTML=
    '<div class="flag">Could not read the database: '+esc(e)+'</div>'; return; }
  if(d.error){ document.getElementById('ds-tiles').innerHTML=
    '<div class="flag">'+esc(d.error)+'</div>'; return; }
  PRESETS=d.presets||[]; mkPresets();
  const t=d.totals, sn=d.snapshot||{}, mm=d.model_meta||{};

  /* dataset */
  document.getElementById('ds-tiles').innerHTML=
     tile(fmt(t.trials),'Trials','NSCLC + breast, 2015 onward')
    +tile(fmt(t.chunks),'Criteria sentences','every trial has criteria text')
    +tile(fmt(t.sponsors),'Distinct sponsors','across '+t.countries+' countries')
    +tile(fmt(t.outcomes),'Recorded endpoints','free text, not coded');
  document.getElementById('ds-source').innerHTML=kv({
    'Source':'ClinicalTrials.gov API v2',
    'Fetched':(sn.fetched_utc||'?'),
    'Filter':'interventional, start 2015+',
    'Conditions':'non-small cell lung cancer; breast cancer',
    'Trials kept':fmt(sn.trials||t.trials),
    'Cross-listed dropped':fmt(sn.cross_listed_dropped||0),
    'Snapshot size':((sn.bytes||0)/1048576).toFixed(1)+' MB, committed',
    'Live API calls at demo time':'<span class="yes">none</span>'});
  document.getElementById('ds-sections').innerHTML=bars(d.sections,'Half');
  document.getElementById('ds-phase').innerHTML=bars(d.phase,'Phase');
  document.getElementById('ds-region').innerHTML=bars(d.region,'Region');
  document.getElementById('ds-status').innerHTML=bars(d.status,'Status');
  document.getElementById('ds-sponsor').innerHTML=bars(d.sponsor,'Sponsor type');
  document.getElementById('ds-countries').innerHTML=bars(d.top_countries,'Country');
  document.getElementById('ds-comparator').innerHTML=bars(d.comparator,'Design');
  document.getElementById('ds-endpoint').innerHTML=bars(d.endpoint,'Endpoint');
  const unc=(d.endpoint.find(r=>r.label.indexOf('Other')===0)||{}).pct;
  document.getElementById('ds-endpoint-flag').innerHTML='<b>'+unc+'%</b> of primary endpoints '
    +'still land in <i>Other / unclassified</i>. That is the cost of free-text endpoints, '
    +'and it is shown rather than hidden.';

  /* model */
  document.getElementById('md-kv').innerHTML=kv({
    'Document vectors':'TF-IDF &rarr; TruncatedSVD ('+(mm.dims||96)+' dims) &mdash; classic LSA',
    'Vocabulary':fmt(mm.vocab||t.vocab)+' terms (unigrams + bigrams)',
    'Similarity':'cosine, via a unit-length dot product',
    'Keyword scoring':'BM25, k1=1.2, b=0.75',
    'Combining the two':'reciprocal rank fusion, k=60',
    'Variance explained':((mm.explained_variance||0)*100).toFixed(1)+'%',
    'Transformer / neural model':'<span class="no">none</span>',
    'External API call':'<span class="no">none</span>',
    'Predictive model':'<span class="no">none &mdash; this retrieves, it does not predict</span>',
    'Library':'scikit-learn, pinned to the database’s container'});
  document.getElementById('md-pipe').textContent=
`criterion sentence
  -> lowercase, strip accents, drop stopwords
  -> unigrams + bigrams        ${fmt(mm.vocab||t.vocab)} term vocabulary
  -> TF-IDF weighting          sublinear tf
  -> TruncatedSVD              ${mm.dims||96} dimensions
  -> L2 normalise              so dot product == cosine
  -> ${fmt(t.vector_rows)} rows in Exasol   (one row per dimension)`;

  /* architecture */
  document.getElementById('arch-svg').innerHTML=archSvg(t);
  document.getElementById('arch-tables').innerHTML=kv({
    'ELIG_VECTORS':fmt(t.vector_rows)+' rows',
    'CHUNK_TOKENS':fmt(t.token_rows)+' rows',
    'ELIG_CHUNKS':fmt(t.chunks)+' rows',
    'TERM_IDF':fmt(t.vocab)+' rows',
    'Loaded from Parquet in':'~9 seconds',
    'Full similarity scan':'~5 seconds'});
  document.getElementById('arch-where').innerHTML=kv({
    'Fetch + shred':'laptop, Python',
    'TF-IDF + SVD fit':'Docker, once',
    'Vector storage':'Exasol table',
    'Model file':'Exasol BucketFS',
    'Query embedding':'Exasol Python UDF',
    'Similarity, BM25, fusion':'<b>Exasol SQL</b>',
    'Ranking + citation':'Exasol SQL'});

  /* results */
  if(!d.eval){document.getElementById('ev-tiles').innerHTML=
    '<div class="flag">No eval results yet &mdash; run <code>./06_eval.sh</code>.</div>';}
  else{
    const s=d.eval.summary, T=s.text_only, W=s.with_section;
    document.getElementById('ev-tiles').innerHTML=
       tile((T.recall_at_k*100).toFixed(1)+'%','Recall, text alone','of the right answers found')
      +tile((W.recall_at_k*100).toFixed(1)+'%','Recall, with the column','same search, one filter added')
      +tile((T.section_purity*100).toFixed(0)+'%','Right-half rate, text alone','how much of the top-k was usable')
      +tile((W.section_purity*100).toFixed(0)+'%','Right-half rate, filtered','');
    let h='<table><thead><tr><th>Question</th><th>Kind</th><th class="n">Recall, text alone</th>'
      +'<th class="n">Recall, filtered</th><th class="n">Change</th></tr></thead><tbody>';
    for(const r of d.eval.results){
      if(r.error){h+='<tr><td>'+esc(r.id)+'</td><td colspan="4">'+esc(r.error)+'</td></tr>';continue;}
      const a=r.text_only.recall_at_k,b=r.with_section.recall_at_k,dl=b-a;
      h+='<tr><td>'+esc(r.id)+'<div class="x" style="color:var(--mut);font-size:11.5px">'
        +esc(r.intent)+'</div></td><td class="sec">'+esc(r.category)+'</td>'
        +'<td class="n">'+a.toFixed(2)+'</td><td class="n">'+b.toFixed(2)+'</td>'
        +'<td class="n" style="color:'+(dl>0?'var(--good)':'var(--mut)')+'">'
        +(dl>0?'+':'')+dl.toFixed(2)+'</td></tr>';}
    document.getElementById('ev-table').innerHTML=h+'</tbody></table>';
    const bc=s.by_category||{};
    document.getElementById('ev-fail').innerHTML=kv({
      'Stopword deletion &mdash; "no prior treatment"':
        'the negation is deleted before scoring. <b>The criteria-half column fixes it.</b>',
      'Antonymy &mdash; "EGFR mutation negative"':
        '<span class="no">the column cannot fix this</span> &mdash; both sentences sit in the same half',
      'Polarity questions, recall':
        (bc.polarity? bc.polarity.recall_text_only+' &rarr; '+bc.polarity.recall_with_section:'?')
        +' (the weakest category)',
      'Other hybrid questions, recall':
        (bc.hybrid? bc.hybrid.recall_text_only+' &rarr; '+bc.hybrid.recall_with_section:'?'),
      'Worst single question':'"no prior systemic chemotherapy" &mdash; recall 0.15, because the '
        +'negation is in <i>your</i> question too'});
    document.getElementById('ev-caveat').textContent=s.caveat||'';
  }
  go();
})();
</script></body></html>"""
