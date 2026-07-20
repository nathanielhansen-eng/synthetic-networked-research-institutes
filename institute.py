#!/usr/bin/env python3
"""
institute.py — one synthetic research institute: a flat 3-persona cell
(Disruptor / Architect / Shield) working an open empirical problem, with live
web search and code execution.

The persona *content* (validated Big-Five commitment architecture) and the
network *theory* already exist in this repo; this file is the missing glue —
the agent runtime that lets the personas actually do open-ended work together.

Design notes
------------
* Personas are the archetypes from `../team_size_and_personality_mix.md`,
  written in the same commitment-architecture format the roster harness
  validates (identity+vector, behavioral spec, no-fold clause, weighted yield),
  so the traits hold under the pressure of a live debate.
* Tools are Anthropic server-side tools, so "search online and analyze data as
  they see fit" is a `tools=[...]` list, not a subsystem:
    - web_search   (basic variant — clean separation from code execution)
    - code_execution (sandboxed Python: pandas/numpy/scipy/matplotlib)
  We deliberately use the *basic* web_search rather than the dynamic-filtering
  variant, because the latter runs code execution under the hood and declaring
  a second code_execution tool alongside it confuses the model.
* The turn loop is a MANUAL agentic loop that handles `stop_reason=="pause_turn"`
  explicitly. Server-side tools routinely pause mid-turn; the SDK tool-runner
  does NOT auto-resume a paused turn (it silently truncates), so we resume by
  hand.

Usage
-----
    python institute.py --problem-file problems.md --rounds 2
    python institute.py --dry-run                 # assemble prompts, no API calls
    python institute.py --rounds 1 --model claude-haiku-4-5   # cheap smoke test
"""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import json
import pathlib
import sys
import time

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

import anthropic

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_MODEL = "claude-opus-4-8"
ROLE_ORDER = ["disruptor", "architect", "shield"]

WEB_SEARCH = {"type": "web_search_20250305", "name": "web_search"}
CODE_EXEC = {"type": "code_execution_20260521", "name": "code_execution"}

# ---- pricing ($ per 1M tokens; input, output) -------------------------------
PRICING = {
    "claude-opus-4-8": (5.0, 25.0), "claude-opus-4-7": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0), "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0), "claude-fable-5": (10.0, 50.0),
}
WEB_SEARCH_PER_1K = 10.0  # Anthropic web-search tool, approx; billed separately

USAGE_KEYS = ("input_tokens", "output_tokens",
              "cache_read_input_tokens", "cache_creation_input_tokens",
              "web_search_requests")


def _price(model):
    for k, v in PRICING.items():
        if model.startswith(k):
            return v
    return (5.0, 25.0)


def cost_of(usage: dict, model: str) -> float:
    pin, pout = _price(model)
    u = usage
    tok = (u.get("input_tokens", 0) * pin
           + u.get("output_tokens", 0) * pout
           + u.get("cache_read_input_tokens", 0) * pin * 0.1
           + u.get("cache_creation_input_tokens", 0) * pin * 1.25) / 1e6
    return tok + u.get("web_search_requests", 0) * WEB_SEARCH_PER_1K / 1000.0


def estimate_cost(model, n_institutes, net_rounds, inst_rounds, cell_size,
                  max_tokens, max_web, ground_truth=False, track_persistence=False,
                  adjudicate=False):
    """Rough pre-run cost estimate → (low, high) USD, using the same pricing table
    and turn-count formula as the live meter. Deliberately approximate: real token
    use depends on the problem and how much the transcript grows; the hard cost
    ceiling is the actual guardrail. Recalibrated against a 2026-07-20 Sonnet 5
    app run (8 turns at web=3: ~46K input tokens/turn and ~1.9x max_tokens output
    /turn, $1.94 actual — web-search payloads and the accumulated transcript
    dominate input, and one turn spans several API calls)."""
    pin, pout = _price(model)
    # deliberation turns: size personas × inst_rounds, + 1 briefing turn, per
    # institute per network round (matches app.py's expected_turns).
    turns = n_institutes * net_rounds * (inst_rounds * cell_size + 1)
    # input/turn: persona + transcript base, plus web-search result payloads —
    # the dominant term, and it rides along in every later call of the turn.
    in_lo = 6000 + 6000 * max_web
    in_hi = 12000 + 14000 * max_web
    # output/turn: pause_turn resumes mean a turn spans several API calls, so
    # realized output routinely exceeds max_tokens.
    out_lo, out_hi = 1.0 * max_tokens, 2.5 * max_tokens
    web_per_turn = 0.66 * max_web       # briefing/synthesis turns rarely search

    def _turn(in_tok, out, webs):
        return (in_tok * pin + out * pout) / 1e6 + webs * WEB_SEARCH_PER_1K / 1000.0

    lo = turns * _turn(in_lo, out_lo, 0.4 * web_per_turn)
    hi = turns * _turn(in_hi, out_hi, web_per_turn)
    # judge pass: 1 classify call per briefing (+1 correctness call under ground truth)
    briefings = n_institutes * net_rounds
    jcalls = briefings * (2 if ground_truth else 1)
    jcost = jcalls * (1500 * pin + 500 * pout) / 1e6
    lo += jcost
    hi += jcost
    if adjudicate:
        # 1 call per round-2+ briefing; input = attacker briefing + its neighbour
        # briefings from the previous round. Smoke-observed: ~4.7K in / ~2.2K out
        # with ONE target briefing; more neighbours = more input.
        acalls = n_institutes * max(0, net_rounds - 1)
        acost = acalls * (8000 * pin + 2000 * pout) / 1e6
        lo += acost
        hi += acost
    if track_persistence:
        pcalls = cell_size * (1 + n_institutes)     # baseline once + finals per institute
        pcost = pcalls * (2000 * pin + 800 * pout) / 1e6
        lo += pcost
        hi += pcost
    return lo, hi


