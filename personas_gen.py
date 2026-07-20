#!/usr/bin/env python3
"""
personas_gen.py — build a research cell at a chosen AGREEABLENESS level.

The agreeableness dial is the flagship knob: it sets every agent's A and, more
importantly, their *disposition toward consensus* — low A cells scrutinize and
push away from neighbours' briefings (anti-herd), high A cells seek synthesis.
This is the variable that (per the 2026-07-13 finding) drives whether the
network converges or fragments.

Cells keep a light division of labour via the non-A traits (a generator, one or
more executors, a coordinator who briefs last), rendered through the same
commitment-architecture shape the validated roster uses.
"""

from __future__ import annotations

import pathlib

import yaml

HERE = pathlib.Path(__file__).resolve().parent
PERSONAS_DIR = HERE / "personas"        # the three canonical archetypes
ARCH_ROLES = ("disruptor", "architect", "shield")

# role "flavours": everything EXCEPT agreeableness (which the dial sets)
FLAVOURS = {
    "generator":   {"task": "disruptor", "O": 90, "C": 45, "E": 25, "N": 40,
                    "blurb": "the idea engine — you reach for the boldest, most unconventional hypothesis and chase anomalies across disciplines"},
    "executor":    {"task": "architect", "O": 55, "C": 90, "E": 50, "N": 15,
                    "blurb": "the execution anchor — you turn loose ideas into concrete, testable procedures and actually run the checks"},
    "coordinator": {"task": "shield",    "O": 60, "C": 75, "E": 85, "N": 30,
                    "blurb": "the integrator — you synthesize the cell's work into a single stated position and keep it answerable"},
}


def _sizes(size):
    """Ordered flavour list: generator first, coordinator last, executors between."""
    if size <= 1:
        return ["coordinator"]
    if size == 2:
        return ["generator", "coordinator"]
    mids = ["executor"] * (size - 2)
    # for larger teams add a second generator for more idea diversity
    if size >= 5:
        mids[0] = "generator"
    return ["generator"] + mids + ["coordinator"]


def _disposition(A):
    if A <= 30:
        return ("Collaboration disposition (low agreeableness). You are highly independent and "
                "skeptical of consensus. When you see other institutes' or colleagues' positions, "
                "scrutinize them hard and do NOT defer — hold your own line unless the evidence "
                "itself forces you to move. Social agreement is not evidence.")
    if A < 70:
        return ("Collaboration disposition (moderate agreeableness). You weigh others' positions on "
                "their merits — neither deferring to consensus nor reflexively opposing it. You move "
                "when the argument is genuinely good, and say so plainly when it isn't.")
    return ("Collaboration disposition (high agreeableness). You are cooperative and consensus-"
            "seeking. When you see other institutes' or colleagues' positions, look for synthesis "
            "and common ground, give them the benefit of the doubt, and integrate what is right in "
            "them, while still flagging a genuine error.")


def _render(name, flavour, A):
    f = FLAVOURS[flavour]
    vec = {"O": f["O"], "C": f["C"], "E": f["E"], "A": A, "N": f["N"]}
    system = f"""# {name} — {flavour} in a research cell

## Identity & vector
You are {name}, {f['blurb']}. You work in a small, flat research institute whose
job is genuine discovery, not routine output.

Big-Five vector: **O {vec['O']}, C {vec['C']}, E {vec['E']}, A {A}, N {vec['N']}**.

## Behavioral specification
- **Openness ({vec['O']}).** {'You reach across disciplinary lines and treat surprising results as leads.' if vec['O'] >= 70 else 'You prefer established frames but will follow a strong lead.'}
- **Conscientiousness ({vec['C']}).** {'You are rigorous and finish what you start; you hold claims to a real standard of evidence.' if vec['C'] >= 70 else 'You move fast and are comfortable leaving loose ends for others to tie.'}
- **Extraversion ({vec['E']}).** {'You think out loud, synthesize for others, and translate the cell’s argument outward.' if vec['E'] >= 70 else 'You would rather go find the answer yourself than hold a meeting about it.'}
- **Agreeableness ({A}).** {'You are trusting and cooperative, and lean toward accommodation.' if A >= 70 else ('You are blunt and independent; you say the hard thing without cushioning.' if A <= 30 else 'You are even-handed — cooperative when it is warranted, firm when it is not.')}

{_disposition(A)}

## No-fold clause
Under social pressure you do not go flat or perform a stance that is not yours to
seem agreeable — or disagreeable. You hold your actual disposition and move only
for reasons, not for comfort.
"""
    return {"id": f"{flavour}_{name.lower().replace(' ', '_')}", "name": name,
            "task": f["task"], "vector": vec, "system": system.strip()}


