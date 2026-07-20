"""
Python port of Zollman's bandit-network model of scientific communities.

Sources: Zollman, "The Epistemic Benefit of Transient Diversity" (2010) and
"The Communication Structure of Epistemic Communities" (2007); cross-checked
against his 2008 Java code (models/BgModel.java,
learningRules/BgLearning.java): myopic best response to
current expectations, evidence shared with network neighbors each round,
belief update on own + neighbors' results.

The model:
  - Two methodologies ("slot machines"). The old one (A) pays off at a known
    rate p_A = 0.5. The new one (B) pays at unknown rate p_B = 0.5 + epsilon.
  - Each agent holds a beta distribution <alpha, beta> over B's rate.
  - Each round, every agent works on whichever methodology currently has the
    higher expected payoff (myopic: E[B] = alpha/(alpha+beta) vs 0.5),
    performs `trials` Bernoulli trials, and observes the results of every
    network neighbor as well as its own.
  - "Extreme beliefs" (Zollman's stubbornness manipulation) = scaling the
    initial alpha+beta mass while keeping the mean fixed: a stubborn agent
    needs more contrary evidence to cross the 0.5 line.

Absorbing failure: once nobody works on B, no more evidence about B is ever
generated, so the community has permanently abandoned the (better) new theory.
Success: at the horizon, everyone is working on B.

Beyond Zollman's baseline, this version adds (all off by default):

  - Per-agent decision rules (`rule` may be a list): "myopic" (Zollman),
    "margin" (commitment hysteresis delta: abandon your current theory only
    when E < 0.5 - delta), "confidence" (abandon only when P(my theory is
    worse) exceeds a threshold; normal approx to the beta posterior). Rules
    match dashboard.html. Mixed populations = mixed lists.
  - Per-agent prior_strength (scalar or array).
  - The sycophantic-LLM echo node: each round each agent consults the LLM
    with probability consult_rate; the LLM parrots a view v back and the
    agent updates on it as if it were evidence -- echo_strength pseudo-
    observations split alpha += c*v, beta += c*(1-v) (mean-preserving
    confidence inflation). v = (1-lambda)*own view + lambda*population mean:
    lambda = 0 is the private mirror (satellite model, endogenous prior
    inflation), lambda > 0 is the shared foundation model (covert
    densification). echo_polarizing=True instead dumps all c on the favored
    side (the "you're absolutely right, and more so" variant).

  - The LLM as a belief-carrying node (llm_belief=True): instead of parroting
    the (stateless) population mean, the shared component of the echoed view
    is the LLM's *own* persistent belief v_L, an EMA that starts at llm_prior
    and moves toward what the LLM ingests each round. This decouples the two
    strengths the single mass dial conflates: conviction (how hard the LLM
    pushes scientists) is echo_strength c; plasticity (how hard the LLM itself
    is to move) is llm_plasticity eta -- an exponential learning rate whose
    half-life in rounds is ln(2) / -ln(1-eta). eta=0 is the frozen oracle
    (immovable snapshot at llm_prior); eta=1 tracks the latest signal fully
    (recovers the stateless echo). llm_intake picks what moves it: "opinions"
    (the sycophantic loop -- it trains on the community's mean view) or
    "evidence" (a fair but slow aggregator -- it reads the round's B trial
    outcomes, and updates only when someone is on B). llm_shared=True is one
    hub node consulted by all; False gives each agent a private lagged mirror.
    The starvation regime lives here: a strong-but-slow wrong prior drags the
    weak-prior scientists off B before it concedes, and once nobody is on B the
    evidence stops, so a movable oracle never gets the data that would move it.

All runs for a condition are vectorized across numpy axis 0.
"""

import numpy as np


RULES = ("myopic", "margin", "confidence")


def phi(z):
    """Standard normal CDF, Abramowitz-Stegun 26.2.17 (same as dashboard.html)."""
    z = np.asarray(z, dtype=float)
    t = 1.0 / (1.0 + 0.2316419 * np.abs(z))
    d = 0.3989423 * np.exp(-z * z / 2.0)
    p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
    return np.where(z > 0, 1.0 - p, p)


# ---------------------------------------------------------------- networks

def cycle(n):
    a = np.zeros((n, n), dtype=float)
    for i in range(n):
        a[i, (i - 1) % n] = a[i, (i + 1) % n] = 1
    return a


def wheel(n):
    """Agent 0 is the hub; agents 1..n-1 form a cycle, each also tied to 0."""
    a = cycle_of_rim(n)
    a[0, 1:] = a[1:, 0] = 1
    return a


def cycle_of_rim(n):
    a = np.zeros((n, n), dtype=float)
    rim = list(range(1, n))
    for idx, i in enumerate(rim):
        a[i, rim[(idx - 1) % len(rim)]] = 1
        a[i, rim[(idx + 1) % len(rim)]] = 1
    return a


def complete(n):
    a = np.ones((n, n), dtype=float)
    np.fill_diagonal(a, 0)
    return a


def line(n):
    a = np.zeros((n, n), dtype=float)
    for i in range(n - 1):
        a[i, i + 1] = a[i + 1, i] = 1
    return a


