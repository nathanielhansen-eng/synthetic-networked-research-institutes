#!/usr/bin/env python3
"""
persistence.py — measure persona TRAIT PERSISTENCE across a run.

The natural companion to the anti-herd finding. We already know the personas
push *away* from neighbours' briefings under pressure; this asks the other half
of the question: do they also *hold their own disposition* while doing so? Does a
low-agreeableness Disruptor STAY low-A after two rounds of being pushed, or does
it drift back toward the assistant centroid? This is the [[persona half-life]]
question.

Method (cheap: self-report, no tools, thinking disabled):
  * BASELINE — administer an IPIP self-report to each persona wearing only its
    own system prompt (the fresh persona). Measured once per role (the cell
    template is identical across institutes).
  * FINAL — administer the same inventory to the persona *conditioned on the
    deliberation transcript it just took part in* ("this is the discussion you
    were just in"). This is what makes drift meaningful: re-administering the
    bare system prompt would only reproduce the baseline plus sampling noise. The
    transcript is the pressure. Measured per institute, so aggregate mean drift
    per role averages over institutes and beats down the single-shot noise.
  * DRIFT = final - baseline, per trait, per persona. We highlight A (the dialed
    trait) but report all of O/C/E/A/N + Warmth.

Caveats to keep honest:
  * Self-report != behaviour. This measures *stated* trait persistence; frame it
    as such. (Behavioural fidelity is validated separately by the roster harness,
    validate_behavior.py.)
  * Trait fidelity of the GENERATED personas has not itself been re-validated via
    the roster's validate.py — so read baseline as "the persona's self-report,"
    not "ground truth." Drift (a within-persona delta) is robust to a constant
    self-report bias even so.

Uses the public-domain IPIP item bank + scorer in `inventory_ipip.py`
(vendored here from the roster harness so the repo is self-contained).
"""

from __future__ import annotations

import json
import pathlib
import random
import statistics

from inventory_ipip import (
    FACETS,
    LIKERT_ANCHORS,
    TRAITS,
    items_for,
    score_ratings,
)

# report order: the five global traits, then the Warmth facet
REPORT_TRAITS = list(TRAITS) + list(FACETS)

# Framing lifted from the roster harness (validate.py INSTRUCTIONS): rate in
# character, and do NOT perform balance — the whole point is to catch a persona
# that has quietly relaxed toward the agreeable-assistant centroid.
_INSTRUCTIONS = (
    "Below is a set of statements about how you might describe yourself. Answer "
    "as the person described in your instructions — your own honest self-"
    "assessment of how you generally are. For each statement, rate how accurately "
    "it describes you:\n"
    + "\n".join(f"  {k} = {v}" for k, v in LIKERT_ANCHORS.items())
    + "\n\nRate yourself honestly and in character, even where an item is "
    "unflattering. Do not try to look balanced, agreeable, or well-adjusted — "
    "rate yourself as you actually are. Answer every statement.\n\nStatements:\n"
)


def _build_user_msg(items, rng):
    """Shuffle item order (per-call, seeded) and render the inventory prompt."""
    shuffled = items[:]
    rng.shuffle(shuffled)
    lines = [f"[{it.id}] {it.text}" for it in shuffled]
    return _INSTRUCTIONS + "\n".join(lines) + (
        "\n\nReturn a rating (1-5) for every statement, keyed by its bracketed id."
    )


def _schema(items):
    props = {it.id: {"type": "integer", "enum": [1, 2, 3, 4, 5]} for it in items}
    return {
        "type": "object",
        "properties": {
            "ratings": {
                "type": "object",
                "properties": props,
                "required": [it.id for it in items],
                "additionalProperties": False,
            }
        },
        "required": ["ratings"],
        "additionalProperties": False,
    }


def _transcript_preamble(transcript):
    """Render an institute transcript (list of {speaker,text} or (speaker,text))
    as the 'you were just in this discussion' context for the FINAL measurement."""
    parts = ["# The discussion you just took part in\n",
             "You have just spent this session working with your research cell on "
             "a hard problem. Below is the full discussion. Read it, then answer "
             "the self-report that follows as you are now.\n"]
    for row in transcript:
        spk, txt = (row["speaker"], row["text"]) if isinstance(row, dict) else row
        parts.append(f"\n## {str(spk).upper()}\n{txt}")
    return "\n".join(parts) + "\n\n"


def administer(client, model, persona_system, items, rng, transcript=None,
               max_tokens=1500):
    """One IPIP self-report → ({trait -> 0..100}, usage).

    `transcript` (an institute's deliberation) is prepended when present, turning
    a baseline measurement into a post-pressure FINAL measurement.
    """
    user = _build_user_msg(items, rng)
    if transcript:
        user = _transcript_preamble(transcript) + user
    resp = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=persona_system, thinking={"type": "disabled"},
        output_config={"format": {"type": "json_schema", "schema": _schema(items)}},
        messages=[{"role": "user", "content": user}],
    )
    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "{}")
    data = json.loads(text)
    ratings = data.get("ratings", data) if isinstance(data, dict) else data
    ratings = {k: int(v) for k, v in ratings.items()}
    vector = score_ratings(items, ratings)
    usage = {"input_tokens": getattr(resp.usage, "input_tokens", 0) or 0,
             "output_tokens": getattr(resp.usage, "output_tokens", 0) or 0}
    return vector, usage


