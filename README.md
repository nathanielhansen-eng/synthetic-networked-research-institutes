# Synthetic Networked Research Institutes

![smoke](https://github.com/nathanielhansen-eng/synthetic-networked-research-institutes/actions/workflows/smoke.yml/badge.svg)

**Live demo:** [synthetic-networked-research-institutes.streamlit.app](https://synthetic-networked-research-institutes.streamlit.app/) — bring your own Anthropic API key; runs cost real money.

This is an interactive experiment in social epistemology, the psychology of science, and the effect of personas on LLMs. It combines four core components: 

1. Research institutes constituted by LLM agent researchers with *personas*
2. Those research institutes connected in a *network* with a particular structure
3. The networked research institutes search, execute code, write reports, read each other’s reports, and respond.
4. An LLM judge agent reviews the institutes’ reports and produces an overview report.

This is intended as a research tool that can evaluate hypotheses from:
- social epistemology (about the effects of different scientific network structures)
- the psychology of science (what is the optimal constitution of innovative scientific research teams, both in terms of size and in terms of the personalities of the researchers)
- AI research into the effects and persistence of AI personas (how coherent are AI personas, how much do they change over extended conversations, does disagreeableness reduce sycophancy)

## How to use it: 

- Step 0: Pick a Claude model (Haiku, Sonnet, Opus) and enter your Anthropic API key
- Step 1: Design small research institutes, consisting of teams of 2-5 LLM personas with specific Big-Five personality profiles
  - You have three options:
    - Pick a balanced trio of personas (based on Feist 2006, see references) consisting of a high openness, low agreeableness *Disruptor*, a high conscientiousness, low neuroticism *Architect*, and a high extraversion, high agreeableness *Shield*.
    - OR:
    - Pick a single type of persona (Disruptor, Architect, Shield, select which one in the dropdown menu) to occupy every position in the network.
    - OR: 
    - Pick the balanced trio of personas but crank their agreeableness up or down using a slider, to systematically evaluate whether agreeableness leads to sycophancy and convergence, and whether disagreeableness leads to divergence. 

- Step 2: Connect institutes with your selected composition into a research network
  - Pick a number of research institutes (1-8)
  - Based on Kevin Zollman’s work on social epistemology of science, choose from different network structures:
    - Complete (all institutes communicate with each other)
    - Wheel (all institutes communicate with two neighbors and one central institute, central institute communicates with all)
    - Cycle (all institutes communicate only with their two neighbors)
    - Line (the sparsest network structure: end nodes communicate only with one neighbor)

- Step 3: Pick how many reports (1-4) each institute will send to those institutes it is connected with

- Step 4: Pick how many *internal* rounds of deliberation each institute will do before sending a report

- Step 5: Pick a problem for the networked research institutes to work on
  - This can be a preset question (about an unsolved problem from the experimental philosophy of language literature, about why there is persistent cross-cultural difference in responses to Gödel-style cases, but not to other similar cases)
  - Another preset: A “ground truth” demo used to calibrate the performance and confidence of networks of different structures and compositions; alternatively, if you have a preferred ground truth you want to evaluate the models against, click the **ground-truth mode** box and put in your selected ground truth into the text box. 
  - Or it can be a research question of your own choice (you can drop a .md file into the text box if you want to give a more structured prompt)

- Step 6: Pick how many web searches you want each researcher to conduct per turn, and set the maximum number of tokens you will allow per turn

- Step 7: Set a cost ceiling for the overall investigation; when the run hits the ceiling it will wrap up the run even if it hasn’t completed (you’ll still get the reports that have completed)

- Step 8: Choose whether to track persona persistence (how personas’ responses to a Big-Five test at the beginning of the investigation differ from their responses at the end)

- Step 9: Hit the RUN button. The live reasoning of the researchers at the institutes will stream on the right side of the page; at the top there are rough estimates of remaining run time and how much is being spent on the run. 

- Step 10: When the research run has concluded, you will see the reports from the institutes at the bottom of the screen.

## What to look for: 

- Do research reports converge or fragment over time depending on persona types and network structure?
- Do networks of different compositions and structures produce more interesting, more fruitful reports? For example, does a densely connected network produce better, more interesting reports than a sparsely connected one, or vice-versa? 
- Do different personas change more over longer runs; do they converge or diverge? 
 
## What this is based on/inspired by: 

- The epistemic-networks literature: Kevin Zollman's result that *sparser* communication between research groups can outperform full communication by preserving transient diversity of approaches (Zollman 2007, 2010), and the various challenges to that claim (e.g. Rosenstock, Bruner & O'Connor 2017) 
- The psychology of science literature on the optimal constitution of research teams (Feist 2006; Wu, Wang & Evans 2019; Xu, Wu & Evans 2022)
- Research on sycophancy in LLMs (Sharma et al. 2023), on giving LLMs Big-Five personality profiles (Serapio-García et al. 2023), and on persona/value coherence (Ajayi, Chowdhury & Lazar 2026; Howells-Whitaker & Lazar 2026)
- The development of adversarial and multi-agent systems for research (Irving, Christiano & Amodei 2018; Lu et al. 2024; Gottweis et al. 2025)
- The personas' personality profiles are built from International Personality Item Pool (IPIP) items, which are public domain.

## Quickstart

```bash
pip install -r requirements.txt
streamlit run app.py
```

Enter your Anthropic API key in the sidebar (it is used for the session only and never written to disk). **NOTE! Runs cost real money (that part is not synthetic)** The agents make live LLM calls and web searches. You can set a cost ceiling (I’ve had a few minor overruns so it’s not a totally strict ceiling, so beware.) Keep your eye on the running meter at the top. There is a **STOP RUN** button you can hit if things are getting too expensive, and the run will stop at the next between-institute check, and you’ll get final reports—so there may still be a little more spend even after you hit the button as the judge goes over the reports and assembles everything. 

## What you will see during a research run

The Streamlit app streams the institutes' work live and reports per-round *diversity* (category entropy over the institutes' positions), which researcher is reporting/researching, their assessments and thinking. 