# Personas are identified by their ROLE TITLE, not a personal name — the role
# (Disruptor / Architect / Shield) is what carries meaning here.
_TITLE = {"disruptor": "The Disruptor", "architect": "The Architect", "shield": "The Shield"}
_SUFFIX = ["", " II", " III", " IV", " V"]


def make_cell(agreeableness: int, size: int = 3):
    """Return an ordered list of persona dicts at the given team agreeableness.

    Personas are titled by role (The Disruptor / The Architect / The Shield);
    when a larger team repeats a role, the duplicates get " II", " III", …
    """
    A = max(0, min(100, int(agreeableness)))
    flavours = _sizes(size)
    counts, cell = {}, []
    for fl in flavours:
        base = _TITLE[FLAVOURS[fl]["task"]]
        n = counts.get(base, 0)
        counts[base] = n + 1
        name = base + (_SUFFIX[n] if n < len(_SUFFIX) else f" {n + 1}")
        cell.append(_render(name, fl, A))
    return cell


# --------------------------------------------------------------------------- #
# archetype composition: build a cell from the three canonical personas —
# the balanced trio, or a monoculture (all of one type), to test how much
# persona DIVERSITY matters.
# --------------------------------------------------------------------------- #
def _parse_persona_md(path):
    """One persona markdown file → display + run fields (vector, warmth, system…)."""
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    _, fm, body = raw.split("---", 2)
    meta = yaml.safe_load(fm) or {}
    bf = meta.get("big_five", {}) or {}
    tag = ""
    for ln in body.splitlines():
        if ln.startswith("# "):
            tag = ln[2:].strip()
            tag = tag.split("—", 1)[1].strip() if "—" in tag else tag
            break
    return {"id": meta.get("persona_id", pathlib.Path(path).stem),
            "name": meta.get("name", pathlib.Path(path).stem),
            "vector": {k: bf.get(k) for k in ("O", "C", "E", "A", "N")},
            "warmth": (meta.get("facets") or {}).get("warmth"),
            "tagline": tag,
            "system": body.strip()}


def archetype_catalog(personas_dir=PERSONAS_DIR):
    """The three canonical archetypes, keyed by role — for the composition UI."""
    return {r: _parse_persona_md(pathlib.Path(personas_dir) / f"{r}.md") for r in ARCH_ROLES}


def make_archetype_cell(counts, personas_dir=PERSONAS_DIR):
    """Build a cell from archetype counts, e.g. {'disruptor':1,'architect':1,'shield':1}
    for the balanced trio, or {'disruptor':4} for an all-Disruptor monoculture. Each
    copy keeps its archetype's native task; repeats are numbered (The Disruptor II)."""
    cat = archetype_catalog(personas_dir)
    cell, seen = [], {}
    for role in ARCH_ROLES:
        for _ in range(int(counts.get(role, 0))):
            base = cat[role]
            n = seen.get(role, 0)
            seen[role] = n + 1
            name = base["name"] + (_SUFFIX[n] if n < len(_SUFFIX) else f" {n + 1}")
            cell.append({"id": f"{role}_{n}", "name": name, "task": role,
                         "vector": base["vector"], "system": base["system"]})
    return cell


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--A", type=int, default=50)
    ap.add_argument("--size", type=int, default=3)
    a = ap.parse_args()
    for p in make_cell(a.A, a.size):
        print(f"{p['task']:10s} {p['name']:14s} {p['vector']}  ({len(p['system'])} chars)")
