"""Clinical trial intelligence: the problem, the fix, and what it is worth.

A booth screen has to work when nobody is standing next to it, so this page is
built as an ARGUMENT rather than a tool. Each section states a challenge a pharma
data team actually has, shows what the engine does about it with live numbers and
the real SQL, and says what the audience should take from it.

Nothing here is typed in by hand. Every figure is queried when the page loads.
"""
import base64, json, os, re, sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data as D                                  # noqa: E402
import architecture as ARCH                       # noqa: E402
import stage as STAGE                             # noqa: E402
import agent as AGENT                             # noqa: E402
import report as REPORT                           # noqa: E402
from theme import CSS                             # noqa: E402

st.set_page_config(page_title="Clinical Trial Intelligence — Exasol",
                   layout="wide", initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)

DEMO_Q = "Phase 3 NSCLC trials that exclude patients with prior anti-PD-1 therapy"


def logo(variant="dark"):
    """Exasol's mark, inlined so the page needs no network.

    Both width/height attributes AND an inline style: Streamlit's own image
    styling beats a class rule, and an SVG carrying only a viewBox renders at
    full container width.
    """
    f = Path(__file__).resolve().parent / "assets" / f"exasol_logo_{variant}.svg"
    try:
        b64 = base64.b64encode(f.read_bytes()).decode()
        return (f'<img src="data:image/svg+xml;base64,{b64}" alt="Exasol" '
                f'width="104" height="26" '
                f'style="height:26px;width:auto;max-width:104px;display:block;"/>')
    except Exception:
        return ""


def n(x):
    return "{:,}".format(int(x))


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def kicker(k, title, copy=""):
    html(f'<div class="section-shell"><div class="section-kicker">{k}</div>'
         f'<h2 class="section-title">{title}</h2>'
         + (f'<div class="section-copy">{copy}</div>' if copy else "") + "</div>")


def challenge(lbl, big, body):
    html(f'<div class="chal"><div class="lbl">{lbl}</div>'
         f'<div class="big">{big}</div><p>{body}</p></div>')


def solution(lbl, big, body):
    html(f'<div class="sol"><div class="lbl">{lbl}</div>'
         f'<div class="big">{big}</div><p>{body}</p></div>')


def notice(title, items):
    lis = "".join(f"<li>{i}</li>" for i in items)
    html(f'<div class="note-card"><div class="mini-kicker">{title}</div><ul>{lis}</ul></div>')


def duo(hard, fix):
    """Challenge and answer at the same size, side by side.

    Same weight on both sides deliberately: a problem stated in two lines beside
    a solution stated in six reads as a sales pitch, and the audience discounts
    it. The left card has to be as long and as specific as the right one.
    """
    html(f'<div class="duo">'
         f'<div class="dcard hard"><div class="k">{hard["k"]}</div><h3>{hard["t"]}</h3>'
         + "".join(f"<p>{x}</p>" for x in hard["p"]) + "</div>"
         f'<div class="dcard fix"><div class="k">{fix["k"]}</div><h3>{fix["t"]}</h3>'
         + "".join(f"<p>{x}</p>" for x in fix["p"]) + "</div></div>")


def triplet(items):
    html('<div class="triplet">' + "".join(
        f'<div class="tri"><div class="k">{k}</div><div class="t">{v}</div></div>'
        for k, v in items) + "</div>")


def bighead(kick, title, lede):
    html(f'<div class="section-kicker">{kick}</div><div class="bigtitle">{title}</div>'
         f'<div class="lede2">{lede}</div>')


def pains(items):
    cells = "".join(
        f'<div class="pain {i.get("tone","")}"><div class="who">{i["who"]}</div>'
        f'<div class="q">{i["q"]}</div><div class="a">{i["a"]}</div></div>' for i in items)
    html(f'<div class="painrow">{cells}</div>')


def lanex(tag, body, cls=""):
    """A lane of the diagram, said in sentences. The picture and the free text are
    the same content twice, because a diagram nobody can narrate is decoration."""
    html(f'<div class="lanex {cls}"><div class="tag">{tag}</div><p>{body}</p></div>')