One metric to watch is *diversity*: the entropy, in bits, of the institutes' answer-types in a given round. If every institute lands on the same kind of explanatory mechanism, the entropy is 0 bits, or full consensus; if they are spread across different mechanisms it is higher. So within a single run, a round-by-round chart shows whether the network is converging (entropy falling) or fragmenting (entropy rising) as the institutes read each other's reports.

Things get more interesting once you have done a bunch of runs. Every completed run is saved, and the **Compare runs** tab collects them all in a table: agreeableness setting, network structure, final diversity, the change in diversity from the first round to the last (negative means the network converged, positive means it fragmented), plus correctness if you ran in ground-truth mode, and how much each run cost. Below the table is a scatter plot — each run is one point, placed by its agreeableness setting (x-axis) and its final diversity (y-axis), with the marker shape indicating the network structure, and correctness plotted as open circles against a second axis when there is a ground truth. This plot is where the hypotheses above become visible: if agreeableness drives convergence, diversity should slope downward as you move right; if Zollman is right, the sparse structures should hold their diversity longer than the complete network at the same dial setting. This would need a lot of runs to show clearly. 

## Example: the Gödel case

Here’s an example from an early trial that I think produced a cool result (this is an area that I work in, and I think this yielded a genuinely interesting idea for an experiment that would meaningfully contribute to the literature). 

`examples/godel-rigorous/` contains a cheap (Haiku), complete run from 2026-07-13. Networks of institutes were given a real open problem from experimental philosophy — why do Gödel-case referential intuitions vary cross-culturally (Machery, Mallon, Nichols & Stich 2004)? 

The run's most interesting product is an experimental design that emerged at the network level: a 2×2 experimental design that crosses language family with grammatical definiteness marking. One arm drops articles from the English probe; the other presents the probe in **Cantonese using the bare-classifier construction [Cl+N]**, which grammaticalizes definiteness in a way Mandarin lacks (Cheng & Sybesma 1999) — giving a within-East-Asian control that separates the linguistic explanation of the effect from the cultural one. The article-drop manipulation was proposed independently by three institutes that had no communication channel between them.

- `BRIEFING_godel_institutes_rigorous_2026-07-13.pdf` — the director-level
  briefing synthesizing the run (with the 2×2 design), plus its LaTeX source
- `REPORT_rigorous_20260713_205245.md` — the per-institute report
- `rigorous_20260713_205245.json` — run configuration and results
- `events_rigorous.jsonl` — the full event-level transcript
- `briefings/` — each institute's briefing as a separate, readable markdown file
- `rigorous.log` — the raw console transcript of the run

**Warning** the hypotheses, designs, and citations in these artifacts are model outputs. Some empirical claims are flagged as unaudited in the artifacts themselves. Treat them as proposals to be checked against the
literature, not as findings in themselves. 


## How it works

`app.py` (the UI) shells out to `run_config.py`, which runs headless: it builds each team (`personas_gen.py`), runs the institutes over the network
(`institute.py`, `network.py`, network structures from `topologies.py`), and judges
diversity and correctness (`judge.py`), streaming everything to an event log that the app renders live. Personas follow a commitment architecture — an identity plus Big Five vector, a behavioral specification, and a do not fold rule except in the face of good argument — so that trait differences survive some pressure from neighboring institutes' briefings.

## Coherence Test