def blank_usage() -> dict:
    return {k: 0 for k in USAGE_KEYS}


def add_usage(acc: dict, u: dict):
    for k in USAGE_KEYS:
        acc[k] = acc.get(k, 0) + u.get(k, 0)


def cost_summary(usage: dict, model: str) -> str:
    return (f"tokens in={usage['input_tokens']:,} out={usage['output_tokens']:,} "
            f"cache_r={usage['cache_read_input_tokens']:,} "
            f"cache_w={usage['cache_creation_input_tokens']:,} "
            f"web={usage['web_search_requests']}  |  ${cost_of(usage, model):.4f}")


class EventSink:
    """Append-only JSONL event log the director view tails; also carries per-turn context."""

    def __init__(self, path=None, truncate=True):
        self.f = open(path, "w" if truncate else "a", buffering=1, encoding="utf-8") if path else None
        self.ctx = {}

    def set_context(self, **kw):
        self.ctx.update(kw)

    def emit(self, etype, **payload):
        if not self.f:
            return
        rec = {"ts": time.time(), "type": etype, **self.ctx, **payload}
        self.f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def close(self):
        if self.f:
            self.f.close()


def resolve_tools(model: str, code_mode: str, max_web=None):
    """Basic web_search always; code execution per --code (auto = off on Haiku).

    Haiku's support for the code-execution server tool is uncertain and this
    class of problem (literature synthesis) rarely needs it, so `auto` drops it
    on Haiku to keep early trials from 400-ing; force it with --code on.
    `max_web` caps web_search invocations per turn (bounds cost and variance).
    """
    web = dict(WEB_SEARCH)
    if max_web:
        web["max_uses"] = int(max_web)
    tools = [web]
    want_code = {"on": True, "off": False,
                 "auto": "haiku" not in model.lower()}[code_mode]
    if want_code:
        tools.append(CODE_EXEC)
    return tools


def load_attachment_block(path: str, extract_pdf: bool = True) -> dict:
    """Build a document block for a file.

    A base64 PDF is counted at ~1 token per 4 bytes of *encoded* data — a 44-page
    paper balloons to ~400K tokens, which dominates the bill. So by default we
    extract the PDF's text (≈10x smaller) and attach that; pass extract_pdf=False
    (CLI: --pdf-mode base64) to send the real PDF when layout/figures matter.
    """
    p = pathlib.Path(path)
    if p.suffix.lower() == ".pdf" and extract_pdf:
        try:
            import pypdf
            text = "\n\n".join(pg.extract_text() or "" for pg in pypdf.PdfReader(str(p)).pages)
            src = {"type": "text", "media_type": "text/plain", "data": text}
        except Exception as e:  # noqa: BLE001
            print(f"[warn] pypdf extract failed ({e}); falling back to base64 PDF", flush=True)
            data = base64.standard_b64encode(p.read_bytes()).decode("ascii")
            src = {"type": "base64", "media_type": "application/pdf", "data": data}
    elif p.suffix.lower() == ".pdf":
        data = base64.standard_b64encode(p.read_bytes()).decode("ascii")
        src = {"type": "base64", "media_type": "application/pdf", "data": data}
    else:
        src = {"type": "text", "media_type": "text/plain", "data": p.read_text(encoding="utf-8")}
    return {"type": "document", "source": src, "title": p.name, "citations": {"enabled": True}}