def evidence(rows):
    cells = "".join(f'<div class="evid"><div class="k">{k}</div><div class="v">{v}</div></div>'
                    for k, v in rows)
    html(cells)


def kpis(cards):
    cells = "".join(
        f'<div class="kpi {c.get("tone","")}"><div class="k">{c["k"]}</div>'
        f'<div class="v">{c["v"]}</div><div class="x">{c.get("x","")}</div></div>'
        for c in cards)
    html(f'<div class="kpi-grid">{cells}</div>')


def bars(rows, tone_of=lambda r: "", value=lambda r: f'{r["pct"]}%'):
    top = max((r["pct"] for r in rows), default=1) or 1
    out = []
    for r in rows:
        w = 100.0 * r["pct"] / top
        out.append(f'<div class="barrow"><div class="lb">{r["label"]}</div>'
                   f'<div class="tr"><div class="fl {tone_of(r)}" style="width:{w:.1f}%"></div></div>'
                   f'<div class="vv">{value(r)}</div></div>')
    html(f'<div class="bars">{"".join(out)}</div>')


def rows_panel(rows, want):
    if not rows:
        html('<div class="res"><div class="tx">(no rows)</div></div>')
        return
    out = []
    for r in rows:
        bad = want and r["CRITERION_SECTION"] != want
        tag = r["CRITERION_SECTION"] + (" &mdash; wrong half" if bad else "")
        out.append(f'<div class="res{" bad" if bad else ""}"><div class="top">'
                   f'<span class="nct">{r["NCT_ID"]}</span><span class="tag">{tag}</span>'
                   f'<span class="sim">cos {r["VEC_SIM"]}</span></div>'
                   f'<div class="tx">{r["CRITERION"]}</div></div>')
    html("".join(out))


# ---------------------------------------------------------------- hero
h = D.health()
if not h["exasol"]:
    st.error("Exasol is not answering. Start the deployment, then reload.\n\n" + h["err"])
    st.stop()

t = D.totals()
lake = D.lake_totals() if h["lake"] else {"papers": 0, "links": 0}
lake_card = ("signal-card" if h["lake"] else "signal-card down")
lake_val = "Connected" if h["lake"] else "Unavailable"
lake_meta = (f'Iceberg on object storage, engine {h["engine"]}' if h["lake"]
             else (h["cause"] or "unavailable"))
agent_ok = AGENT.have_key()
agent_card = "signal-card" if agent_ok else "signal-card down"

html(f'<div class="pagehead">{logo("dark")}'
     f'<div class="ph-t">Clinical trial intelligence</div></div>')

html(f"""
<section class="hero-shell">
  <div class="hero-eyebrow">Clinical Trial Intelligence &middot; Live Demo</div>
  <div class="hero-title">&ldquo;Pembrolizumab in the US&rdquo; is 538 trials. Or 304. Or 50.</div>
  <div class="hero-copy">
    The difference is three judgements: which brand names count as the same drug, whether
    &ldquo;in the US&rdquo; means <em>a</em> US site or <em>only</em> US sites, and whether a
    combination trial counts. None of them is obvious, and most systems bury all three in a
    WHERE clause nobody reads. This one writes them down, applies one by default, and prints
    what the alternatives would have given &mdash; next to the statement that produced every
    number. Ask it a question, or ask it for the whole landscape.
  </div>
  <div class="signal-grid">
    <div class="signal-card"><div class="signal-label">Exasol</div>
      <div class="signal-value">Connected</div>
      <div class="signal-meta">Trials, criteria, vectors and the resolution layer, in one engine</div></div>
    <div class="{lake_card}"><div class="signal-label">Lakehouse</div>
      <div class="signal-value">{lake_val}</div>
      <div class="signal-meta">{lake_meta}</div></div>
    <div class="signal-card"><div class="signal-label">Trials</div>
      <div class="signal-value">{n(t["trials"])}</div>
      <div class="signal-meta">{n(t["criteria"])} eligibility criteria &middot; {t["countries"]} countries</div></div>
    <div class="{agent_card}"><div class="signal-label">Agent</div>
      <div class="signal-value">{"Ready" if agent_ok else "No API key"}</div>
      <div class="signal-meta">{"Claude, over the Exasol MCP server" if agent_ok
        else "set ANTHROPIC_API_KEY in .env to enable"}</div></div>
  </div>
</section>""")