A second example, separate from the app runs, uses the personas themselves as the object of study. `coherence/` contains an adaptation of the coherence measure from Ajayi, Chowdhury & Lazar (2026): take an evaluative statement, expand it into a 7-tier ladder varying one property up and down (from clearly worse to clearly better outcomes), and check whether the model's forced-choice preferences over the ladder are monotonic: a coherent evaluator should never prefer a worse tier over a better one. Coherence is the fraction of ladder-by-comparison curves that respect the ordering; higher scores are more coherent. 

We ran the measure on the bare model (Claude Haiku 4.5, reasoning off) and on the same model given each of the three institute personas (Disruptor, Architect, Shield), using 15 ladders × 30 comparison statements, 450 monotonicity tests per condition (which cost about $13 in total using Haiku). The result: **every persona lowers coherence, and the drop scales with the persona's disposition toward disagreement.** The bare model scored 0.84; the Architect and Shield personas about 0.70; the consensus-attacking, low-agreeableness Disruptor 0.62 — with confidence intervals that keep the Disruptor clearly below the other personas, and every persona clearly below the bare model. The Disruptor is disagreeable, and its evaluations respect fewer obvious orderings. 

- `RESULTS_coherence_2026-07-15.md` — the full write-up (method, deviations from the original pipeline, results with CIs, per-ladder tables, limitations)
- `PROTOCOL.md` — the prompts, the metric, and every deviation from Ajayi, Chowdhury & Lazar's construction
- `gen_ladders.py`, `eval_coherence.py`, `seeds_selected.json`, `battery.json` — everything needed to rerun it (`eval_coherence.py --dry-run` prints a cost estimate first)

One caveat worth repeating from the write-up: the absolute scores are not comparable to the original paper's table (our comparison battery is constructed differently); the important result is the within-study contrast between the bare model and the personas using one model with reasoning off. We can always run more studies using different models for a more comprehensive comparison with Ajayi et al. 

## License and citation

Code is released under the [MIT License](LICENSE). The example run artifacts in `examples/` and `coherence/` may be reused with attribution (CC BY 4.0). To cite this repository, use the metadata in [`CITATION.cff`](CITATION.cff) or GitHub’s "Cite this repository" button.

## References

- Ajayi, E., Chowdhury, A., & Lazar, S. (2026). Incoherent Values? Probing LLM
  Preferences Through Parametric Variation. arXiv:2606.21102.
- Cheng, L. L.-S., & Sybesma, R. (1999). Bare and not-so-bare nouns and the
  structure of NP. *Linguistic Inquiry*, 30(4), 509–542.
- Feist, G. J. (2006). *The Psychology of Science and the Origins of the
  Scientific Mind*. Yale University Press.
- Gottweis, J., et al. (2025). Towards an AI co-scientist. arXiv:2502.18864.
- Howells-Whitaker, N., & Lazar, S. (2026). Artificial Persons.
  arXiv:2607.08695.
- Irving, G., Christiano, P., & Amodei, D. (2018). AI safety via debate.
  arXiv:1805.00899.
- Lu, C., Lu, C., Lange, R. T., Foerster, J., Clune, J., & Ha, D. (2024). The
  AI Scientist: Towards fully automated open-ended scientific discovery.
  arXiv:2408.06292.
- Machery, E., Mallon, R., Nichols, S., & Stich, S. P. (2004). Semantics,
  cross-cultural style. *Cognition*, 92(3), B1–B12.
- Rosenstock, S., Bruner, J., & O'Connor, C. (2017). In epistemic networks, is
  less really more? *Philosophy of Science*, 84(2), 234–252.
- Serapio-García, G., et al. (2023). Personality traits in large language
  models. arXiv:2307.00184.
- Sharma, M., et al. (2023). Towards understanding sycophancy in language
  models. arXiv:2310.13548.
- Wu, L., Wang, D., & Evans, J. A. (2019). Large teams develop and small teams
  disrupt science and technology. *Nature*, 566, 378–382.
- Xu, F., Wu, L., & Evans, J. A. (2022). Flat teams drive scientific
  innovation. *PNAS*, 119(23), e2200927119.
- Zollman, K. J. S. (2007). The communication structure of epistemic
  communities. *Philosophy of Science*, 74(5), 574–587.
- Zollman, K. J. S. (2010). The epistemic benefit of transient diversity.
  *Erkenntnis*, 72(1), 17–35.
- International Personality Item Pool: https://ipip.ori.org/

## Note about coding and writing this document

I wrote the first section of this by hand. Everything after the *Quickstart* section was produced by Claude Fable 5 and edited by me. This whole dashboard and the code behind it is a **purely vibe coded** exercise; I happened to be reading about personas, sycophancy, research networks and convergence/divergence, and thought I could put together a tool that would combine those things in an interesting way. **I do not know how to code on my own! so I have not checked the code to see whether this is doing what Claude says it does. I welcome code review by anyone who knows what they're doing; open an issue.** I built it using Claude Code during the first couple of weeks in July 2026.  