# --------------------------------------------------------------------------- #
# persona loading
# --------------------------------------------------------------------------- #
def load_persona(path: pathlib.Path) -> dict:
    """Parse a persona markdown file into {id, name, vector, system}."""
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        meta = yaml.safe_load(fm) or {}
    else:
        meta, body = {}, raw
    return {
        "id": meta.get("persona_id", path.stem),
        "name": meta.get("name", path.stem),
        "role": meta.get("role", ""),
        "vector": meta.get("big_five", {}),
        "system": body.strip(),
    }


def load_cell(personas_dir: pathlib.Path) -> list:
    """Ordered list of persona dicts; each carries a `task` (which ROLE_TASK to use).
    The last agent is the synthesizer/briefer."""
    agents = []
    for role in ROLE_ORDER:
        p = load_persona(personas_dir / f"{role}.md")
        p["task"] = role
        agents.append(p)
    return agents


# --------------------------------------------------------------------------- #
# prompt assembly
# --------------------------------------------------------------------------- #
ROLE_TASK = {
    "disruptor": (
        "It is your move. Either PROPOSE the boldest hypothesis the evidence "
        "will bear about the problem, or ATTACK the cell's current position at "
        "its weakest point. Search ACROSS disciplines — linguistics, "
        "psycholinguistics, cultural/cognitive psychology, and beyond, not just "
        "the philosophy canon — for a surprising, on-point datum, and use "
        "code_execution to run the quickest test that could kill your own idea. "
        "Be blunt and specific. End with the single sharpest claim you're "
        "willing to stake."
    ),
    "architect": (
        "It is your move. Take the Disruptor's proposal (and any neighbor-"
        "institute positions) and make it OPERATIONAL: state exactly what would "
        "confirm or refute it, then actually do it — use web_search to find the "
        "sources (from whatever field has them — linguistics, psychology, "
        "translation studies, not only philosophy) and code_execution to pull, "
        "clean, and analyze real numbers. Report precisely what held up and what "
        "didn't, with the figures and citations attached."
    ),
    "shield": (
        "It is your move. SYNTHESIZE the cell's current position from the "
        "Disruptor's proposal and the Architect's analysis. State (a) one clear "
        "claim, (b) what specific evidence would falsify it, and (c) a calibrated "
        "confidence between 0 and 1. Keep the disagreement honest — do not "
        "manufacture consensus. Decide, generously but not credulously, what to "
        "take from any neighbor institutes."
    ),
}


BRIEFING_PROMPT = """You are writing this institute's DIRECTOR BRIEFING — a
standalone markdown document the research director reads WITHOUT seeing your
internal discussion, and which may be handed to OTHER institutes as their input.
Synthesize the cell's work into exactly this template, filling every section
substantively and concretely (name the specific papers, cases, and distinctions
the cell actually used):

# Institute Briefing — {label}

**Problem.** <one-sentence restatement>

## Conclusion
<the cell's current best answer, 2-4 sentences>

## Confidence
<a single number 0.00-1.00> — <one line on why that level>

## Key reasons and evidence
- <bullets; cite specific sources/data the cell relied on>

## What would falsify this
- <bullets>

## Directions for further research
- <concrete, actionable next studies, analyses, or probes>

## Open disagreements in the cell
- <where the Disruptor and Architect still diverge, if they do>

Write only the briefing document — no preamble, no sign-off."""


def build_user_prompt(problem, role, transcript, neighbor_ctx, round_i, rounds):
    parts = [f"# The problem\n{problem}\n"]
    if neighbor_ctx:
        parts.append(f"# Positions from neighboring institutes (Zollman channel)\n{neighbor_ctx}\n")
    if transcript:
        parts.append("# Your institute's discussion so far")
        for spk, txt in transcript:
            parts.append(f"\n## {spk.upper()}\n{txt}")
        parts.append("")
    parts.append(f"# Your task (round {round_i + 1} of {rounds})\n{ROLE_TASK[role]}")
    return "\n".join(parts)


def build_user_content(problem, role, transcript, neighbor_ctx, round_i, rounds, attachments):
    """Content list = attached document blocks (cached) followed by the text task."""
    text = build_user_prompt(problem, role, transcript, neighbor_ctx, round_i, rounds)
    if not attachments:
        return text
    blocks = [dict(b) for b in attachments]
    blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}  # cache the paper
    blocks.append({"type": "text", "text": text})
    return blocks


