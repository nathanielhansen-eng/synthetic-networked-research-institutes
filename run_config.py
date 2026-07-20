#!/usr/bin/env python3
"""
run_config.py — one configured run, driven by a JSON config file.

This is what the Streamlit app shells out to: it builds the team (from the
agreeableness dial or the fixed archetypes), runs the network on the chosen
topology, then judges each institute's final position for mechanism DIVERSITY
and — if a ground-truth target is given — for CORRECTNESS. Streams to an event
log (director-compatible) and writes a results JSON.

    python run_config.py config.json
"""

from __future__ import annotations

import json
import pathlib
import statistics
import sys

import anthropic

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import institute as inst      # noqa: E402
import network as net         # noqa: E402
import judge                  # noqa: E402
import personas_gen           # noqa: E402
import persistence            # noqa: E402
from topologies import NETWORKS  # noqa: E402  (adjacency for the adjudication pass)


def _report_md(cfg, history, metrics, cost, bdir, abort=None):
    gt = bool((cfg.get("ground_truth") or "").strip())
    L = [f"# Run report — {cfg['topology']}, agreeableness {cfg.get('agreeableness','–')}",
         "",
         f"model {cfg['model']} · {cfg['n_institutes']} institutes · size "
         f"{cfg.get('cell_size','–')} · {cfg['net_rounds']} network rounds · "
         f"team={cfg.get('team')} · cost ${cost:.4f}", ""]
    if abort:
        if abort.get("reason") == "user_stop":
            L += [f"> ⚠️ **Run KILLED BY USER** (at ${abort['cost']:.2f}) after "
                  f"inst{abort['after_institute']} in network round "
                  f"{abort['after_net_round']} — the remaining institutes never "
                  f"answered. Everything below reports only the work that existed "
                  f"when the run was killed. Partial-round diversity is not "
                  f"reported.", ""]
        else:
            L += [f"> ⚠️ **Run ABORTED at the cost ceiling** (${abort['cost']:.2f} ≥ "
                  f"${abort['ceiling']:.2f}) after inst{abort['after_institute']} in "
                  f"network round {abort['after_net_round']} — the remaining institutes "
                  f"never answered. Partial-round diversity is not reported.", ""]
    L += [f"**Problem.** {cfg['problem']}", ""]
    if gt:
        L += [f"**Ground truth.** {cfg['ground_truth']}", ""]
    L += ["## Metrics", "", "| round | diversity (bits) | mean confidence"
          + (" | mean correctness |" if gt else " |"),
          "|---|---|---|" + ("---|" if gt else "")]
    for m in metrics:
        div = (m["entropy_bits"] if m.get("entropy_bits") is not None
               else f"– (partial: {m['n']}/{cfg['n_institutes']})")
        row = f"| {m['round']} | {div} | {m['mean_confidence']} "
        if gt:
            row += f"| {m.get('mean_correctness','–')} "
        L.append(row + "|")
    L += ["", "## Institute answers (one line each)", ""]
    for h in sorted(history, key=lambda x: (x["net_round"], x["institute"])):
        line = (f"- **inst{h['institute']} · r{h['net_round']+1}** "
                f"[{h.get('category','?')}] conf {h.get('confidence','–')}")
        if gt and h.get("correctness") is not None:
            line += f" · correctness {h['correctness']:.2f}"
        line += f" — {h.get('one_line','')}"
        L.append(line)
    if any(h.get("adjudication") for h in history):
        L += ["", "## Adjudication of claimed kills (LLM judge — advisory, audit before trusting)", ""]
        for h in sorted(history, key=lambda x: (x["net_round"], x["institute"])):
            for a in h.get("adjudication") or []:
                L.append(f"- **inst{h['institute']} · r{h['net_round']+1}** "
                         f"[{a['verdict'].upper()}] {a['claim']} — {a['rationale']}")
    L += ["", f"Full briefings: `{bdir.name}/`", ""]
    return "\n".join(L)


