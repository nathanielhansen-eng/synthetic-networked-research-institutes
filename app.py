#!/usr/bin/env python3
"""
app.py — Synthetic Networked Research Institutes, interactive (three-panel).

Left: the controls. Middle: a live network diagram whose visual properties track
the sliders (topology shape; node size = researchers; node colour = agreeableness;
edge thickness = briefing exchanges; inner rings = internal rounds). Right: the
institutes' live activity.

Bring your own Anthropic API key. Runs cost money (live LLM + web search).

    .venv/bin/streamlit run app.py
"""

from __future__ import annotations

import base64
import glob
import html as _html
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import netviz  # noqa: E402  (network diagram; pulls in the verified Zollman topologies)
import institute  # noqa: E402  (pricing table + pre-run cost estimator)
import personas_gen  # noqa: E402  (archetype catalog for the composition picker)

RUNDIR = HERE / "_app_runs"
RUNDIR.mkdir(exist_ok=True)
ACTIVE = RUNDIR / "active_run.json"  # the run in progress, if any — lets a rerun re-attach


def _child_alive(pid):
    """Liveness of the run child. waitpid reaps it the moment it exits, so a
    finished run never lingers as a zombie that still looks alive."""
    try:
        return os.waitpid(pid, os.WNOHANG) == (0, 0)
    except ChildProcessError:  # not (or no longer) our child, e.g. server restarted
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _read_ceiling(control_path, fallback):
    try:
        v = json.loads(pathlib.Path(control_path).read_text(encoding="utf-8")).get("max_cost")
        return float(v) if v else fallback
    except (OSError, ValueError):
        return fallback


def _update_control(control_path, **kv):
    """Merge keys into the run's control file (never clobber the other keys —
    a pending stop must survive a ceiling raise and vice versa)."""
    p = pathlib.Path(control_path)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    d.update(kv)
    p.write_text(json.dumps(d), encoding="utf-8")

PRESETS = {
    "Gödel case (cross-disciplinary, open)": {
        "problem": (
            "Why does the cross-cultural effect in the experimental philosophy of "
            "reference attach specifically to the Gödel case (Machery et al. 2004) "
            "and not to other probes? Reconstruct the landscape by cross-disciplinary "
            "search (linguistics, psycholinguistics, cultural psychology, translation) "
            "and adjudicate among candidate mechanisms."),
        "ground_truth": "",
    },
    "Ground-truth demo: protein-coding fraction of the genome": {
        "problem": (
            "What fraction of the human genome codes for proteins? Give a single "
            "best estimate with a short justification."),
        "ground_truth": (
            "Roughly 1–2% of the human genome consists of protein-coding sequence "
            "(about 1.5%). An answer near 1–2% is correct; ~1.5% is ideal; answers "
            "much above ~2% or that confuse coding with total functional/transcribed "
            "DNA are wrong."),
    },
    "Custom…": {"problem": "", "ground_truth": ""},
}

TOPOLOGIES = ["cycle", "wheel", "complete", "line"]
MODELS = ["claude-haiku-4-5", "claude-sonnet-5", "claude-opus-4-8"]


# --------------------------------------------------------------------------- #
# live + results rendering
# --------------------------------------------------------------------------- #
def _fmt_eta(sec):
    if sec is None:
        return "estimating…"
    sec = int(max(0, sec))
    m, s = divmod(sec, 60)
    return f"~{m}m{s:02d}s left" if m else f"~{s}s left"


def _fading_dots(tick):
    ops = [(1.0, 0.3, 0.3), (0.3, 1.0, 0.3), (0.3, 0.3, 1.0)][tick % 3]
    return "".join(f"<span style='opacity:{o}'>●</span>" for o in ops)