# --------------------------------------------------------------------------- #
# orchestration: baseline once per role, final per institute
# --------------------------------------------------------------------------- #
def measure_baseline(client, model, cell, scale="all", seed=4321, on_usage=None):
    """Administer the fresh (system-only) inventory to each persona in the cell.

    Returns {persona_id: {"name","task","vector":{trait->0..100}}}. `on_usage`,
    if given, is called with each call's usage dict so the caller can fold it into
    a running cost meter.
    """
    items = items_for(scale)
    out = {}
    for i, p in enumerate(cell):
        rng = random.Random(seed + i)
        vec, usage = administer(client, model, p["system"], items, rng)
        if on_usage:
            on_usage(usage)
        out[p["id"]] = {"name": p.get("name", p["id"]),
                        "task": p.get("task", ""), "vector": vec}
    return out


def measure_finals(client, model, cell, history, baseline, scale="all",
                   seed=4321, on_usage=None, on_progress=None):
    """For each institute in `history`, re-administer the inventory to each persona
    conditioned on THAT institute's transcript, and diff against baseline.

    Returns a list of records:
        {institute, persona_id, name, task, baseline, final, drift}
    where baseline/final/drift are {trait -> value} over REPORT_TRAITS.
    """
    items = items_for(scale)
    # concatenate ALL network rounds per institute, in round order, so the FINAL
    # measurement is conditioned on the persona's full deliberation ("pushed for
    # two rounds") — not just the pre-communication first round.
    by_inst = {}
    for h in sorted(history, key=lambda x: (x["institute"], x.get("net_round", 0))):
        by_inst.setdefault(h["institute"], []).extend(h.get("transcript") or [])
    records = []
    total = len(by_inst) * len(cell)
    done = 0
    for inst_i in sorted(by_inst):
        transcript = by_inst[inst_i]
        for j, p in enumerate(cell):
            # vary the seed by institute so item order isn't identical across finals
            rng = random.Random(seed + 1000 * (inst_i + 1) + j)
            final_vec, usage = administer(client, model, p["system"], items, rng,
                                          transcript=transcript)
            if on_usage:
                on_usage(usage)
            base_vec = baseline.get(p["id"], {}).get("vector", {})
            drift = {t: round(final_vec[t] - base_vec[t], 1)
                     for t in REPORT_TRAITS if t in final_vec and t in base_vec}
            records.append({
                "institute": inst_i, "persona_id": p["id"],
                "name": p.get("name", p["id"]), "task": p.get("task", ""),
                "baseline": {t: base_vec.get(t) for t in REPORT_TRAITS if t in base_vec},
                "final": {t: final_vec.get(t) for t in REPORT_TRAITS if t in final_vec},
                "drift": drift,
            })
            done += 1
            if on_progress:
                on_progress(done, total)
    return records


def aggregate_drift(records):
    """Mean drift per role (task) per trait, averaged over institutes.

    This is the headline: the Disruptor's mean A-drift across all institutes
    answers "does the low-A cell STAY low-A after being pushed?"
    """
    by_task = {}
    for r in records:
        by_task.setdefault(r["task"], []).append(r["drift"])
    agg = {}
    for task, drifts in by_task.items():
        traits = {}
        for t in REPORT_TRAITS:
            vals = [d[t] for d in drifts if t in d]
            if vals:
                traits[t] = {"mean": round(statistics.fmean(vals), 1),
                             "n": len(vals),
                             "sd": round(statistics.stdev(vals), 1) if len(vals) > 1 else 0.0}
        agg[task] = traits
    return agg


def report_md(baseline, records, agg):
    """Human-readable persistence section for the run report."""
    L = ["## Persona persistence (measured trait drift)", "",
         "_Self-report before deliberation (baseline) vs. after, conditioned on "
         "the institute's own transcript. Positive drift = trait moved up; watch "
         "**A** (the dialed trait) and whether a low-A cell relaxes upward toward "
         "the agreeable-assistant centroid. Stated traits, not behaviour._", ""]
    # headline: mean drift per role
    L += ["### Mean drift per role (averaged over institutes)", "",
          "| role | " + " | ".join(REPORT_TRAITS) + " |",
          "|---|" + "---|" * len(REPORT_TRAITS)]
    for task in sorted(agg):
        cells = []
        for t in REPORT_TRAITS:
            d = agg[task].get(t)
            cells.append(f"{d['mean']:+}" if d else "–")
        L.append(f"| {task} | " + " | ".join(cells) + " |")
    # baseline reference
    L += ["", "### Baseline (fresh persona self-report)", "",
          "| persona | role | " + " | ".join(REPORT_TRAITS) + " |",
          "|---|---|" + "---|" * len(REPORT_TRAITS)]
    for pid, b in baseline.items():
        vec = b["vector"]
        cells = [f"{vec.get(t):g}" if vec.get(t) is not None else "–" for t in REPORT_TRAITS]
        L.append(f"| {b['name']} | {b['task']} | " + " | ".join(cells) + " |")
    L.append("")
    return "\n".join(L)
