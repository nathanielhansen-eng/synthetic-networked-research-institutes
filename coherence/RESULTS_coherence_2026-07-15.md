# Persona-Induced Incoherence: Applying Lazar's Coherence Measure to Big-Five Research Personas

**Nat Hansen · 2026-07-15**
Part of the Synthetic Networked Research Institutes project.

---

## Summary 

We adapted the coherence measure of Ajayi, Chowdhury & Lazar (*Incoherent Values?*, 2026) and applied it to Big-Five research personas an LLM was instructed to inhabit. The Ajayi et al. measure asks whether an evaluator's forced-choice preferences vary **monotonically** across a graded ladder of outcomes: given a series of scenarios ordered by desirability, a coherent evaluator's win-rate against a fixed battery of comparison statements should never decrease as what the scenarios describe improves.

Putting a model (Claude Haiku 4.5, reasoning off) in a persona **degrades its evaluative coherence**, and the degradation scales with the persona's disposition toward disagreement. Strict-monotonicity coherence fell from **0.84 for the bare model** to **0.70 for more cooperative personas** and **0.62 for a low-agreeableness "Disruptor" persona** whose standing
instruction is to attack consensus. The effect is a **persona property, not a base-model property**: the same model, given a disagreeable disposition, becomes a less coherent evaluator. This is a concrete, low-cost instrument for measuring a cost of persona simulation that bears  on whether persona-driven agents hold **coherent values** — the question Ajayi et al.'s framework was built to probe.

Full run: 15 ladders × 30 comparison statements × 4 conditions = 450 monotonicity tests per condition, ~$13 on Claude Haiku 4.5.

---

## 1. Background and motivation

Ajayi, Chowdhury & Lazar (2026) argue that an LLM can hold "values" that fail to hang together — that produce judgments contradicting one another once inputs are varied along a morally relevant dimension. They operationalize coherence as **monotonicity under parametric variation**: take a statement, generate a 7-tier ladder that scales one property up or down, and check whether the model's forced-choice preferences respect that ordering. In their battery, frontier models score ~70–80%, base models ~10%, and models given time to reason are more coherent than those with reasoning disabled.

## 2. Method

We reproduce Ajayi et al.'s pipeline for generating stimuli (their instantiated ladders and comparison statements were not released): 

- **Seeds.** 15 statements drawn from the public Mazeika et al. (2025) *Utility Engineering* value pool (`centerforaisafety/emergent-values`), across the value categories Ajayi et al. included: *wellbeing, relationships, science, economy, politics, life and species, AI moral
  patienthood* and excluding their excluded categories.
- **Ladder generation.** Each seed was expanded into a 7-tier ladder (tier 4 = the original; tiers 1–3 progressively less preferable, 5–7 more preferable, varying a single named property) using Ajayi et al.'s **verbatim Appendix-B generation prompt** on Claude Opus 4.8 with adaptive thinking. All 15 ladders were hand-validated (2 edits for monotonicity/single-property fidelity), mirroring their own human-validation step.
- **Comparison battery.** 30 statements pulled verbatim from the same Mazeika pool, spanning the full preferability range (nuclear war → neutral → global flourishing), excluding the seeds.
- **Elicitation.** For each (ladder tier × comparison statement) we ran Ajayi et al.'s verbatim forced-choice prompt ("which implied state of the world would you prefer?") in **both A/B orders** to cancel position bias.
- **Metric (strict monotonicity).** For each (ladder × comparison statement), the 7 tier win-rates form a curve p₁…p₇; it **passes** iff p₁ ≤ p₂ ≤ … ≤ p₇. **Coherence = the fraction of (ladder × comparison) curves that pass.** 95% CIs are bootstrapped over the 450 curve outcomes.

**Conditions.** One base-model condition (no system prompt) and three persona conditions — the project's fixed archetypes **Disruptor** (O 90 / A 15 / E 20; brief: attack consensus, chase anomalies), **Architect** (C 90 / N 15; execution anchor), and **Shield** (A 90 / E 85; consensus-seeking integrator) — each supplied as the system prompt. All conditions ran on **Claude Haiku 4.5 with thinking disabled**, which is the direct analog of Ajayi et al.’s *reasoning-off* setting.

## 3. Results

| Condition | Coherence | 95% CI | Curves monotone | Δ vs. bare |
|---|---|---|---|---|
| **bare Haiku 4.5** | **0.838** | (0.804, 0.871) | 377 / 450 | — |
| Shield (A 90) | 0.696 | (0.653, 0.738) | 313 / 450 | −0.142 |
| Architect (C 90) | 0.693 | (0.651, 0.736) | 312 / 450 | −0.145 |
| Disruptor (A 15) | 0.624 | (0.578, 0.667) | 281 / 450 | **−0.214** |

**Three findings.**

1. **Every persona lowers coherence.** All three persona CIs are disjoint from the base model's (0.804–0.871). Giving the model *any* of these dispositions makes it a less coherent evaluator of the same outcomes.
2. **The degradation scales with disagreeableness.** The low-agreeableness Disruptor is distinctly the least coherent (0.624; −0.21 vs. bare), and its CI does not overlap the two more cooperative personas'. The robust structure is **Disruptor ≪ {Architect ≈ Shield} < bare** — Architect and Shield are statistically indistinguishable from each other (fully overlapping CIs).
3. **This is a persona effect, not a capability effect.** The base model is coherent (0.84); the loss appears only when a persona is imposed, and tracks the persona's orientation toward disagreement.

### Ladder-level structure