def render_live(events_path, feed, status, net_ph, diag, expected_turns, tick):
    rows = []
    if os.path.exists(events_path):
        for line in open(events_path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    te = [r for r in rows if r["type"] == "turn_end"]
    cost = sum(r.get("cost", 0) for r in te)
    jp = [r for r in rows if r["type"] == "judge_progress"]
    if jp:
        cost = max(cost, jp[-1].get("cost", cost))
    done = any(r["type"] == "run_end" for r in rows)
    last_type = rows[-1]["type"] if rows else None
    judging = (not done) and (last_type in ("judge_start", "judge_progress"))

    # turns
    turns, cur = [], None
    for r in rows:
        if r["type"] == "turn_start":
            im = re.search(r"(\d+)", str(r.get("institute", "")))
            cur = {"h": f"{r.get('institute','')} · r{r.get('round','')} · {r.get('persona','')}",
                   "t": "", "i": int(im.group(1)) if im else None}
            turns.append(cur)
        elif r["type"] == "text" and cur is not None:
            cur["t"] += r.get("t", "")
        elif r["type"] == "tool" and cur is not None:
            cur["t"] += f" «▸{r.get('name')}» "

    # active node (for the diagram): last working institute, unless judging/done
    active = None
    if not done and not judging:
        cst = next((r for r in reversed(rows) if r["type"] == "turn_start"), None)
        if cst:
            mm = re.search(r"inst(\d+)", str(cst.get("institute", "")))
            if mm and int(mm.group(1)) < diag[1]:
                active = int(mm.group(1))

    # ETA from average time per completed turn
    eta = None
    ts = [r.get("ts") for r in rows if r.get("ts")]
    if te and len(ts) >= 2 and not done:
        per = (ts[-1] - ts[0]) / max(1, len(te))
        eta = per * max(0, expected_turns - len(te))

    dots = _fading_dots(tick)
    hit_ceiling = any(r["type"] == "cost_abort" for r in rows)
    user_stopped = any(r["type"] == "user_stop" for r in rows)
    if done:
        if user_stopped:
            headline = "⚠️ Run killed by user — partial report below."
        elif hit_ceiling:
            headline = "⚠️ Run aborted at the cost ceiling — partial report below."
        else:
            headline = "Run complete — see the report below."
        head = f"**{headline}** · {len(te)} turns · **${cost:.4f}**"
    elif judging:
        p = jp[-1] if jp else {}
        head = (f"finalizing {dots} · judging briefings {p.get('done','…')}/{p.get('total','…')} "
                f"(scoring diversity & correctness — no live text here) · **${cost:.4f}**")
    else:
        c = next((r for r in reversed(rows) if r["type"] == "turn_start"), {})
        who = f"{c.get('institute','')} · {c.get('persona','')}"
        head = (f"running {dots} · {who} · turn {len(te)}/{expected_turns} · "
                f"{_fmt_eta(eta)} · **${cost:.4f}**")
    status.markdown(head, unsafe_allow_html=True)

    # feed — anchored to the BOTTOM (flex column-reverse), newest at bottom, chronological top→down
    box = ("<div style='height:430px;overflow-y:auto;display:flex;flex-direction:column-reverse;"
           f"background:{netviz.PANEL_BG};color:#cfe8d4;font-family:ui-monospace,Menlo,monospace;"
           "font-size:12.5px;line-height:1.45;padding:12px 14px;border-radius:8px;border:1px solid #2a3540;'>")
    # header colour = the institute's accent (same as its node outline/number)
    inner = "".join(
        f"<div style='margin-bottom:14px;white-space:pre-wrap;'><b style='color:"
        f"{netviz.INST_COLORS[t['i'] % len(netviz.INST_COLORS)] if t.get('i') is not None else '#fff'}'>"
        f"{_html.escape(t['h'])}</b>\n{_html.escape(t['t'])}</div>"
        for t in reversed(turns[-40:]))
    feed.markdown(box + inner + "</div>", unsafe_allow_html=True)

    # diagram with the active node lit + its report-arrows
    fig = netviz.network_figure(*diag, active=active)
    net_ph.pyplot(fig)
    plt.close(fig)


_PERSIST_TRAITS = ["O", "C", "E", "A", "N", "WARMTH"]


def _render_persistence(p):
    """Drift chart + table for a persistence block (None if not tracked)."""
    if not p:
        return
    st.markdown("#### Persona persistence — measured trait drift")
    st.caption("Big-Five self-report before deliberation vs. after (conditioned on "
               "each institute's own transcript). Bars = mean drift per role, "
               "averaged over institutes; positive = the trait moved up. Watch **A** "
               "— does a low-agreeableness cell stay low-A after being pushed, or "
               "relax toward the agreeable-assistant centroid (drift up)? Stated "
               f"traits, not behaviour · persistence cost ${p.get('cost_usd', 0):.4f}.")
    agg = p.get("aggregate_drift") or {}
    if agg:
        # index = trait, one column per role → grouped bars
        drift_df = pd.DataFrame(
            {task: {t: (agg[task].get(t) or {}).get("mean", 0.0) for t in _PERSIST_TRAITS}
             for task in agg}
        ).reindex(_PERSIST_TRAITS)
        st.bar_chart(drift_df)
    recs = p.get("records") or []
    if recs:
        rows = []
        for r in recs:
            row = {"inst": r["institute"], "persona": r["name"], "role": r["task"]}
            for t in _PERSIST_TRAITS:
                row[f"Δ{t}"] = r["drift"].get(t)
            rows.append(row)
        st.dataframe(pd.DataFrame(rows))


def _abort_warning(d):
    """One loud line whenever a saved run was cut short (cost ceiling or user stop)."""
    ab = d.get("aborted")
    if not ab:
        return
    if ab.get("reason") == "user_stop":
        st.warning(f"⚠️ Run KILLED BY USER at ${ab['cost']:.2f}, after "
                   f"inst{ab['after_institute']} in network round "
                   f"{ab['after_net_round']} — the remaining institutes never "
                   "answered. Everything below reports only the work that existed "
                   "when the run was killed. Partial-round diversity is suppressed.")
    else:
        st.warning(f"⚠️ Run aborted at the cost ceiling (${ab['cost']:.2f} ≥ "
                   f"${ab['ceiling']:.2f}) after inst{ab['after_institute']} in "
                   f"network round {ab['after_net_round']} — the remaining "
                   "institutes never answered. Partial-round diversity is suppressed.")


def render_results(out_path):
    d = json.loads(pathlib.Path(out_path).read_text(encoding="utf-8"))
    metrics = d["metrics"]
    gt = bool((d["config"].get("ground_truth") or "").strip())
    st.subheader("Result")
    _abort_warning(d)
    st.caption(f"{d['config']['model']} · {d['config']['topology']} · "
               f"{d['config']['n_institutes']} institutes · agreeableness "
               f"{d['config'].get('agreeableness','–')} · cost ${d['cost_usd']:.4f}")
    DIV_HELP = ("Mechanism diversity: how spread out the institutes' answer-types are. "
                "0 bits = they all gave the same kind of answer (consensus); higher = more "
                "distinct mechanisms. Max = log2(number of institutes).")
    cols = st.columns(max(1, len(metrics)))
    for c, m in zip(cols, metrics):
        ent = m.get("entropy_bits")
        c.metric(f"R{m['round']} diversity",
                 f"{ent} bits" if ent is not None
                 else f"– ({m.get('n','?')}/{d['config']['n_institutes']} answered)",
                 help=DIV_HELP)
        if gt and "mean_correctness" in m:
            c.metric(f"R{m['round']} correctness", f"{m['mean_correctness']:.2f}",
                     help="mean 0–1 correctness vs the ground-truth target")
    chart = {"diversity (bits)": [m.get("entropy_bits") for m in metrics]}
    if gt:
        chart["mean correctness"] = [m.get("mean_correctness", 0) for m in metrics]
    st.line_chart(chart)

    _render_persistence(d.get("persistence"))

    # per-institute answers, one line each
    st.markdown("#### Institute answers (one line each)")
    rowlist = []
    for h in d["history"]:
        row = {"inst": h["institute"], "round": h["net_round"] + 1,
               "mechanism": h.get("category", "?"), "conf": h.get("confidence")}
        if gt:
            row["correct"] = h.get("correctness")
        row["answer"] = (h.get("one_line") or "")[:160]
        rowlist.append(row)
    st.dataframe(pd.DataFrame(rowlist))


def render_run_report(out_path):
    """The top-level run report — header, metrics table, and one-line institute
    answers — shown above the full briefings. Renders the saved report_*.md when
    present (so it matches the on-disk report byte-for-byte, including ground-truth
    and persistence sections), otherwise rebuilds a compact version from the JSON."""
    p = pathlib.Path(out_path)
    rp = p.parent / f"report_{p.stem.replace('out_', '')}.md"
    if rp.exists():
        txt = rp.read_text(encoding="utf-8")
        txt = re.sub(r"(?m)^Full briefings:.*\n?", "", txt)  # drop the on-disk path pointer
        st.markdown(txt)
        return
    d = json.loads(p.read_text(encoding="utf-8"))
    cfg = d["config"]
    gt = bool((cfg.get("ground_truth") or "").strip())
    st.markdown(f"### Run report — {cfg['topology']}, agreeableness {cfg.get('agreeableness', '–')}")
    st.caption(f"{cfg['model']} · {cfg['n_institutes']} institutes · size {cfg.get('cell_size', '–')} · "
               f"{cfg['net_rounds']} network rounds · team={cfg.get('team')} · cost ${d['cost_usd']:.4f}")
    st.markdown(f"**Problem.** {cfg['problem']}")
    st.markdown("**Institute answers (one line each)**")
    for h in sorted(d["history"], key=lambda x: (x["net_round"], x["institute"])):
        line = (f"- **inst{h['institute']} · r{h['net_round'] + 1}** "
                f"[{h.get('category', '?')}] conf {h.get('confidence', '–')}")
        if gt and h.get("correctness") is not None:
            line += f" · correctness {h['correctness']:.2f}"
        st.markdown(line + f" — {h.get('one_line', '')}")


_VERDICT_ICON = {"lands": "🗡️", "contestable": "⚖️", "fails": "✖️"}


def render_briefings(out_path):
    d = json.loads(pathlib.Path(out_path).read_text(encoding="utf-8"))
    gt = bool((d["config"].get("ground_truth") or "").strip())
    _abort_warning(d)
    with st.expander("📋 Run report", expanded=True):
        render_run_report(out_path)
    st.markdown("#### Full briefings")
    for h in d["history"]:
        tag = f"inst{h['institute']} · r{h['net_round']+1} · **{h.get('category','?')}**"
        if gt and h.get("correctness") is not None:
            tag += f" · correctness {h['correctness']:.2f}"
        adj = h.get("adjudication")
        if adj:
            _v = [a["verdict"] for a in adj]
            tag += ("  ·  claimed kills: "
                    + " ".join(f"{_VERDICT_ICON[v]}{_v.count(v)}" for v in
                               ("lands", "contestable", "fails") if v in _v))
        with st.expander(tag):
            if h.get("one_line"):
                st.markdown("<div style='color:#f5b301;font-style:italic;"
                            "font-size:15.5px;margin:2px 0 8px;'>"
                            f"{_html.escape(h['one_line'])}</div>",
                            unsafe_allow_html=True)
            if gt and h.get("correctness_rationale"):
                st.caption("grader: " + h["correctness_rationale"])
            if adj:
                st.markdown("**Adjudication of claimed kills** — 🗡️ lands · ⚖️ contestable "
                            "· ✖️ fails *(an LLM judge's opinion: flags for your audit, "
                            "not verdicts)*")
                for a in adj:
                    st.markdown(f"- {_VERDICT_ICON[a['verdict']]} **{a['verdict'].upper()}** "
                                f"— {a['claim']}  \n  *{a['rationale']}*")
            st.markdown(h.get("briefing", ""))
    n_flags = sum(len(h.get("unsupported_claims") or []) for h in d["history"])
    st.warning(f"⚠️ {n_flags} unsupported empirical claims flagged — verify before "
               "trusting (these cells are idea-rich, citation-poor).")


def load_runs():
    """Summarize every saved run in _app_runs/ for the picker + comparison table."""
    runs = []
    for f in sorted(glob.glob(str(RUNDIR / "out_*.json"))):
        try:
            d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        cfg, m = d.get("config", {}), d.get("metrics", [])
        if not m:
            continue
        # aborted runs: compare on COMPLETE rounds only — a truncated round's
        # entropy is over fewer institutes and not comparable across runs
        comp = [x for x in m if x.get("entropy_bits") is not None] or m
        first, last = comp[0], comp[-1]
        runs.append({
            "stamp": pathlib.Path(f).stem.replace("out_", ""),
            "A": cfg.get("agreeableness"), "topology": cfg.get("topology"),
            "nodes": cfg.get("n_institutes"), "size": cfg.get("cell_size"),
            "net_rounds": cfg.get("net_rounds"), "team": cfg.get("team"),
            "aborted": bool(d.get("aborted")),
            "div_final": last.get("entropy_bits"),
            "div_delta": round((last.get("entropy_bits", 0) or 0) - (first.get("entropy_bits", 0) or 0), 3),
            "corr_final": last.get("mean_correctness"),
            "conf_final": last.get("mean_confidence"),
            "cost": d.get("cost_usd", 0), "path": f})
    return runs


# --------------------------------------------------------------------------- #
# page
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Synthetic Networked Research Institutes", layout="wide")
st.markdown(  # best-effort: hide Streamlit's built-in "running man" status widget
    "<style>[data-testid='stStatusWidget']{visibility:hidden;}"
    ".stStatusWidget{visibility:hidden;}</style>", unsafe_allow_html=True)
_cache = getattr(st, "cache_data", None) or st.cache  # st.cache gone in modern Streamlit
_rerun = getattr(st, "rerun", None) or st.experimental_rerun  # experimental_rerun gone in modern Streamlit


@_cache
def _logo_b64():
    fig = netviz.logo_figure()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


st.markdown(
    "<div style='display:flex;align-items:center;gap:18px;margin:0 0 0.6rem 0;'>"
    f"<img src='data:image/png;base64,{_logo_b64()}' style='height:67px;' "
    "alt='dense, sparse, and cycle research networks'/>"
    "<h1 style='margin:0;padding:0;'>Synthetic Networked Research Institutes</h1></div>",
    unsafe_allow_html=True)

# A run in progress (started by this session or any other — survives widget
# reruns AND browser refreshes): re-attach to it instead of orphaning it.
run = None
if ACTIVE.exists():
    try:
        run = json.loads(ACTIVE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        run = None
    if run and not _child_alive(run["pid"]):
        # it finished while nobody was watching — collect the result
        if pathlib.Path(run["cfg"]["out"]).exists():
            st.session_state["last_out"] = run["cfg"]["out"]
        else:
            st.warning(f"The last run ended without writing results — see `{run['logf']}`.")
        ACTIVE.unlink(missing_ok=True)  # missing_ok: another tab may have got here first
        run = None

with st.sidebar:
    st.header("Configuration")
    key = st.text_input("Anthropic API key", type="password",
                        help="Used only to launch the run; not stored. Leave blank to reuse the shell's key.")
    model = st.selectbox("Model", MODELS, index=0)

    st.subheader("Team")
    cell_size = st.slider("Institute size (number of researchers)", 2, 5, 3,
                          help="Researchers per institute. Active for “Single type” and "
                               "“Adjust team agreeableness”; the balanced trio is fixed at 3.")

    st.subheader("Team composition")
    comp = st.radio(
        "",
        ["Balanced trio (Disruptor · Architect · Shield)", "Single type",
         "Adjust team agreeableness"], index=0)
    _arch = personas_gen.archetype_catalog()
    _EMOJI = {"disruptor": "🔴", "architect": "🔵", "shield": "🟢"}
    fixed = comp.startswith("Balanced")
    single = comp == "Single type"
    counts, agreeableness = {}, 50

    def _stat_line(d):
        v = d["vector"]
        return (f"<span style='color:#9aa0a6;font-size:12px;'>O{v['O']} · C{v['C']} · E{v['E']} · "
                f"<b>A{v['A']}</b> · N{v['N']} · warmth {d['warmth']}</span>")

    if fixed:
        counts = {"disruptor": 1, "architect": 1, "shield": 1}
        st.caption("The canonical cell — one of each type, held to be the strongest "
                   "general-purpose team. Size fixed at 3; agreeableness varies across the three.")
        for r in ("disruptor", "architect", "shield"):
            d = _arch[r]
            st.markdown(f"**{_EMOJI[r]} {d['name']}** — *{d['tagline']}*  \n{_stat_line(d)}",
                        unsafe_allow_html=True)
    elif single:
        _lab2role = {_arch[r]["name"]: r for r in ("disruptor", "architect", "shield")}
        _sel = st.selectbox("Type", list(_lab2role),
                            help="Every researcher is this same archetype — a monoculture. "
                                 "Compare against the balanced trio to see how much diversity matters.")
        _role = _lab2role[_sel]
        counts = {_role: cell_size}
        agreeableness = _arch[_role]["vector"]["A"]
        d = _arch[_role]
        st.caption(f"An institute of **{cell_size} × {d['name']}** — a monoculture "
                   f"(all A{agreeableness}). How well does a team of only this type do?")
        st.markdown(f"*{d['tagline']}*  \n{_stat_line(d)}", unsafe_allow_html=True)
    else:  # Adjust team agreeableness
        agreeableness = st.slider("Team agreeableness", 0, 100, 30,
                                  help="Low = independent, anti-herd. High = consensus-seeking.")
        st.caption("Builds the Disruptor/Architect/Shield trio (size set above) but **flattens "
                   "agreeableness to one shared level** across all three — even the Disruptor "
                   "takes the A you set. Isolates agreeableness as a single clean variable; the "
                   "other traits stay fixed.")

    eff_size = 3 if fixed else cell_size

    st.subheader("Network")
    topology = st.selectbox("Zollman topology", TOPOLOGIES, index=0,
                            help="cycle/line = sparse; complete = dense; wheel = hub.")
    n_institutes = st.slider("Number of institutes (nodes)", 1, 8, 4)
    net_rounds = st.slider("Network rounds (briefing exchanges)", 1, 4, 2)
    inst_rounds = st.slider("Internal rounds per institute", 1, 3, 1)

    st.subheader("Problem")
    preset = st.selectbox("Preset", list(PRESETS))
    problem = st.text_area("Research question", value=PRESETS[preset]["problem"], height=130)
    use_gt = st.checkbox("Ground-truth mode", value=bool(PRESETS[preset]["ground_truth"]),
                         help="Score each institute's position for correctness vs a target.")
    ground_truth = st.text_area("Ground-truth target / rubric",
                                value=PRESETS[preset]["ground_truth"], height=90) if use_gt else ""

    st.subheader("Budget & tools")
    max_web = st.slider("Web searches per turn", 0, 8, 3)
    max_tokens = st.slider("Max tokens per turn", 1500, 6000, 3000, step=500)
    max_cost = st.number_input("Hard cost ceiling ($)", 0.5, 50.0, 5.0, step=0.5)
    track_persistence = st.checkbox(
        "Track persona persistence", value=False,
        help="Administer a short Big-Five self-report to each persona before "
             "deliberation and again after (conditioned on its own transcript), "
             "and report per-trait drift. Does a low-agreeableness cell STAY "
             "low-A after being pushed, or relax toward the assistant centroid? "
             "Adds ~2 cheap calls per persona per institute; no tools.")
    _elo, _ehi = institute.estimate_cost(
        model, n_institutes, net_rounds, inst_rounds, eff_size,
        max_tokens, max_web, bool(use_gt), track_persistence)
    _eturns = n_institutes * net_rounds * (inst_rounds * eff_size + 1)
    st.markdown(
        f"<div style='background:#161a20;border:1px solid #2a3540;border-radius:8px;"
        f"padding:8px 12px;margin:2px 0 8px;font-size:13px;'>💵 <b>Estimated cost "
        f"${_elo:.2f}–${_ehi:.2f}</b> · ~{_eturns} turns<br>"
        f"<span style='color:#9aa0a6;font-size:11.5px;'>Rough — real token use "
        f"varies with the problem. The hard ceiling (${max_cost:.2f}) stops the run "
        f"if it overshoots.</span></div>", unsafe_allow_html=True)
    if run:
        go = False
        st.subheader("Run in progress")
        _cap = _read_ceiling(run["cfg"]["control"], run["cfg"]["max_cost"])
        st.caption(f"Ceiling now **${_cap:.2f}**. If the run looks worth more, raise "
                   "it here — the run picks the new ceiling up at its next "
                   "between-institutes check, no restart. Raise it *before* the "
                   "meter reaches the ceiling; once the abort fires the run is over.")
        _newcap = st.number_input("New ceiling ($)", 0.5, 100.0, float(_cap), step=0.5,
                                  key=f"cap_{run['stamp']}")
        if st.button("Apply ceiling"):
            _update_control(run["cfg"]["control"], max_cost=_newcap)
            st.success(f"Ceiling now ${_newcap:.2f}")
        if st.button("⏹ Stop run"):
            _update_control(run["cfg"]["control"], stop=True)
            st.warning("Stop requested. The run halts at its next "
                       "between-institutes check (the institute currently "
                       "working finishes its turn first), then judges and "
                       "reports everything that exists — marked as KILLED "
                       "BY USER.")
    else:
        go = st.button("▶ Run")

    _runs = load_runs()
    if _runs:
        st.subheader("History")
        _labels = {f"{r['stamp']} · A{r['A']} · {r['topology']} · ${r['cost']:.2f}": r["path"]
                   for r in reversed(_runs)}
        _pick = st.selectbox("Load a past run", ["(latest)"] + list(_labels))
        if _pick != "(latest)":
            st.session_state["last_out"] = _labels[_pick]

left, right = st.columns([0.85, 1.3])

diag = (topology, n_institutes, agreeableness, eff_size, net_rounds, inst_rounds, fixed)
with left:
    st.subheader("Network")
    net_ph = st.empty()
    if not run:  # while re-attached to a run, the monitor draws the RUN's diagram
        _f = netviz.network_figure(*diag, active=None)
        net_ph.pyplot(_f)
        plt.close(_f)
    if fixed:
        st.caption("**Node** = the balanced Disruptor/Architect/Shield trio · **number + "
                   "outline colour** = institute id (matches the feed headers) · "
                   "**size** = researchers (3) · **edge thickness** = briefing exchanges · "
                   "**🟡 gold node + arrows** = the institute currently sharing its "
                   "report with its neighbours.")
    elif single:
        st.caption("**Node fill** = the chosen archetype's agreeableness (🔴 low/anti-herd → "
                   "🔵 high/consensus) · **number + outline colour** = institute id · "
                   "**size** = researchers · **edge thickness** = briefing exchanges · "
                   "**🟡 gold node + arrows** = the institute currently sharing its report. "
                   "Every institute is a monoculture of the same type.")
    else:
        st.caption("**Node fill** = agreeableness (🔴 low/anti-herd → 🔵 high/consensus) · "
                   "**number + outline colour** = institute id (matches the feed headers) · "
                   "**size** = researchers · **edge thickness** = briefing exchanges · "
                   "**inner rings** = internal rounds · **🟡 gold node + arrows** = the "
                   "institute currently sharing its report with its neighbours.")

with right:
    st.subheader("Activity")
    status, feed = st.empty(), st.empty()
    if not go and not run:
        status.info("Configure on the left, then ▶ Run. The institutes' live reasoning streams here.")

if go:
    if not problem.strip():
        st.sidebar.error("Enter a research question.")
        st.stop()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    team = "dialed" if comp.startswith("Adjust") else "archetypes"
    cfg = {"model": model, "team": team,
           "counts": counts,
           "agreeableness": agreeableness, "cell_size": eff_size,
           "topology": topology, "n_institutes": n_institutes, "net_rounds": net_rounds,
           "inst_rounds": inst_rounds, "problem": problem.strip(),
           "ground_truth": ground_truth.strip(), "max_web": max_web, "max_tokens": max_tokens,
           "max_cost": max_cost, "track_persistence": track_persistence,
           "events": str(RUNDIR / f"events_{stamp}.jsonl"),
           "out": str(RUNDIR / f"out_{stamp}.json"),
           "control": str(RUNDIR / f"control_{stamp}.json")}
    cfg_path = RUNDIR / f"config_{stamp}.json"
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    # the live-updatable knobs (just the cost ceiling for now); run_config
    # re-reads this before every between-institutes ceiling check
    pathlib.Path(cfg["control"]).write_text(json.dumps({"max_cost": max_cost}),
                                            encoding="utf-8")

    env = dict(os.environ)
    if key.strip():
        env["ANTHROPIC_API_KEY"] = key.strip()
    # Send the child's stdout/stderr to a log FILE, never a PIPE. The live view
    # tails events.jsonl (via render_live), so it never reads this stream; a PIPE
    # here only deadlocks — run_config's verbose prints fill the 64 KB pipe buffer
    # and the child blocks on write() while we sit in the monitor loop, never
    # draining it. A file never blocks, and doubles as a persistent trace. The
    # with-block closes only the parent's copy of the fd; the child keeps its own.
    logf = RUNDIR / f"stdout_{stamp}.log"
    with open(logf, "w", encoding="utf-8") as _lf:
        proc = subprocess.Popen([sys.executable, str(HERE / "run_config.py"), str(cfg_path)],
                                env=env, stdout=_lf, stderr=subprocess.STDOUT, text=True)
    ACTIVE.write_text(json.dumps({
        "pid": proc.pid, "stamp": stamp, "cfg": cfg, "logf": str(logf),
        "diag": list(diag),
        "expected_turns": n_institutes * net_rounds * (inst_rounds * eff_size + 1),
    }), encoding="utf-8")
    # rerun so the whole page (sidebar included) renders in run-in-progress mode,
    # then the monitor below re-attaches — the same path every later rerun takes
    _rerun()

if run:
    # monitor the active run from its on-disk record — works whether this script
    # execution launched it, is a widget-triggered rerun, or is a fresh session
    _rdiag, _exp = tuple(run["diag"]), run["expected_turns"]
    tick = 0
    while _child_alive(run["pid"]):
        render_live(run["cfg"]["events"], feed, status, net_ph, _rdiag, _exp, tick)
        tick += 1
        time.sleep(1.0)
    render_live(run["cfg"]["events"], feed, status, net_ph, _rdiag, _exp, tick)
    ACTIVE.unlink(missing_ok=True)
    if pathlib.Path(run["cfg"]["out"]).exists():
        st.session_state["last_out"] = run["cfg"]["out"]
        _rerun()  # redraw with the sidebar back in configure mode
    else:
        _log = pathlib.Path(run["logf"])
        _txt = _log.read_text(encoding="utf-8") if _log.exists() else ""
        status.error("Run failed:\n\n```\n" + (_txt[-1500:] or "(no output)") + "\n```")

# ---- post-run area: briefings / metrics / cross-run comparison, in tabs ----
_last = st.session_state.get("last_out")
_have_last = bool(_last and pathlib.Path(_last).exists())
_allruns = load_runs()
if _have_last or _allruns:
    st.markdown("---")
    tab_brief, tab_metrics, tab_cmp = st.tabs(
        ["📜 Briefings", "📈 Metrics", f"📊 Compare runs ({len(_allruns)})"])
    with tab_brief:
        if _have_last:
            render_briefings(_last)
        else:
            st.info("No run loaded — run one, or pick a past run from the sidebar History.")
    with tab_metrics:
        if _have_last:
            render_results(_last)
        else:
            st.info("No run loaded — run one, or pick a past run from the sidebar History.")
    with tab_cmp:
        if not _allruns:
            st.info("No saved runs yet — every completed run lands here for comparison.")
        else:
            df = pd.DataFrame([{
                "run": r["stamp"], "A": r["A"], "topology": r["topology"], "nodes": r["nodes"],
                "size": r["size"], "netR": r["net_rounds"],
                "diversity": r["div_final"], "Δdiv (r1→last)": r["div_delta"],
                "correctness": r["corr_final"], "confidence": r["conf_final"],
                "cost$": round(r["cost"] or 0, 3),
                "aborted": "⚠️" if r["aborted"] else "",
            } for r in reversed(_allruns)])
            st.dataframe(df)
            _plottable = [r for r in _allruns if r["div_final"] is not None]
            if len(_plottable) >= 2:
                cfig = netviz.compare_figure(_plottable)
                st.pyplot(cfig)
                plt.close(cfig)
            st.caption("**diversity** = mechanism spread (0 bits = full consensus; higher = the "
                       "institutes hold different mechanisms). **Δdiv** = change from round 1 to the "
                       "last round (negative = converged, positive = fragmented). Turn the agreeableness "
                       "dial and watch these move.")