NETWORKS = {"cycle": cycle, "wheel": wheel, "complete": complete, "line": line}


# ---------------------------------------------------------------- the model

def simulate(
    network="cycle",
    n_agents=10,
    epsilon=0.001,
    trials=1000,
    prior_strength=1.0,
    max_steps=3000,
    n_runs=500,
    seed=0,
    track_every=None,
    decide=None,
    rule="myopic",
    delta=0.05,
    conf=0.99,
    consult_rate=0.0,
    echo_strength=0.0,
    echo_lambda=0.0,
    echo_polarizing=False,
    echo_contrarian=False,
    llm_belief=False,
    llm_prior=0.5,
    llm_plasticity=0.1,
    llm_intake="opinions",
    llm_shared=True,
):
    """Run the model. Returns a dict of results.

    prior_strength: multiplies the initial <alpha, beta> mass, mean fixed.
        1.0 reproduces Zollman's baseline (alpha, beta ~ U(0, 4]);
        larger = more "stubborn"/extreme initial beliefs.
        Scalar or per-agent array of length n_agents.
    rule: decision rule, a string or a per-agent list of length n_agents.
        "myopic": work on whichever arm looks better right now (Zollman).
        "margin": abandon the current theory only when E < 0.5 - delta
            (commitment hysteresis; adoption is still myopic).
        "confidence": abandon the current theory only when P(it is worse)
            > conf (settledness; normal approx to the beta posterior).
    consult_rate: per-round probability each agent consults the LLM
        (scalar or per-agent array). With echo_strength = 0 it does nothing.
    echo_strength: pseudo-observations per consultation. The echoed view is
        v = (1 - echo_lambda) * own E + echo_lambda * population mean E;
        update alpha += c*v, beta_ += c*(1-v) (mean-preserving), or all c on
        the favored side if echo_polarizing.
    echo_lambda: 0 = private mirror (satellite LLMs), 1 = pure consensus
        parrot; in between = a shared model tugged by the literature. With
        llm_belief=True the shared component is the LLM's own belief v_L
        rather than the population mean, so lambda is how much each agent
        defers to the model vs its own view.
    llm_belief: give the LLM its own persistent belief v_L (an EMA) instead
        of the stateless population-mean echo. Off by default (old behavior).
    llm_prior: v_L's starting mean. < 0.5 backs the old theory (a headwind),
        > 0.5 backs the new one (a tailwind).
    llm_plasticity: eta, the EMA learning rate on the LLM's belief; half-life
        in rounds = ln(2) / -ln(1-eta). 0 = frozen at llm_prior (immovable),
        1 = fully tracks the current signal (stateless echo). This is the
        "movable but stubborn" dial, independent of echo_strength.
    llm_intake: what moves v_L -- "opinions" (EMA toward the community's mean
        view; the sycophantic loop) or "evidence" (EMA toward the empirical B
        success rate that round, and only on rounds someone is on B; a fair
        but slow aggregator that can be starved of data).
    llm_shared: True = one hub belief consulted by all; False = a private
        lagged mirror per agent (tracks its own owner under llm_intake).
    track_every: if set, record the fraction of agents working on B every
        `track_every` steps (for trajectory plots).
    decide: optional callback replacing the rule machinery entirely. Called
        as decide(expectation, alpha, beta_) -> bool array "work on B".
        This is the hook where an LLM-persona decision rule plugs in.
    """
    rng = np.random.default_rng(seed)
    adj = NETWORKS[network](n_agents)
    share = adj + np.eye(n_agents)          # everyone sees self + neighbors
    p_b = 0.5 + epsilon
    prior_strength = np.broadcast_to(np.asarray(prior_strength, dtype=float),
                                     (n_agents,))
    consult_rate = np.broadcast_to(np.asarray(consult_rate, dtype=float),
                                   (n_agents,))

    if isinstance(rule, str):
        rule = [rule] * n_agents
    if len(rule) != n_agents or any(r not in RULES for r in rule):
        raise ValueError(f"rule must be one of {RULES} or a list of them, "
                         f"length {n_agents}; got {rule!r}")
    rule = np.array(rule)
    is_margin = rule == "margin"
    is_confidence = rule == "confidence"
    sticky = is_margin | is_confidence      # rules that consult current choice

    # Zollman baseline priors: alpha, beta ~ U(0, 4]
    alpha = rng.uniform(0, 4, size=(n_runs, n_agents)) * prior_strength
    beta_ = rng.uniform(0, 4, size=(n_runs, n_agents)) * prior_strength

    on_b = alpha / (alpha + beta_) > 0.5    # initial choice: myopic
    alive = np.ones(n_runs, dtype=bool)     # runs not yet absorbed at all-A
    steps_to_fail = np.full(n_runs, -1)
    trajectory = []
    use_echo = echo_strength > 0 and consult_rate.any()

    if llm_intake not in ("opinions", "evidence"):
        raise ValueError(f"llm_intake must be 'opinions' or 'evidence'; "
                         f"got {llm_intake!r}")
    # the LLM's own belief v_L (an EMA): one shared hub, or one mirror/agent.
    n_llm = 1 if llm_shared else n_agents
    v_l = np.full((n_runs, n_llm), float(llm_prior))
    # evidence-intake signal carried over from the previous round's trials
    ev_signal = np.zeros((n_runs, n_llm))
    ev_gate = np.zeros((n_runs, n_llm))     # 1 where B was tried (so v_L moves)

    for t in range(max_steps):
        # -- the LLM echo: confidence inflation before this round's decision
        if use_echo:
            consulted = (rng.random(size=(n_runs, n_agents)) < consult_rate) \
                        & alive[:, None]
            e = alpha / (alpha + beta_)
            if llm_belief:
                # move the LLM's own belief toward what it ingests (EMA);
                # eta=0 => frozen at llm_prior, eta=1 => tracks the signal.
                if llm_plasticity > 0:
                    if llm_intake == "opinions":
                        sig = e.mean(axis=1, keepdims=True) if llm_shared else e
                        gate = llm_plasticity
                    else:                    # evidence: last round's B rate
                        sig = ev_signal
                        gate = llm_plasticity * ev_gate
                    v_l += gate * (sig - v_l)
                shared_view = v_l            # broadcasts (shared) or per-agent
            else:
                shared_view = e.mean(axis=1, keepdims=True)
            v = (1 - echo_lambda) * e + echo_lambda * shared_view
            if echo_contrarian:         # the challenger: argue the other side
                v = 1.0 - v
            if echo_polarizing:
                v = (v > 0.5).astype(float)
            alpha += np.where(consulted, echo_strength * v, 0.0)
            beta_ += np.where(consulted, echo_strength * (1 - v), 0.0)

        expectation = alpha / (alpha + beta_)
        if decide is not None:
            on_b = decide(expectation, alpha, beta_)
        else:
            stay = expectation > 0.5        # myopic default, both directions
            if is_margin.any():
                margin_stay = expectation > 0.5 - delta
                stay = np.where(is_margin & on_b, margin_stay, stay)
            if is_confidence.any():
                tot = alpha + beta_
                sd = np.sqrt(np.maximum(expectation * (1 - expectation), 1e-12)
                             / (tot + 1))
                conf_stay = phi((0.5 - expectation) / sd) <= conf
                stay = np.where(is_confidence & on_b, conf_stay, stay)
            on_b = stay
        on_b &= alive[:, None]              # frozen runs generate nothing

        if track_every and t % track_every == 0:
            trajectory.append(on_b.mean(axis=1).copy())

        # absorbing failure: no one works on B any more
        newly_dead = alive & ~on_b.any(axis=1)
        steps_to_fail[newly_dead] = t
        alive &= ~newly_dead
        if not alive.any():
            break

        # evidence: only agents on B generate information about B
        succ = np.where(on_b, rng.binomial(trials, p_b, size=on_b.shape), 0)
        tried = np.where(on_b, trials, 0)

        # pool own + neighbors' evidence, exact Bayesian (beta-binomial) update
        alpha += succ @ share.T
        beta_ += (tried - succ) @ share.T

        # stash this round's empirical B rate for the LLM's evidence intake.
        # shared: pooled over the whole community; private: each agent's own.
        # gate = 0 where nobody generated B data, so v_L simply doesn't move
        # (the starvation mechanism: an abandoned theory stops informing it).
        if llm_belief and llm_intake == "evidence":
            if llm_shared:
                sc = succ.sum(axis=1, keepdims=True)
                tr = tried.sum(axis=1, keepdims=True)
            else:
                sc, tr = succ, tried
            ev_gate = (tr > 0).astype(float)
            ev_signal = np.where(tr > 0, sc / np.where(tr > 0, tr, 1), 0.0)

    expectation = alpha / (alpha + beta_)
    success = alive & on_b.all(axis=1)      # converged: everyone working on B

    return {
        "success": success,                 # converged: all on the better arm
        "failed": ~alive,                   # absorbed: B abandoned forever
        "undecided": alive & ~success,
        "steps_to_fail": steps_to_fail,
        "trajectory": np.array(trajectory) if trajectory else None,
        "final_expectation": expectation,
        "final_on_b": on_b,
        "params": dict(network=network, n_agents=n_agents, epsilon=epsilon,
                       trials=trials, prior_strength=prior_strength.tolist(),
                       max_steps=max_steps, n_runs=n_runs, seed=seed,
                       rule=rule.tolist(), delta=delta, conf=conf,
                       consult_rate=consult_rate.tolist(),
                       echo_strength=echo_strength, echo_lambda=echo_lambda,
                       echo_polarizing=echo_polarizing,
                       echo_contrarian=echo_contrarian,
                       llm_belief=llm_belief, llm_prior=llm_prior,
                       llm_plasticity=llm_plasticity, llm_intake=llm_intake,
                       llm_shared=llm_shared),
        "final_llm_view": v_l,
    }


def success_rate(**kw):
    r = simulate(**kw)
    return r["success"].mean()
