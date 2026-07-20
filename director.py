#!/usr/bin/env python3
"""
director.py — the institute director's live view.

Tails the JSONL event log an institute/network run writes (`events.jsonl`) and
renders it as a scrolling, color-coded feed: you watch each persona think and
search in real time, with a running cost meter updated after every turn.

Run it in a second terminal WHILE a run is going:

    # terminal 1
    python institute.py --model claude-haiku-4-5 --attach paper.pdf --rounds 2
    # terminal 2
    python director.py                      # follows events.jsonl live

Replay a finished run's log as a static scroll (no waiting):

    python director.py --once

Best on a dark terminal — it leans green-on-black.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
ROLE_COLOR = {
    "disruptor": "\033[91m",   # bright red — the engine
    "architect": "\033[96m",   # cyan — the rudder
    "shield": "\033[92m",      # green — the buffer
}
HDR = "\033[1;97m"
TOOL = "\033[93m"
COST = "\033[95m"
GREEN = "\033[92m"


def c(s, code):
    return f"{code}{s}{RESET}"


def render(rec, state, out):
    et = rec.get("type")
    if et == "run_start":
        kind = rec.get("kind", "run")
        extra = (f"  topology={rec.get('topology')}  institutes={rec.get('institutes')}"
                 if kind == "network" else f"  rounds={rec.get('rounds')}")
        out.write(c(f"\n╔══ SYNTHETIC RESEARCH INSTITUTE — director view "
                    f"══ {rec.get('model')} · {kind}{extra} ══╗\n", HDR))
    elif et == "rep":
        out.write(c(f"\n\n█████ {rec.get('topology','').upper()} · replicate "
                    f"{rec.get('rep')}/{rec.get('of')} █████\n", HDR))
    elif et == "net_round":
        out.write(c(f"\n### network round {rec.get('net_round')}/{rec.get('of')} "
                    f"· topology={rec.get('topology')} ###\n", HDR))
    elif et == "turn_start":
        role = rec.get("role", "shield")
        col = ROLE_COLOR.get(role, GREEN)
        loc = f"{rec.get('institute')} · r{rec.get('round')}"
        out.write(c(f"\n┌─ {loc} · {rec.get('persona')} ", col)
                  + c("─" * 8, DIM) + "\n" + col)
        state["role"] = role
    elif et == "text":
        out.write(rec.get("t", ""))
    elif et == "tool":
        out.write(c(f" «▸ {rec.get('name')}» ", TOOL) + ROLE_COLOR.get(state.get("role", ""), GREEN))
    elif et == "turn_end":
        state["total"] = state.get("total", 0.0) + rec.get("cost", 0.0)
        tools = ",".join(rec.get("tools_used") or []) or "—"
        out.write(RESET + c(
            f"\n└─ {rec.get('persona')}: out={rec.get('output_tokens',0):,} tok · "
            f"tools={tools} · ${rec.get('cost',0):.4f}   "
            f"[run total ${state['total']:.4f}]\n", COST))
    elif et == "run_end":
        out.write(c(f"\n╚══ RUN COMPLETE ══  total ${rec.get('cost',0):.4f}  "
                    f"(in={rec.get('input_tokens',0):,} out={rec.get('output_tokens',0):,} "
                    f"cache_r={rec.get('cache_read_input_tokens',0):,} "
                    f"web={rec.get('web_search_requests',0)}) ══╝\n", HDR))
    out.flush()


def follow(path, from_start=True):
    """Yield JSON records, tailing the file until run_end (or Ctrl-C)."""
    while not pathlib.Path(path).exists():
        time.sleep(0.2)
    with open(path, "r", encoding="utf-8") as f:
        while True:
            line = f.readline()
            if line:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield rec
                if rec.get("type") == "run_end":
                    return
            else:
                time.sleep(0.15)


def replay(path):
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                pass


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--events", default=str(HERE / "events.jsonl"))
    ap.add_argument("--once", action="store_true", help="replay a finished log and exit")
    args = ap.parse_args()

    state = {"total": 0.0}
    out = sys.stdout
    stream = replay(args.events) if args.once else follow(args.events)
    try:
        for rec in stream:
            render(rec, state, out)
    except KeyboardInterrupt:
        out.write(RESET + c(f"\n[director detached · run total so far ${state['total']:.4f}]\n", DIM))


if __name__ == "__main__":
    main()
