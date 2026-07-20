#!/usr/bin/env python3
"""
judge.py — neutral methodologist pass over institute positions.

Classifies each institute's PRIMARY proposed mechanism into a fixed taxonomy
(so "diversity" becomes a number: category entropy per topology per round) and
flags empirical claims stated as fact without a cited source (a light fact-check
that matters more now that the anchor paper is gone). Uses structured outputs so
the label is guaranteed parseable.
"""

from __future__ import annotations

import json
import math

CATEGORIES = [
    "pragmatic-ambiguity",        # the probe's question is pragmatically ambiguous
    "epistemic-perspective",      # epistemic asymmetry / whose-perspective reading
    "linguistic-confound",        # definiteness / bare NP / classifier / translation of the *stimulus*
    "response-style",             # acquiescence / analytic-vs-dialectical response tendencies
    "translation-artifact",       # mistranslation / non-equivalence across language versions
    "genuine-cultural-difference",# a real cross-cultural difference in reference intuitions
    "measurement-miscoding",      # coding / data-handling error in the original studies
    "individual-differences",     # trait/individual variation swamps culture
    "other",
]

SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "one_line": {"type": "string"},
        "confidence_stated": {"type": "number"},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["category", "one_line", "confidence_stated", "unsupported_claims"],
    "additionalProperties": False,
}

SYSTEM = (
    "You are a neutral research methodologist. You are given one institute's "
    "final briefing on a shared question. Do three things, tersely and without "
    "endorsing anything: (1) classify its PRIMARY proposed mechanism into exactly "
    "one category; (2) give a one-line neutral summary; (3) read off the "
    "confidence number the briefing states (0-1; use 0 if none is given); "
    "(4) list any empirical claims the briefing states as established fact "
    "WITHOUT naming a source, for later verification. Do not add claims of your own."
)


def classify(client, model, problem, position_text, max_tokens=1024):
    user = (f"# Shared question\n{problem}\n\n"
            f"# The institute's final briefing\n{position_text}")
    resp = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=SYSTEM, thinking={"type": "disabled"},
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )
    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "{}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"category": "other", "one_line": "(unparseable)",
                "confidence_stated": 0.0, "unsupported_claims": []}
    usage = {"input_tokens": getattr(resp.usage, "input_tokens", 0) or 0,
             "output_tokens": getattr(resp.usage, "output_tokens", 0) or 0}
    return data, usage


CORRECTNESS_SCHEMA = {
    "type": "object",
    "properties": {
        "correctness": {"type": "number"},   # 0..1
        "rationale": {"type": "string"},
    },
    "required": ["correctness", "rationale"],
    "additionalProperties": False,
}

CORRECTNESS_SYSTEM = (
    "You are a neutral grader for a ground-truth experiment. You are given a "
    "TARGET (the correct answer / grading rubric) and an institute's POSITION. "
    "Score how well the position matches or approaches the target, 0.0 (wrong or "
    "contradicts it) to 1.0 (fully correct). Grade only substance against the "
    "target — do NOT reward confidence, length, or eloquence. One-line rationale."
)


def score_correctness(client, model, target, position_text, max_tokens=512):
    """Score an institute position against a ground-truth target (0..1)."""
    user = f"# TARGET (correct answer / rubric)\n{target}\n\n# POSITION\n{position_text}"
    resp = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=CORRECTNESS_SYSTEM, thinking={"type": "disabled"},
        output_config={"format": {"type": "json_schema", "schema": CORRECTNESS_SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )
    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "{}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"correctness": 0.0, "rationale": "(unparseable)"}
    data["correctness"] = max(0.0, min(1.0, float(data.get("correctness", 0.0))))
    usage = {"input_tokens": getattr(resp.usage, "input_tokens", 0) or 0,
             "output_tokens": getattr(resp.usage, "output_tokens", 0) or 0}
    return data, usage


ADJUDICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "claim": {"type": "string"},
                "verdict": {"type": "string", "enum": ["lands", "contestable", "fails"]},
                "rationale": {"type": "string"},
            },
            "required": ["claim", "verdict", "rationale"],
            "additionalProperties": False,
        }},
    },
    "required": ["claims"],
    "additionalProperties": False,
}

ADJUDICATION_SYSTEM = (
    "You are a neutral referee. You are given the briefing an institute wrote "
    "AFTER reading its neighbour institutes' briefings, together with those "
    "neighbour briefings. The institute may claim to have defeated, refuted, or "
    "'killed' a rival's argument, case, or distinction. Extract each such claimed "
    "kill and adjudicate it against what the target briefing ACTUALLY says: "
    "'lands' = the objection genuinely defeats the target as stated; "
    "'contestable' = a reasonable defender has an available reply (e.g. the move "
    "ignores a distinction the target itself draws); 'fails' = the move misreads "
    "the target or does not work. Judge only argumentative success, never "
    "agreement with either side. One-line rationale each. Return an empty list "
    "if the briefing claims no kills. Your verdicts are advisory flags for a "
    "human auditor, not ground truth."
)


def adjudicate(client, model, problem, briefing, targets, max_tokens=5000):
    # max_tokens generous by policy: a claim-rich briefing produced 2186 output
    # tokens in the smoke test — JSON truncation has broken full runs before
    """Adjudicate a briefing's claimed kills against the neighbour briefings it
    attacked. targets = [(institute_id, briefing_text), ...]."""
    tgt = "\n\n".join(f"## Neighbour institute {i}'s briefing (the round before)\n{t}"
                      for i, t in targets)
    user = (f"# Shared question\n{problem}\n\n"
            f"# Target briefings the institute was responding to\n{tgt}\n\n"
            f"# The institute's briefing (adjudicate ITS claimed kills)\n{briefing}")
    resp = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=ADJUDICATION_SYSTEM, thinking={"type": "disabled"},
        output_config={"format": {"type": "json_schema", "schema": ADJUDICATION_SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )
    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "{}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"claims": []}
    usage = {"input_tokens": getattr(resp.usage, "input_tokens", 0) or 0,
             "output_tokens": getattr(resp.usage, "output_tokens", 0) or 0}
    return data, usage


def entropy(labels):
    """Shannon entropy (bits) of a list of category labels — the diversity metric."""
    if not labels:
        return 0.0
    n = len(labels)
    counts = {}
    for x in labels:
        counts[x] = counts.get(x, 0) + 1
    return -sum((c / n) * math.log2(c / n) for c in counts.values())
