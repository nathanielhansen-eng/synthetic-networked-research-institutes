#!/usr/bin/env python3
"""
network.py — several institutes talking the Zollman way.

Each institute is one 3-persona cell (institute.py). The institutes are nodes in
a communication topology imported from `topologies.py` (our Python port of
Zollman's epistemic-network model). Each network round, an institute sees only
its NEIGHBORS' latest positions (the "Zollman channel") before deliberating
again — so a sparse topology (cycle) preserves transient diversity while a dense
one (complete) converges fast and often prematurely, exactly the finding
`topologies.py` reproduces for bandit agents, now with LLM institutes as the nodes.

You can also vary the institutes' internal DESIGN (which personas staff them) to
compare, e.g., the canonical 3-archetype cell against an all-Disruptor
monoculture — the "series of institutes with different designs" idea.

Usage
-----
    python network.py --topology cycle --institutes 3 --net-rounds 2 --inst-rounds 1
    python network.py --dry-run
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import sys

import anthropic

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import institute as inst  # noqa: E402

# the network topologies, from our port of Zollman's model
from topologies import NETWORKS  # noqa: E402


def neighbor_context(adj, positions, i):
    """Assemble institute i's view: only its neighbors' latest positions."""
    chunks = []
    for j, tie in enumerate(adj[i]):
        if tie and positions[j]:
            chunks.append(f"### Institute {j}\n{positions[j]}")
    return "\n\n".join(chunks)


def _read_control(control_path, cost_fallback):
    """Re-read the run's control file, so the app can raise max_cost mid-run or
    request a stop. Returns (ceiling, stop_requested)."""
    try:
        d = json.loads(pathlib.Path(control_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return cost_fallback, False
    v = d.get("max_cost")
    return (float(v) if v else cost_fallback), bool(d.get("stop"))


def run_network(client, model, problem, topology, n_institutes, net_rounds,
                inst_rounds, designs, max_tokens, attachments=None, tools=None,
                sink=None, brief_dir=None, label_prefix="", max_cost=None,
                control_path=None):
    adj = NETWORKS[topology](n_institutes)
    positions = [""] * n_institutes
    history = []
    total_usage = inst.blank_usage()
    stop = False
    abort = None  # set when the cost ceiling fires — callers must surface this

    for nr in range(net_rounds):
        if stop:
            break
        print(f"\n{'#'*72}\n# NETWORK ROUND {nr+1}/{net_rounds}  topology={topology}\n{'#'*72}", flush=True)
        if sink:
            sink.set_context(institute=None, round=None, persona=None, role=None)
            sink.emit("net_round", net_round=nr + 1, of=net_rounds, topology=topology)
        new_positions = [""] * n_institutes
        for i in range(n_institutes):
            cell = designs[i % len(designs)]
            ctx = neighbor_context(adj, positions, i) if nr > 0 else ""
            res = inst.run_institute(
                client, model, problem, cell, inst_rounds,
                neighbor_ctx=ctx, label=f"{label_prefix}inst{i}", max_tokens=max_tokens,
                verbose=True, attachments=attachments, tools=tools, sink=sink,
            )
            inst.add_usage(total_usage, res["usage"])
            user_stop = False
            if control_path:
                max_cost, user_stop = _read_control(control_path, max_cost)
            cur = inst.cost_of(total_usage, model)
            if user_stop:
                print(f"[STOP] user stop requested at ${cur:.2f}; halting.", flush=True)
                abort = {"reason": "user_stop", "cost": round(cur, 4),
                         "ceiling": max_cost,
                         "after_institute": i, "after_net_round": nr + 1}
                if sink:
                    sink.emit("user_stop", cost=cur)
                stop = True
            elif max_cost and cur >= max_cost:
                print(f"[ABORT] network cost ${cur:.2f} "
                      f">= ceiling ${max_cost}; stopping.", flush=True)
                abort = {"reason": "cost", "cost": round(cur, 4),
                         "ceiling": max_cost,
                         "after_institute": i, "after_net_round": nr + 1}
                if sink:
                    sink.emit("cost_abort", cost=cur, ceiling=max_cost)
                stop = True
            new_positions[i] = res["position"]  # = the briefing, so neighbors get the full report
            brief_file = ""
            if brief_dir and res["briefing"]:
                brief_file = str(brief_dir / f"{label_prefix}{topology}_net{nr+1}_inst{i}.md")
                pathlib.Path(brief_file).write_text(res["briefing"], encoding="utf-8")
            history.append({"net_round": nr, "institute": i,
                            "briefing": res["briefing"], "briefing_file": brief_file,
                            "position": res["position"], "usage": res["usage"],
                            "transcript": [{"speaker": s, "text": t} for s, t in res["transcript"]]})
            if stop:
                break
        positions = new_positions
    return positions, history, total_usage, abort


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--problem-file", default=str(HERE / "problems.md"))
    ap.add_argument("--problem", default=None)
    ap.add_argument("--topology", default="cycle", choices=list(NETWORKS))
    ap.add_argument("--institutes", type=int, default=3)
    ap.add_argument("--net-rounds", type=int, default=2)
    ap.add_argument("--inst-rounds", type=int, default=1)
    ap.add_argument("--model", default=inst.DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--attach", action="append", default=[])
    ap.add_argument("--code", choices=["auto", "on", "off"], default="auto")
    ap.add_argument("--pdf-mode", choices=["text", "base64"], default="text")
    ap.add_argument("--events", default=str(HERE / "events.jsonl"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.problem:
        problem = args.problem.strip()
    else:
        problem = inst._extract_active_problem(pathlib.Path(args.problem_file).read_text(encoding="utf-8"))

    # default: every institute is the canonical 3-archetype cell. Swap entries
    # here to give some institutes a different internal design.
    canonical = inst.load_cell(HERE / "personas")
    designs = [canonical]
    tools = inst.resolve_tools(args.model, args.code)
    attachments = [inst.load_attachment_block(a, extract_pdf=(args.pdf_mode == "text")) for a in args.attach]

    if args.dry_run:
        adj = NETWORKS[args.topology](args.institutes)
        print(f"topology={args.topology}  n={args.institutes}\nadjacency:\n{adj}")
        print(f"designs: {len(designs)} (canonical 3-archetype cell)")
        print(f"model={args.model}  tools={[t['name'] for t in tools]}  "
              f"attachments={[a.get('title') for a in attachments]}")
        print(f"total institute-runs: {args.institutes * args.net_rounds} "
              f"({args.inst_rounds} internal round(s) each)")
        return

    stamp = f"{_dt.datetime.now():%Y%m%d_%H%M%S}"
    brief_dir = HERE / "briefings" / f"network_{args.topology}_{stamp}"
    brief_dir.mkdir(parents=True, exist_ok=True)

    client = anthropic.Anthropic(max_retries=6)
    sink = inst.EventSink(args.events)
    sink.emit("run_start", model=args.model, kind="network", topology=args.topology,
              institutes=args.institutes, net_rounds=args.net_rounds)
    positions, history, total_usage, abort = run_network(
        client, args.model, problem, args.topology, args.institutes,
        args.net_rounds, args.inst_rounds, designs, args.max_tokens,
        attachments=attachments, tools=tools, sink=sink, brief_dir=brief_dir,
    )
    if abort:
        print(f"\n*** RUN ABORTED at the cost ceiling (${abort['cost']:.2f} >= "
              f"${abort['ceiling']:.2f}) after inst{abort['after_institute']}, "
              f"net round {abort['after_net_round']} — results below are partial. ***")
    total_cost = inst.cost_of(total_usage, args.model)
    sink.emit("run_end", cost=total_cost, **total_usage)
    sink.close()

    print("\n" + "=" * 72 + "\nFINAL BRIEFINGS\n" + "=" * 72)
    for i, p in enumerate(positions):
        print(f"\n--- Institute {i} ---\n{p}")
    print("\n" + "=" * 72 + f"\nTOTAL RUN COST  ({args.model})\n" + "=" * 72)
    print(inst.cost_summary(total_usage, args.model))
    print(f"\n[briefings] {brief_dir}")

    out = args.out or str(HERE / f"network_{args.topology}_{stamp}.json")
    pathlib.Path(out).write_text(json.dumps({
        "model": args.model, "topology": args.topology,
        "institutes": args.institutes, "net_rounds": args.net_rounds,
        "inst_rounds": args.inst_rounds, "problem": problem,
        "briefings_dir": str(brief_dir), "aborted": abort,
        "final_positions": positions, "usage": total_usage, "cost_usd": total_cost,
        "history": history,
    }, indent=2), encoding="utf-8")
    print(f"\n[written] {out}   [events] {args.events}")


if __name__ == "__main__":
    main()