# --------------------------------------------------------------------------- #
# the agentic turn (manual loop, pause_turn-safe)
# --------------------------------------------------------------------------- #
def agent_turn(client, model, system, content, tools, sink=None,
               max_tokens=8000, max_pause=10):
    """Stream one persona turn to completion, emitting live events and tallying usage.

    Streams text deltas + tool starts to `sink` (for the director view), and
    resumes server-tool `pause_turn` boundaries by hand (the SDK tool-runner
    would silently truncate them).
    """
    messages = [{"role": "user", "content": content}]
    usage = blank_usage()
    tools_used = []
    pauses = 0

    while True:
        with client.messages.stream(model=model, max_tokens=max_tokens,
                                    system=system, tools=tools, messages=messages) as stream:
            for event in stream:
                et = getattr(event, "type", None)
                if et == "content_block_start":
                    cb = event.content_block
                    if getattr(cb, "type", None) == "server_tool_use":
                        nm = getattr(cb, "name", "tool")
                        tools_used.append(nm)
                        if sink:
                            sink.emit("tool", name=nm)
                elif et == "content_block_delta":
                    d = event.delta
                    if getattr(d, "type", None) == "text_delta" and sink:
                        sink.emit("text", t=d.text)
            resp = stream.get_final_message()

        u = resp.usage
        for k in ("input_tokens", "output_tokens",
                  "cache_read_input_tokens", "cache_creation_input_tokens"):
            usage[k] += getattr(u, k, 0) or 0
        st = getattr(u, "server_tool_use", None)
        if st:
            usage["web_search_requests"] += getattr(st, "web_search_requests", 0) or 0

        if resp.stop_reason == "pause_turn" and pauses < max_pause:
            pauses += 1
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break

    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return text.strip(), tools_used, usage


# --------------------------------------------------------------------------- #
# one institute run
# --------------------------------------------------------------------------- #
def generate_briefing(client, model, problem, shield_system, transcript, label,
                      sink=None, max_tokens=4000):
    """One tool-free synthesis turn (Shield voice) → standalone briefing markdown."""
    parts = [f"# The problem\n{problem}\n", "# The cell's full discussion"]
    for spk, txt in transcript:
        parts.append(f"\n## {spk.upper()}\n{txt}")
    parts.append("\n# Your task\n" + BRIEFING_PROMPT.format(label=label))
    content = "\n".join(parts)
    if sink:
        sink.set_context(institute=label, round="brief", persona="Briefing", role="shield")
        sink.emit("turn_start")
    text, _tu, usage = agent_turn(client, model, shield_system, content, [], sink, max_tokens)
    if sink:
        sink.emit("turn_end", chars=len(text), tools_used=[],
                  cost=cost_of(usage, model), **usage)
    return text.strip(), usage


def run_institute(client, model, problem, cell, rounds, neighbor_ctx="",
                  label="institute", max_tokens=8000, verbose=True,
                  attachments=None, tools=None, sink=None, briefing=True):
    attachments = attachments or []
    tools = tools if tools is not None else [WEB_SEARCH]
    agents = list(cell.values()) if isinstance(cell, dict) else cell  # dict (legacy) or list
    transcript = []
    inst_usage = blank_usage()
    for r in range(rounds):
        for p in agents:
            task = p.get("task", "architect")
            if sink:
                sink.set_context(institute=label, round=r + 1, persona=p["name"], role=task)
                sink.emit("turn_start")
            content = build_user_content(problem, task, transcript, neighbor_ctx, r, rounds, attachments)
            text, tools_used, usage = agent_turn(client, model, p["system"], content,
                                                 tools, sink, max_tokens)
            add_usage(inst_usage, usage)
            transcript.append((p["name"], text))
            if sink:
                sink.emit("turn_end", chars=len(text), tools_used=tools_used,
                          cost=cost_of(usage, model), **usage)
            if verbose:
                tag = f"[{label}] r{r+1} {p['name']}"
                extra = f" (tools: {','.join(tools_used)})" if tools_used else ""
                print(f"{tag}{extra}  [{cost_summary(usage, model)}]\n{text}\n{'-'*72}", flush=True)

    brief = ""
    if briefing:
        brief, b_usage = generate_briefing(client, model, problem, agents[-1]["system"],
                                           transcript, label, sink, max_tokens=4000)
        add_usage(inst_usage, b_usage)
        if verbose:
            print(f"[{label}] BRIEFING\n{brief}\n{'='*72}", flush=True)

    # The shared position IS the briefing when we have one — so a neighbor
    # institute receives the full report, not just a paragraph.
    position = brief if brief else extract_position(transcript)
    return {"label": label, "position": position, "briefing": brief,
            "transcript": transcript, "usage": inst_usage}