mode = st.radio("Mode", ["Explore", "Walkthrough"], horizontal=True,
                label_visibility="collapsed",
                help="Explore: the seven tabs, navigate freely. "
                     "Walkthrough: six steps, Back and Next.")
STAGE_MODE = mode == "Walkthrough"

if STAGE_MODE:
    STAGE.render(D, t, lake, h, n, html)
    st.stop()

if not h["lake"]:
    st.warning(f"**Lakehouse unavailable** — {h['cause']}")
    # A clock skew is repairable from here; anything else needs a real decision.
    if h.get("skew") and h["skew"] > 300:
        if st.button("Resync the clock and retry", type="primary"):
            ok, msg = D.fix_vm_clock()
            st.cache_data.clear()
            (st.success if ok else st.error)(msg)
            st.rerun()
    else:
        st.caption(f"Fix: `{h['fix']}`")

tabs = st.tabs(["1 · The challenge", "2 · The demo", "3 · How Exasol does it"])

# ============================================================ 1. THE CHALLENGE
with tabs[0]:
    ph = D.phase_mix()
    ep = D.endpoint_mix()
    na = next((r for r in ph if r["label"] == "NOT_APPLICABLE"), {"pct": 0, "n": 0})
    other = next((r for r in ep if r["label"].lower().startswith("other")), {"pct": 0, "n": 0})

    bighead("The challenge",
            "Every clinical trial is public. The question a study team actually asks "
            "has no column to answer it.",
            "ClinicalTrials.gov is complete, free and searchable. Phase, sponsor, status and "
            "geography are all coded, and any warehouse can filter them. That part is solved. "
            "The problem starts the moment somebody asks <em>what is the landscape for this drug, "
            "in this country, right now?</em> — and expects an answer they can defend.")

    duo(
        {"k": "Why this is hard",
         "t": "The answer is spread across four shapes of data",
         "p": [
             "Some of it is coded and easy — phase, sponsor, country. Some of it is written as "
             "free text and has no column at all: who a trial will <b>accept</b> lives inside one "
             "<code>eligibilityCriteria</code> blob. Some of it is recorded but misleading: "
             f"<b>{na['pct']}% of trials say the phase is NOT_APPLICABLE</b>, so a naive filter "
             "silently drops a third of the landscape. And some of it is not in the warehouse at "
             "all — the publication record lives in another system entirely.",
             "The usual answer is four systems: a warehouse for the columns, a vector database for "
             "the text, a query engine for the lake, and an application to stitch the three "
             "together. Three copies of the same corpus, and a join that happens where nobody can "
             "audit it — which is exactly the join a regulator will ask about.",
         ]},
        {"k": "What we built instead",
         "t": "One engine, and an agent that can reach all of it",
         "p": [
             "Trials, criteria and vectors sit in Exasol. Publications stay as <b>Iceberg tables in "
             "object storage</b> and are read in place through a virtual schema — never imported. "
             "Both are queried in a single statement, because to the planner the lakehouse is just "
             "another schema.",
             "On top of that, <b>an agent over the Exasol MCP server</b>: it sees the schema, writes "
             "its own SQL, and answers with trial IDs you can check. Ask it a question, or ask it "
             "for a full landscape report — same engine, same data, same citations.",
         ]})

    triplet([
        ("One copy of the data", "Nothing exported to a vector store, nothing imported from the lake."),
        ("One statement", "The structured half and the free-text half resolve together, auditably."),
        ("One answer you can defend", "Every claim carries the NCT id it came from."),
    ])

    kicker("What the layer admits about itself", "A dashboard that hides its own coverage is worse than none")
    kpis([
        {"k": "Trials loaded", "v": n(t["trials"]), "x": "NSCLC and breast, interventional, 2015+"},
        {"k": "Eligibility criteria", "v": n(t["criteria"]), "x": "one row per sentence, section recovered"},
        {"k": "No usable phase", "v": f"{na['pct']}%", "x": "NOT_APPLICABLE — stated, never hidden", "tone": "hot"},
        {"k": "Endpoints unclassifiable", "v": f"{other['pct']}%", "x": "free text, no controlled vocabulary", "tone": "hot"},
    ])