def main(cfg_path):
    cfg = json.loads(pathlib.Path(cfg_path).read_text(encoding="utf-8"))
    model = cfg.get("model", "claude-haiku-4-5")
    events = cfg["events"]
    out = cfg["out"]
    gt = (cfg.get("ground_truth") or "").strip()

    # team: an archetype composition (balanced trio or a monoculture, via counts)
    # or the dialed-agreeableness trio.
    team = cfg.get("team", "dialed")
    if team == "archetypes":
        counts = cfg.get("counts") or {"disruptor": 1, "architect": 1, "shield": 1}
        cell = personas_gen.make_archetype_cell(counts)
    else:
        cell = personas_gen.make_cell(cfg.get("agreeableness", 50), cfg.get("cell_size", 3))

    tools = inst.resolve_tools(model, cfg.get("code", "auto"), max_web=cfg.get("max_web", 3))
    client = anthropic.Anthropic(max_retries=6)
    sink = inst.EventSink(events)
    sink.emit("run_start", model=model, kind="app",
              topology=cfg.get("topology", "cycle"),
              institutes=cfg.get("n_institutes", 4),
              net_rounds=cfg.get("net_rounds", 2),
              agreeableness=cfg.get("agreeableness"),
              cell_size=cfg.get("cell_size"),
              ground_truth=bool(gt))

    # ---- optional: persona persistence — baseline (fresh) before deliberation ----
    track = bool(cfg.get("track_persistence"))
    persist_usage = inst.blank_usage()
    baseline = None
    if track:
        sink.set_context(institute=None, round=None, persona="persistence", role=None)
        sink.emit("persistence_start", phase="baseline", total=len(cell))
        baseline = persistence.measure_baseline(
            client, model, cell,
            on_usage=lambda u: inst.add_usage(persist_usage, u))
        sink.emit("persistence_baseline_done",
                  baseline={pid: b["vector"] for pid, b in baseline.items()})

    positions, history, usage, abort = net.run_network(
        client, model, cfg["problem"], cfg.get("topology", "cycle"),
        cfg.get("n_institutes", 4), cfg.get("net_rounds", 2), cfg.get("inst_rounds", 1),
        [cell], cfg.get("max_tokens", 3000),
        attachments=[], tools=tools, sink=sink,
        brief_dir=None, label_prefix="", max_cost=cfg.get("max_cost"),
        control_path=cfg.get("control"),
    )

    # ---- judge pass: diversity (always) + correctness (if ground truth) ----
    # + adjudication of round-2+ attack claims (if enabled; same model as the run)
    adjud = bool(cfg.get("adjudicate"))
    adj_matrix = NETWORKS[cfg.get("topology", "cycle")](cfg.get("n_institutes", 4)) if adjud else None
    sink.set_context(institute=None, round=None, persona="judge", role=None)
    sink.emit("judge_start", total=len(history))
    for _idx, h in enumerate(history):
        data, ju = judge.classify(client, model, cfg["problem"], h["briefing"])
        inst.add_usage(usage, ju)
        h["category"] = data["category"]
        h["one_line"] = data["one_line"]
        h["confidence"] = data.get("confidence_stated", 0.0)
        h["unsupported_claims"] = data.get("unsupported_claims", [])
        if gt:
            cd, cu = judge.score_correctness(client, model, gt, h["briefing"])
            inst.add_usage(usage, cu)
            h["correctness"] = cd["correctness"]
            h["correctness_rationale"] = cd["rationale"]
        if adjud and h["net_round"] > 0:
            targets = [(g["institute"], g["briefing"]) for g in history
                       if g["net_round"] == h["net_round"] - 1
                       and adj_matrix[h["institute"]][g["institute"]]]
            if targets:
                ad, au = judge.adjudicate(client, model, cfg["problem"],
                                          h["briefing"], targets)
                inst.add_usage(usage, au)
                h["adjudication"] = ad.get("claims") or []
        sink.emit("judge_progress", done=_idx + 1, total=len(history),
                  cost=inst.cost_of(usage, model))

    # ---- optional: persona persistence — FINAL (post-pressure) measurement ----
    persistence_block = None
    if track:
        n_inst = len(set(h["institute"] for h in history))
        sink.set_context(institute=None, round=None, persona="persistence", role=None)
        sink.emit("persistence_start", phase="final", total=n_inst * len(cell))
        records = persistence.measure_finals(
            client, model, cell, history, baseline,
            on_usage=lambda u: inst.add_usage(persist_usage, u),
            on_progress=lambda d, t: sink.emit("persistence_progress", done=d, total=t))
        agg = persistence.aggregate_drift(records)
        inst.add_usage(usage, persist_usage)   # fold persistence cost into the meter
        persistence_block = {"baseline": {pid: b for pid, b in baseline.items()},
                             "records": records, "aggregate_drift": agg,
                             "cost_usd": inst.cost_of(persist_usage, model)}
        sink.emit("persistence_end", aggregate_drift=agg,
                  cost=inst.cost_of(persist_usage, model))

    # ---- per-round metrics: diversity entropy + mean correctness ----
    # A round the cost abort truncated (fewer answers than institutes) gets NO
    # entropy: computed over a partial group it isn't comparable to complete
    # rounds, and at n=1 it reads as full convergence, which is meaningless.
    n_inst = cfg.get("n_institutes", 4)
    rounds = sorted(set(h["net_round"] for h in history))
    metrics = []
    for nr in rounds:
        grp = [h for h in history if h["net_round"] == nr]
        partial = len(grp) < n_inst
        m = {"round": nr + 1, "n": len(grp), "partial": partial,
             "entropy_bits": (None if partial else
                              abs(round(judge.entropy([h["category"] for h in grp]), 3))),
             "mean_confidence": round(statistics.mean([h.get("confidence", 0) for h in grp]), 3)}
        if gt:
            cs = [h["correctness"] for h in grp]
            m["mean_correctness"] = round(statistics.mean(cs), 3)
            m["frac_correct"] = round(sum(1 for c in cs if c >= 0.5) / len(cs), 3)
        metrics.append(m)

    cost = inst.cost_of(usage, model)
    sink.emit("run_end", cost=cost, metrics=metrics, **usage)
    sink.close()

    # human-readable report + individual briefing files alongside the JSON
    outp = pathlib.Path(out)
    stamp = outp.stem.replace("out_", "")
    bdir = outp.parent / f"briefings_{stamp}"
    bdir.mkdir(exist_ok=True)
    for h in history:
        (bdir / f"inst{h['institute']}_r{h['net_round']+1}.md").write_text(
            h["briefing"], encoding="utf-8")
    report = _report_md(cfg, history, metrics, cost, bdir, abort=abort)
    if persistence_block:
        report += "\n" + persistence.report_md(
            persistence_block["baseline"], persistence_block["records"],
            persistence_block["aggregate_drift"])
    (outp.parent / f"report_{stamp}.md").write_text(report, encoding="utf-8")

    pathlib.Path(out).write_text(json.dumps({
        "config": cfg, "metrics": metrics, "cost_usd": cost, "usage": usage,
        "aborted": abort,
        "persistence": persistence_block,
        "final_positions": positions,
        "history": [{k: h.get(k) for k in
                     ("net_round", "institute", "category", "one_line", "confidence",
                      "correctness", "correctness_rationale", "unsupported_claims",
                      "adjudication", "briefing")}
                    for h in history],
    }, indent=2), encoding="utf-8")
    print(f"[done] ${cost:.4f}  metrics={metrics}\n[written] {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "config.json")
