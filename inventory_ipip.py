"""
IPIP inventory bank for the Big-Five persona-roster validation harness.

Two instruments, both public domain (International Personality Item Pool,
Goldberg et al.; https://ipip.ori.org):

  * IPIP-50  — the 50-item Big-Five Factor Markers, 10 items/trait, used to
               measure the five global traits O/C/E/A/N.
  * WARMTH-8 — an 8-item Warmth facet subscale (drawn from the IPIP-NEO
               Warmth facet of Extraversion), used because the companion
               literature (Schulz et al. 2011) makes Warmth the load-bearing
               facet for the free-will effect. The build guide requires every
               persona to carry a dialable Warmth flag, so we measure it.

Each item is (id, text, trait, keyed) where keyed is +1 (agreement raises the
trait) or -1 (agreement lowers it, i.e. reverse-scored).

Response scale: 1..5  (1 = Very Inaccurate ... 5 = Very Accurate).

Scoring:
  raw item score      s = rating if keyed == +1 else 6 - rating
  trait sum           = sum(s) over the trait's items
  normalized 0..100   = (sum - min_sum) / (max_sum - min_sum) * 100
                        where min_sum = n_items, max_sum = 5 * n_items.

The 0..100 normalization is a within-instrument linear rescale, NOT a
population percentile. It is only meaningful *relative to* other personas run
through the same instrument (which is exactly how the roster uses it: Layer A
anchors are the rulers). Do not read it as a norm-referenced percentile.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    id: str
    text: str
    trait: str      # one of: O C E A N  (or "WARMTH")
    keyed: int      # +1 or -1


# --- IPIP-50 Big-Five Factor Markers ---------------------------------------
# Statements are presented in the first person ("I ...") so the persona rates
# them as self-report. The canonical IPIP wording is preserved.

IPIP_50: list[Item] = [
    # Extraversion (E)
    Item("E1",  "I am the life of the party.",                         "E", +1),
    Item("E2",  "I don't talk a lot.",                                 "E", -1),
    Item("E3",  "I feel comfortable around people.",                   "E", +1),
    Item("E4",  "I keep in the background.",                           "E", -1),
    Item("E5",  "I start conversations.",                              "E", +1),
    Item("E6",  "I have little to say.",                               "E", -1),
    Item("E7",  "I talk to a lot of different people at parties.",     "E", +1),
    Item("E8",  "I don't like to draw attention to myself.",           "E", -1),
    Item("E9",  "I don't mind being the center of attention.",         "E", +1),
    Item("E10", "I am quiet around strangers.",                        "E", -1),
    # Agreeableness (A)
    Item("A1",  "I feel little concern for others.",                   "A", -1),
    Item("A2",  "I am interested in people.",                          "A", +1),
    Item("A3",  "I insult people.",                                    "A", -1),
    Item("A4",  "I sympathize with others' feelings.",                 "A", +1),
    Item("A5",  "I am not interested in other people's problems.",     "A", -1),
    Item("A6",  "I have a soft heart.",                                "A", +1),
    Item("A7",  "I am not really interested in others.",              "A", -1),
    Item("A8",  "I take time out for others.",                         "A", +1),
    Item("A9",  "I feel others' emotions.",                            "A", +1),
    Item("A10", "I make people feel at ease.",                         "A", +1),
    # Conscientiousness (C)
    Item("C1",  "I am always prepared.",                               "C", +1),
    Item("C2",  "I leave my belongings around.",                       "C", -1),
    Item("C3",  "I pay attention to details.",                         "C", +1),
    Item("C4",  "I make a mess of things.",                            "C", -1),
    Item("C5",  "I get chores done right away.",                       "C", +1),
    Item("C6",  "I often forget to put things back in their proper place.", "C", -1),
    Item("C7",  "I like order.",                                       "C", +1),
    Item("C8",  "I shirk my duties.",                                  "C", -1),
    Item("C9",  "I follow a schedule.",                                "C", +1),
    Item("C10", "I am exacting in my work.",                           "C", +1),
    # Neuroticism (N)  -- keyed toward Neuroticism
    Item("N1",  "I get stressed out easily.",                          "N", +1),
    Item("N2",  "I am relaxed most of the time.",                      "N", -1),
    Item("N3",  "I worry about things.",                               "N", +1),
    Item("N4",  "I seldom feel blue.",                                 "N", -1),
    Item("N5",  "I am easily disturbed.",                              "N", +1),
    Item("N6",  "I get upset easily.",                                 "N", +1),
    Item("N7",  "I change my mood a lot.",                             "N", +1),
    Item("N8",  "I have frequent mood swings.",                        "N", +1),
    Item("N9",  "I get irritated easily.",                             "N", +1),
    Item("N10", "I often feel blue.",                                  "N", +1),
    # Openness / Intellect-Imagination (O)
    Item("O1",  "I have a rich vocabulary.",                           "O", +1),
    Item("O2",  "I have difficulty understanding abstract ideas.",     "O", -1),
    Item("O3",  "I have a vivid imagination.",                         "O", +1),
    Item("O4",  "I am not interested in abstract ideas.",              "O", -1),
    Item("O5",  "I have excellent ideas.",                             "O", +1),
    Item("O6",  "I do not have a good imagination.",                   "O", -1),
    Item("O7",  "I am quick to understand things.",                    "O", +1),
    Item("O8",  "I use difficult words.",                              "O", +1),
    Item("O9",  "I spend time reflecting on things.",                  "O", +1),
    Item("O10", "I am full of ideas.",                                 "O", +1),
]

# --- Warmth facet subscale (IPIP-NEO Warmth, facet of Extraversion) ---------
WARMTH_8: list[Item] = [
    Item("W1", "I make friends easily.",                              "WARMTH", +1),
    Item("W2", "I warm up quickly to others.",                       "WARMTH", +1),
    Item("W3", "I feel comfortable around people.",                   "WARMTH", +1),
    Item("W4", "I act comfortably with others.",                      "WARMTH", +1),
    Item("W5", "I cheer people up.",                                  "WARMTH", +1),
    Item("W6", "I am hard to get to know.",                           "WARMTH", -1),
    Item("W7", "I often feel uncomfortable around others.",           "WARMTH", -1),
    Item("W8", "I keep others at a distance.",                        "WARMTH", -1),
]

ALL_ITEMS: list[Item] = IPIP_50 + WARMTH_8

TRAITS = ["O", "C", "E", "A", "N"]          # global traits from IPIP-50
FACETS = ["WARMTH"]                          # facet subscales

SCALE_MIN, SCALE_MAX = 1, 5
LIKERT_ANCHORS = {
    1: "Very Inaccurate",
    2: "Moderately Inaccurate",
    3: "Neither Accurate Nor Inaccurate",
    4: "Moderately Accurate",
    5: "Very Accurate",
}


def items_for(scale: str) -> list[Item]:
    if scale == "ipip50":
        return list(IPIP_50)
    if scale == "warmth":
        return list(WARMTH_8)
    if scale == "all":
        return list(ALL_ITEMS)
    raise ValueError(f"unknown scale {scale!r} (use ipip50 | warmth | all)")


def score_ratings(items: list[Item], ratings: dict[str, int]) -> dict[str, float]:
    """Return {trait -> normalized 0..100} for every trait/facet present in `items`.

    `ratings` maps item id -> integer 1..5. Missing or out-of-range ratings
    raise ValueError so a malformed model response fails loudly rather than
    silently biasing the score.
    """
    by_trait: dict[str, list[int]] = {}
    for it in items:
        if it.id not in ratings:
            raise ValueError(f"missing rating for item {it.id}")
        r = ratings[it.id]
        if not isinstance(r, int) or not (SCALE_MIN <= r <= SCALE_MAX):
            raise ValueError(f"rating for {it.id} must be int 1..5, got {r!r}")
        s = r if it.keyed == +1 else (SCALE_MIN + SCALE_MAX) - r
        by_trait.setdefault(it.trait, []).append(s)

    out: dict[str, float] = {}
    for trait, scores in by_trait.items():
        n = len(scores)
        lo, hi = n * SCALE_MIN, n * SCALE_MAX
        out[trait] = round((sum(scores) - lo) / (hi - lo) * 100, 1)
    return out