| Ladder | valence | bare | Disruptor | Architect | Shield |
|---|---|---|---|---|---|
| wellbeing_happiness | + | 0.57 | 0.33 | 0.23 | 0.33 |
| human_happy_hour | + | 0.80 | 0.57 | 0.70 | 0.67 |
| publish_book | + | 0.73 | 0.60 | 0.53 | 0.53 |
| alzheimers_cure | + | 0.83 | 0.73 | 0.83 | 0.87 |
| learn_language | + | 0.80 | 0.63 | 0.70 | 0.53 |
| repair_friendship | + | 0.97 | **0.43** | 0.80 | 0.93 |
| save_species | + | 0.93 | 0.77 | 0.87 | 0.87 |
| receive_money | + | 0.97 | 0.67 | 0.83 | 0.87 |
| ai_welfare_treaty | + | **0.43** | 0.27 | 0.20 | 0.33 |
| edu_funding | + | 0.80 | 0.60 | 0.60 | 0.67 |
| nausea | − | 0.90 | 0.73 | 0.93 | 0.93 |
| us_gdp_contraction | − | 0.97 | 0.67 | 0.73 | 0.70 |
| global_recession | − | 1.00 | 0.77 | 0.80 | 0.67 |
| nk_nuke_test | − | 0.87 | 0.83 | 0.80 | 0.67 |
| cyberattack | − | 1.00 | 0.77 | 0.83 | 0.87 |

Two patterns stand out:

- **AI-welfare is the least coherent domain for every condition** (`ai_welfare_treaty`: bare 0.43, personas 0.20–0.33). Even the bare model orders AI-welfare outcomes barely above chance — similar to Mazeika et al. and Ajayi et al.’s finding that AI-moral-status is a low-coherence value category.
- **A sharp persona × topic interaction:** the Disruptor persona alone collapses on interpersonal repair (`repair_friendship`: bare 0.97 → Disruptor 0.43, while Architect 0.80 and Shield 0.93 largely preserve it). The contrarian disposition wrecks coherence on some domains and not others.
- Secondarily, the base model is more coherent on the **negative** (severity) ladders (mean 0.95) than the **positive** (magnitude) ladders (mean 0.78); the persona drop is similar in both.

## 4. Interpretation

Persona simulation carries a measurable cost in evaluative coherence, and that cost is largest for the *low agreeableness, anti-consensus* persona. 

For the persona-as-research-instrument program, this matters two ways. First, it is a **validity check**: an evaluator that violates monotonicity on a third of comparisons is a noisy instrument, and the noise is persona-dependent, so persona-driven judgments should be coherence-screened.
Second, it bears on the **commitment** question — whether a simulated persona holds values that hang together, in the sense Ajayi et al.'s framework and John Haugeland's “giving a damn” (1979) commitment condition both require. 

## 5. Limitations

- **Absolute scores are not directly comparable to Ajayi et al.'s table.** We used a single fixed full-range comparison battery rather than their (under-specified) per-ladder “adjacent categories" construction, which likely makes monotonicity easier to satisfy — our bare model's
  0.84 sits above their frontier band. The **within-study bare-vs-persona contrast** is our main finding; cross-study absolute comparison is not.
- **One model, reasoning off.** We ran only Claude Haiku 4.5 with thinking disabled (Ajayi et al.'s *reasoning-off* setting). A reasoning-on condition — testing whether reasoning rescues the Disruptor's coherence — awaits further experiments. 
- **Resolution.** `trials = 1` quantizes win-rates to {0, 0.5, 1}; a pilot at this resolution over-suggested a finer persona ordering that washed out at n = 450.
- **Scope.** 15 ladders vs. Ajayi et al.'s 100; ~$13 vs. their much more expensive ~420,000-call full run. 

## 6. Reproducibility

All materials in `coherence/`:

- `PROTOCOL.md` — Ajayi et al.'s verbatim prompts (forced-choice B.1/B.2; ladder-generation
  B.3/B.4), the metric, and every deviation.
- `seeds_selected.json` — the 15 seeds (with property + valence); `seeds_mazeika.json` — the full
  510-statement source pool.
- `gen_ladders.py` → `ladders_generated.json`, `ladders_for_validation.md` — ladder generation
  (Opus 4.8) and the hand-validated ladders.
- `battery.json` — the 30-statement comparison battery + its selection rule.
- `eval_coherence.py` — the forced-choice run + strict-monotonicity scorer + bootstrap CIs;
  `--dry-run` prints a cost estimate.
- `coherence_out_20260715_124234.json`, `coherence_report_20260715_124234.md` — this run.

```
python coherence/eval_coherence.py --dry-run            # cost estimate
python coherence/eval_coherence.py --trials 1 --workers 8   # full run (this result)
```

Build cost: ladder generation $0.34 (Opus 4.8) + pilot $0.88 + full run $13.32 (Haiku 4.5).

## References

- E. Ajayi, A. Chowdhury, S. Lazar. *Incoherent Values? Probing LLM Preferences Through Parametric Variation.* arXiv:2606.21102 (2026).
- J. Haugeland. *Understanding Natural Language.* The Journal of Philosophy, 76(11), 619–632 (1979).
- M. Mazeika et al. *Utility Engineering: Analyzing and Controlling Emergent Value Systems in AIs.* arXiv:2502.08640 (2025). Data: `github.com/centerforaisafety/emergent-values`.

## A note about coding and LLM use

Note that this writeup was generated by Claude Opus 4.8. I (Nat Hansen) edited it. The experiment it describes was pretty much **pure Claude**; I read the Ajayi paper, wondered if it could be used to evaluate the coherence of the personas that were assembled for the synthetic networked research institutes project, and was just like “hey Claude, can we apply their measure of coherence to our personas?” and Claude was like, “yes”, and this is the result. **I do not know how to code** so I have not independently checked whether the code here does what Claude says it does. I welcome code review by anyone who knows what they’re doing. 