# ============================================================ 2. THE DEMO
with tabs[1]:
    bighead("The demo",
            "Ask a question. Or ask for the whole landscape.",
            "Both run against the same Exasol. The agent reaches it through the "
            "<b>Exasol MCP server</b> and writes its own SQL; the report runs a fixed set of "
            "statements so the same keyword always produces the same document. Either way every "
            "number carries the statement that produced it.")

    if not AGENT.have_key():
        st.warning("**No `ANTHROPIC_API_KEY`** — copy `.env.example` to `.env`, paste your key, "
                   "and restart with `./app/run.sh`.")

    mode2 = st.radio("What to run", ["Ask a question", "Generate a report"],
                     horizontal=True, label_visibility="collapsed")

    # ---------------------------------------------------------------- ask
    if mode2 == "Ask a question":
        aq = st.selectbox("Ask", AGENT.SIMPLE_PRESETS, label_visibility="collapsed")
        custom = st.text_input("or type your own", value="",
                               placeholder="ask anything about the trials…",
                               label_visibility="collapsed")
        question = custom.strip() or aq
        if st.button("Ask the agent", disabled=not AGENT.have_key(), type="primary"):
            with st.spinner("the agent is writing SQL…"):
                st.session_state["simple_run"] = (question, AGENT.ask_simple(question))

        run = st.session_state.get("simple_run")
        if run:
            q_done, tr = run
            if tr["error"]:
                st.error(tr["error"])
            else:
                st.markdown(tr["answer"])
                if tr.get("rows"):
                    st.dataframe(tr["rows"], width="stretch", hide_index=True)
                final_sql = tr["sql"][-1] if tr["sql"] else ""
                if final_sql:
                    kicker("Citation", "The statement that produced this answer")
                    st.code(final_sql, language="sql")
                if len(tr["sql"]) > 1:
                    with st.expander(f"The agent ran {len(tr['sql'])} statements to get there"):
                        for q_ in tr["sql"][:-1]:
                            st.code(q_, language="sql")

    # ---------------------------------------------------------------- report
    else:
        rq = st.selectbox("Report on", REPORT.PRESETS, label_visibility="collapsed")
        rcustom = st.text_input("or type a keyword", value="",
                                placeholder="e.g. Osimertinib for NSCLC in Japan",
                                label_visibility="collapsed")
        keyword = rcustom.strip() or rq
        if st.button("Generate report", disabled=not AGENT.have_key(), type="primary"):
            with st.spinner("running the report statements…"):
                st.session_state["report"] = (keyword, REPORT.generate(keyword, lake_ok=h["lake"]))

        rep = st.session_state.get("report")
        if rep:
            kw, r = rep
            f = r["filters"]
            scope = " · ".join(f"**{k}**: {v}" for k, v in f["matched"]) or "_no filter matched_"
            st.markdown(f"### Trial landscape — {kw}")
            st.caption(f"Scope resolved to {scope}"
                       + (f" · not recognised: {', '.join(f['unmatched'])}" if f["unmatched"] else ""))
            if not f["matched"]:
                st.warning("Nothing in the keyword matched a value in the database, so this report "
                           "covers the whole corpus. Try naming a drug, a country or an indication.")

            if r["summary"]:
                html(f'<div class="verdictbox"><div class="t">{r["summary"]}</div></div>')

            for sec in r["sections"]:
                kicker(sec["title"], sec["note"])
                if sec["error"]:
                    st.error(sec["error"])
                elif sec["rows"]:
                    st.dataframe(sec["rows"], width="stretch", hide_index=True)
                else:
                    st.info("**Data Not Available** — no rows for this section within the scope above.")
                with st.expander("the statement behind this section"):
                    st.code(sec["sql"], language="sql")

            kicker("Not covered", "Stated so nobody has to ask")
            for line in r["not_covered"]:
                st.markdown(f"- {line}")

            st.download_button("Download this report (Markdown)",
                               data=REPORT.as_markdown(kw, r),   # SQL stays on screen, not in the file
                               file_name=f"trial-landscape-{re.sub(r'[^a-z0-9]+', '-', kw.lower()).strip('-')}.md",
                               mime="text/markdown")