def extract_position(transcript):
    """The Shield speaks last each round; its final turn is the institute's position."""
    for name, text in reversed(transcript):
        if name.lower().startswith("the shield") or "shield" in name.lower():
            return text
    return transcript[-1][1] if transcript else ""


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--problem-file", default=str(HERE / "problems.md"))
    ap.add_argument("--problem", default=None, help="inline problem text (overrides --problem-file)")
    ap.add_argument("--personas-dir", default=str(HERE / "personas"))
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--attach", action="append", default=[],
                    help="attach a PDF/text file as context (repeatable)")
    ap.add_argument("--code", choices=["auto", "on", "off"], default="auto",
                    help="code-execution tool: auto=off on Haiku, on/off to force")
    ap.add_argument("--pdf-mode", choices=["text", "base64"], default="text",
                    help="text=extract PDF text (~10x cheaper); base64=send real PDF")
    ap.add_argument("--events", default=str(HERE / "events.jsonl"),
                    help="live event log for the director view (director.py tails this)")
    ap.add_argument("--out", default=None, help="write JSON transcript here")
    ap.add_argument("--dry-run", action="store_true", help="assemble prompts, make no API calls")
    args = ap.parse_args()

    if args.problem:
        problem = args.problem.strip()
    else:
        problem = _extract_active_problem(pathlib.Path(args.problem_file).read_text(encoding="utf-8"))

    cell = load_cell(pathlib.Path(args.personas_dir))
    tools = resolve_tools(args.model, args.code)
    attachments = [load_attachment_block(a, extract_pdf=(args.pdf_mode == "text")) for a in args.attach]

    if args.dry_run:
        print("=== DRY RUN: personas ===")
        for p in cell:
            print(f"  {p.get('task',''):10s} {p['name']:18s} vector={p['vector']}  ({len(p['system'])} chars)")
        print(f"\nmodel={args.model}  tools={[t['name'] for t in tools]}  "
              f"attachments={[a.get('title') for a in attachments]}")
        print("\n=== sample round-1 Disruptor prompt (text portion) ===\n")
        print(build_user_prompt(problem, "disruptor", [], "", 0, args.rounds))
        return

    client = anthropic.Anthropic(max_retries=6)
    sink = EventSink(args.events)
    sink.emit("run_start", model=args.model, rounds=args.rounds, kind="institute")
    result = run_institute(client, args.model, problem, cell, args.rounds,
                           max_tokens=args.max_tokens, attachments=attachments,
                           tools=tools, sink=sink)
    total_cost = cost_of(result["usage"], args.model)
    sink.emit("run_end", cost=total_cost, **result["usage"])
    sink.close()

    print("\n" + "=" * 72 + "\nINSTITUTE BRIEFING\n" + "=" * 72)
    print(result["briefing"] or result["position"])
    print("\n" + "=" * 72 + f"\nRUN COST  ({args.model})\n" + "=" * 72)
    print(cost_summary(result["usage"], args.model))

    stamp = f"{_dt.datetime.now():%Y%m%d_%H%M%S}"
    brief_path = ""
    if result["briefing"]:
        bdir = HERE / "briefings"
        bdir.mkdir(exist_ok=True)
        brief_path = str(bdir / f"institute_{stamp}.md")
        pathlib.Path(brief_path).write_text(result["briefing"], encoding="utf-8")

    out = args.out or str(HERE / f"run_{stamp}.json")
    pathlib.Path(out).write_text(json.dumps({
        "model": args.model, "rounds": args.rounds, "problem": problem,
        "briefing": result["briefing"], "briefing_file": brief_path,
        "position": result["position"], "usage": result["usage"], "cost_usd": total_cost,
        "transcript": [{"speaker": s, "text": t} for s, t in result["transcript"]],
    }, indent=2), encoding="utf-8")
    tail = f"   [briefing] {brief_path}" if brief_path else ""
    print(f"\n[written] {out}   [events] {args.events}{tail}")


def _extract_active_problem(md: str) -> str:
    """Pull the first '## ACTIVE' section from problems.md, else the whole file."""
    lines = md.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith("## active"):
            block = []
            for ln2 in lines[i + 1:]:
                if ln2.startswith("## "):
                    break
                block.append(ln2)
            return "\n".join(block).strip()
    return md.strip()


if __name__ == "__main__":
    main()