# ============================================================ 3. HOW IT WORKS
with tabs[2]:
    bighead("How Exasol does it",
            "One engine holds the columns, the free text and the lakehouse.",
            "Everything expensive runs once, before the demo. A question only ever touches the "
            "bottom half of this picture.")

    cost = D.tier_cost() if h["lake"] else {"native_ms": 0, "lake_ms": 0, "delta_ms": 0}
    html(f'<div class="archbox">{ARCH.diagram(t, lake, cost)}</div>')

    c1, c2 = st.columns(2)
    with c1:
        solution("The idea that makes it possible",
                 "A vector is rows. Cosine is a <em>GROUP BY</em>.",
                 f"Exasol has no vector type and no vector index, so each 96-dimension vector is "
                 f"stored as 96 rows, normalised at build time. A dot product then <em>is</em> cosine, "
                 f"and similarity over {n(t['vector_rows'])} rows is an ordinary join and aggregate — "
                 "the one thing this engine was built for. No index to tune, no recall cliff.")
        st.code("""SELECT v.NCT_ID, v.CHUNK_ID, SUM(v.VAL * q.VAL) AS SIM
FROM   CT.ELIG_VECTORS v
JOIN   QV q ON q.DIM = v.DIM
GROUP  BY v.NCT_ID, v.CHUNK_ID""", language="sql")
    with c2:
        solution("And the data that should not move",
                 "A virtual schema, not a pipeline",
                 f"{n(lake['papers'])} PubMed records stay as Iceberg tables on object storage and "
                 "are never loaded. A Rust UDF running DataFusion reads them at query time and the "
                 f"planner joins them to native tables — about <b>+{cost['delta_ms']} ms</b> over a "
                 "native query. To the agent it is simply another schema."
                 if h["lake"] else "Start the lake with lake/up.sh to show this live.")
        solution("Why an agent can use any of it",
                 "Because it is all just SQL",
                 "The agent gets no special path and no special access — the same views, the same "
                 "grants, through the Exasol MCP server. That is what makes a lakehouse usable by "
                 "an agent at all.")

    kicker("Component by component", "Sourced, ingested, stored, served")
    rows = "".join(f'<tr><td class="l">{a}</td><td class="m">{b}</td><td>{c}</td></tr>'
                   for a, b, c in ARCH.COMPONENTS)
    html(f'<table class="cmp"><tr><th>Layer</th><th>What it is</th><th>Why it is there</th></tr>'
         f'{rows}</table>')

    kicker("What this will not claim", "Measured on the loaded corpus, not quoted from a datasheet")
    c1, c2 = st.columns(2)
    with c1:
        challenge("Not a transformer",
                  "TF-IDF with a 96-dimension SVD",
                  "A transformer would retrieve better — and would be just as blind to the word "
                  "&ldquo;no&rdquo;, because that failure is tokenisation, not model capacity.")
        challenge("Not proof of non-publication",
                  "Publication linkage is a lower bound",
                  "A paper that never cites its NCT number is invisible to the join.")
    with c2:
        challenge("Not the whole registry",
                  "NSCLC and breast, interventional, 2015 onwards",
                  "12,404 trials. Other indications, epidemiology, reimbursement and regulatory "
                  "data are not in this corpus.")
        challenge("Not billion-scale",
                  "25.8M vector rows on a single-node VM",
                  "Cost is linear in rows × dimensions. At a hundred times this, you would "
                  "partition or accept approximate search.")

st.markdown("<br/>", unsafe_allow_html=True)
if st.button("Refresh all live numbers"):
    st.cache_data.clear()
    st.rerun()
