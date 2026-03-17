#!/usr/bin/env python3
"""
EVOLUTION SWARM INTELLIGENCE — Monte Carlo simulation + multi-persona consensus.

MiroFish applied: instead of asking the LLM to imagine futures, we COMPUTE them.
Historical outcome data builds empirical transition models. Monte Carlo simulation
projects strategy trajectories forward. Multiple virtual evaluators with different
utility functions vote on the best path. The result is a strategy recommendation
grounded in statistical reality, not LLM imagination.

The swarm replaces "what does the LLM think will happen?" with "what does the
data say will happen, evaluated from multiple perspectives?"

Usage:
    python engine/swarm.py simulate [n_sims] [horizon]   Monte Carlo strategy simulation
    python engine/swarm.py select                         Swarm-consensus strategy selection
    python engine/swarm.py landscape                      Map explored fitness space + gaps
    python engine/swarm.py predict <strategy_id> [steps]  Predict trajectory for one strategy
    python engine/swarm.py personas                       Show swarm personas and their weights
    python engine/swarm.py history [N]                    Recent swarm decisions
"""

import json
import math
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

try:
    from engine.stats import now, wilson_lower, sample_sd
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now, wilson_lower, sample_sd

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
STATE_FILE = STATE_DIR / "evolution.json"
OUTCOMES_FILE = STATE_DIR / "outcomes.jsonl"
SWARM_LOG = STATE_DIR / "swarm.jsonl"

# Simulation defaults
DEFAULT_SIMULATIONS = 500
DEFAULT_HORIZON = 10  # cycles ahead
FITNESS_BUCKETS = {"low": (0.0, 0.33), "mid": (0.33, 0.66), "high": (0.66, 1.0)}

# Swarm personas — each evaluates strategies through a different lens
PERSONAS = {
    "explorer": {
        "description": "Maximizes information gain — prefers high-uncertainty strategies",
        "weights": {"info_gain": 0.50, "expected_value": 0.15, "upside": 0.25, "downside": 0.10},
    },
    "exploiter": {
        "description": "Maximizes expected fitness gain — prefers proven winners",
        "weights": {"info_gain": 0.05, "expected_value": 0.55, "upside": 0.25, "downside": 0.15},
    },
    "contrarian": {
        "description": "Prefers strategies dissimilar to recent choices — breaks ruts",
        "weights": {"info_gain": 0.20, "expected_value": 0.15, "upside": 0.15, "downside": 0.10, "novelty": 0.40},
    },
    "survivor": {
        "description": "Minimizes downside risk — prefers low-variance strategies",
        "weights": {"info_gain": 0.05, "expected_value": 0.30, "upside": 0.10, "downside": 0.55},
    },
    "strategist": {
        "description": "Weights trajectory momentum — prefers strategies on an upswing",
        "weights": {"info_gain": 0.10, "expected_value": 0.25, "upside": 0.20, "downside": 0.15, "momentum": 0.30},
    },
}

MAX_HISTORY = 200


# ============================================================================
# DATA LOADING
# ============================================================================

def load_state() -> dict:
    """Load evolution state."""
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)


def load_outcomes() -> list:
    """Load outcome records from JSONL."""
    if not OUTCOMES_FILE.exists():
        return []
    results = []
    with open(OUTCOMES_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return results


# ============================================================================
# TRANSITION MODEL — Empirical P(fitness_delta | strategy, fitness_bucket)
# ============================================================================

def _fitness_bucket(fitness: float) -> str:
    """Classify fitness into bucket."""
    if fitness < 0.33:
        return "low"
    elif fitness < 0.66:
        return "mid"
    return "high"


def build_transition_model(state: dict) -> dict:
    """Build empirical transition model from cycle history.

    Returns a nested dict:
        model[strategy_id][fitness_bucket] = {
            "deltas": [list of fitness deltas],
            "mean_delta": float,
            "sd_delta": float,
            "success_rate": float,
            "n": int,
        }

    Also builds a global fallback for strategies with no history.
    """
    model = {}
    global_deltas = {"low": [], "mid": [], "high": []}

    for cycle in state.get("cycles", []):
        sid = cycle.get("strategy")
        delta = cycle.get("delta", 0.0)
        fitness = cycle.get("fitness", 0.0)
        prev_fitness = fitness - delta
        bucket = _fitness_bucket(max(0.0, prev_fitness))

        if sid not in model:
            model[sid] = {}
        if bucket not in model[sid]:
            model[sid][bucket] = {"deltas": [], "kept": 0, "total": 0}

        model[sid][bucket]["deltas"].append(delta)
        model[sid][bucket]["total"] += 1
        if cycle.get("kept", False):
            model[sid][bucket]["kept"] += 1

        global_deltas[bucket].append(delta)

    # Compute statistics
    for sid in model:
        for bucket in model[sid]:
            entry = model[sid][bucket]
            deltas = entry["deltas"]
            entry["mean_delta"] = sum(deltas) / len(deltas) if deltas else 0.0
            entry["sd_delta"] = sample_sd(deltas) if len(deltas) >= 2 else 0.05
            entry["success_rate"] = entry["kept"] / entry["total"] if entry["total"] else 0.5
            entry["n"] = len(deltas)

    # Global fallback
    model["_global"] = {}
    for bucket, deltas in global_deltas.items():
        if deltas:
            model["_global"][bucket] = {
                "deltas": deltas,
                "mean_delta": sum(deltas) / len(deltas),
                "sd_delta": sample_sd(deltas) if len(deltas) >= 2 else 0.05,
                "success_rate": 0.5,
                "n": len(deltas),
            }
        else:
            model["_global"][bucket] = {
                "deltas": [],
                "mean_delta": 0.02,
                "sd_delta": 0.05,
                "success_rate": 0.5,
                "n": 0,
            }

    return model


def _sample_delta(model: dict, strategy_id: str, fitness: float) -> float:
    """Sample a fitness delta from the transition model.

    Uses strategy-specific data if available (>= 3 observations),
    otherwise falls back to global bucket statistics.
    """
    bucket = _fitness_bucket(fitness)

    # Try strategy-specific model
    strat_data = model.get(strategy_id, {}).get(bucket)
    if strat_data and strat_data["n"] >= 3:
        # Sample from empirical distribution (normal approximation + noise)
        delta = random.gauss(strat_data["mean_delta"], strat_data["sd_delta"])
        # Apply success/failure draw (sometimes improvements get reverted)
        if random.random() > strat_data["success_rate"]:
            delta = min(delta, 0)  # Failed cycles don't gain fitness
        return delta

    # Fall back to global
    global_data = model.get("_global", {}).get(bucket, {})
    mean = global_data.get("mean_delta", 0.02)
    sd = global_data.get("sd_delta", 0.05)
    return random.gauss(mean, sd)


# ============================================================================
# MONTE CARLO SIMULATION
# ============================================================================

def monte_carlo_simulate(strategy: dict, model: dict, current_fitness: float,
                         n_sims: int = DEFAULT_SIMULATIONS,
                         horizon: int = DEFAULT_HORIZON) -> dict:
    """Run Monte Carlo simulation of a strategy's future trajectory.

    For each simulation:
      1. Start at current_fitness
      2. Sample fitness deltas from the transition model for `horizon` steps
      3. Clamp fitness to [0, 1]
      4. Record final fitness and trajectory

    Returns statistics over all simulations.
    """
    sid = strategy["id"]
    final_fitnesses = []
    max_fitnesses = []
    min_fitnesses = []
    trajectories_sample = []  # Store a few full trajectories for visualization

    for sim in range(n_sims):
        fitness = current_fitness
        trajectory = [fitness]

        for step in range(horizon):
            delta = _sample_delta(model, sid, fitness)
            fitness = max(0.0, min(1.0, fitness + delta))
            trajectory.append(fitness)

        final_fitnesses.append(fitness)
        max_fitnesses.append(max(trajectory))
        min_fitnesses.append(min(trajectory))
        if sim < 5:  # Store first 5 trajectories for inspection
            trajectories_sample.append([round(f, 4) for f in trajectory])

    # Statistics
    mean_final = sum(final_fitnesses) / n_sims
    sd_final = sample_sd(final_fitnesses) if n_sims >= 2 else 0.0
    sorted_finals = sorted(final_fitnesses)
    p10 = sorted_finals[int(n_sims * 0.10)]
    p25 = sorted_finals[int(n_sims * 0.25)]
    p50 = sorted_finals[int(n_sims * 0.50)]
    p75 = sorted_finals[int(n_sims * 0.75)]
    p90 = sorted_finals[int(n_sims * 0.90)]

    # Expected gain
    expected_gain = mean_final - current_fitness

    # Probability of improvement
    prob_improve = sum(1 for f in final_fitnesses if f > current_fitness) / n_sims

    # Probability of reaching key thresholds
    prob_above_80 = sum(1 for f in final_fitnesses if f >= 0.80) / n_sims
    prob_above_90 = sum(1 for f in final_fitnesses if f >= 0.90) / n_sims

    # Downside: P(fitness drops by more than 0.05)
    prob_regression = sum(1 for f in final_fitnesses if f < current_fitness - 0.05) / n_sims

    # Sharpe-like ratio: expected gain / volatility
    sharpe = expected_gain / sd_final if sd_final > 0 else 0.0

    return {
        "strategy_id": sid,
        "strategy_name": strategy.get("name", ""),
        "current_fitness": round(current_fitness, 4),
        "simulations": n_sims,
        "horizon": horizon,
        "mean_final": round(mean_final, 4),
        "sd_final": round(sd_final, 4),
        "expected_gain": round(expected_gain, 4),
        "sharpe_ratio": round(sharpe, 4),
        "prob_improve": round(prob_improve, 4),
        "prob_above_80": round(prob_above_80, 4),
        "prob_above_90": round(prob_above_90, 4),
        "prob_regression": round(prob_regression, 4),
        "percentiles": {
            "p10": round(p10, 4), "p25": round(p25, 4), "p50": round(p50, 4),
            "p75": round(p75, 4), "p90": round(p90, 4),
        },
        "max_potential": round(max(max_fitnesses), 4),
        "worst_case": round(min(min_fitnesses), 4),
        "sample_trajectories": trajectories_sample,
    }


# ============================================================================
# INFORMATION THEORY
# ============================================================================

def beta_entropy(alpha: float, beta_param: float) -> float:
    """Entropy of Beta(alpha, beta) distribution.

    Higher entropy = more uncertainty = more to learn from trying this strategy.
    Uses the digamma approximation for the Beta distribution entropy.
    """
    if alpha <= 0 or beta_param <= 0:
        return 0.0
    total = alpha + beta_param
    # Beta distribution entropy formula
    try:
        ln_beta = math.lgamma(alpha) + math.lgamma(beta_param) - math.lgamma(total)
        psi_sum = (alpha - 1) * _digamma(alpha) + (beta_param - 1) * _digamma(beta_param)
        psi_total = (total - 2) * _digamma(total)
        return ln_beta - psi_sum + psi_total
    except (ValueError, OverflowError):
        return 0.0


def _digamma(x: float) -> float:
    """Digamma function approximation (Stirling series)."""
    if x < 1e-6:
        return -1.0 / max(x, 1e-10)
    # Shift x up for better convergence
    result = 0.0
    while x < 6:
        result -= 1.0 / x
        x += 1
    # Asymptotic expansion
    result += math.log(x) - 1.0 / (2 * x)
    x2 = x * x
    result -= 1.0 / (12 * x2)
    result += 1.0 / (120 * x2 * x2)
    return result


def expected_information_gain(strategy: dict) -> float:
    """Compute expected information gain from trying a strategy.

    Strategies with more uncertainty (higher Beta entropy) = more to learn.
    Untested strategies have maximum information gain.
    """
    alpha = strategy.get("successes", 0) + 1
    beta_param = (strategy.get("attempts", 0) - strategy.get("successes", 0)) + 1
    return beta_entropy(alpha, beta_param)


# ============================================================================
# NOVELTY / DISSIMILARITY
# ============================================================================

def novelty_score(strategy: dict, state: dict) -> float:
    """How different is this strategy from recent choices?

    Measures cycles since this strategy was last used, normalized.
    Strategies never used get maximum novelty.
    """
    cycles = state.get("cycles", [])
    if not cycles:
        return 1.0

    sid = strategy["id"]
    # Find most recent use
    for i in range(len(cycles) - 1, -1, -1):
        if cycles[i].get("strategy") == sid:
            cycles_ago = len(cycles) - i
            # Normalize: 1 cycle ago = low novelty, 10+ cycles ago = high novelty
            return min(1.0, cycles_ago / 10.0)

    return 1.0  # Never used = maximum novelty


def momentum_score(strategy: dict, state: dict) -> float:
    """Is this strategy on an upswing or downswing?

    Looks at the last N cycles this strategy was used and computes
    the trend in fitness deltas. Positive trend = upswing.
    """
    sid = strategy["id"]
    deltas = []
    for cycle in state.get("cycles", []):
        if cycle.get("strategy") == sid:
            deltas.append(cycle.get("delta", 0.0))

    if len(deltas) < 2:
        return 0.5  # Neutral — not enough data

    # Use last 5 deltas max
    recent = deltas[-5:]
    # Simple linear regression slope
    n = len(recent)
    x_mean = (n - 1) / 2.0
    y_mean = sum(recent) / n
    num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
    den = sum((i - x_mean) ** 2 for i in range(n))

    if den == 0:
        return 0.5

    slope = num / den
    # Normalize slope to [0, 1] range: negative slope = 0, strong positive = 1
    return max(0.0, min(1.0, 0.5 + slope * 5))


# ============================================================================
# SWARM EVALUATION — Multi-persona consensus
# ============================================================================

def persona_evaluate(persona_name: str, simulations: dict, state: dict) -> list:
    """A single swarm persona ranks strategies according to its utility function.

    Each persona weights the simulation metrics differently:
      - info_gain: Beta entropy (uncertainty)
      - expected_value: Mean final fitness from Monte Carlo
      - upside: P90 potential
      - downside: 1 - P(regression) [higher = safer]
      - novelty: Dissimilarity from recent choices
      - momentum: Trajectory trend
    """
    persona = PERSONAS[persona_name]
    weights = persona["weights"]
    scored = []

    for sid, sim in simulations.items():
        strategy = sim["_strategy"]

        components = {
            "info_gain": expected_information_gain(strategy),
            "expected_value": sim["expected_gain"],
            "upside": sim["percentiles"]["p90"],
            "downside": 1.0 - sim["prob_regression"],
        }

        if "novelty" in weights:
            components["novelty"] = novelty_score(strategy, state)
        if "momentum" in weights:
            components["momentum"] = momentum_score(strategy, state)

        # Normalize expected_value to [0, 1] range for fair weighting
        # EV can be negative; map [-0.5, 0.5] to [0, 1]
        ev = components["expected_value"]
        components["expected_value"] = max(0.0, min(1.0, ev + 0.5))

        # Weighted sum
        score = sum(weights.get(k, 0) * components.get(k, 0) for k in weights)

        scored.append({
            "strategy_id": sid,
            "score": round(score, 6),
            "components": {k: round(v, 4) for k, v in components.items()},
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def borda_count(persona_rankings: dict) -> list:
    """Aggregate persona rankings using Borda count voting.

    Each persona gives N points to their 1st choice, N-1 to 2nd, etc.
    The strategy with the most total Borda points wins.
    Returns the final consensus ranking.
    """
    points = Counter()

    for persona_name, ranking in persona_rankings.items():
        n = len(ranking)
        for i, entry in enumerate(ranking):
            # Top-ranked gets n points, second gets n-1, etc.
            points[entry["strategy_id"]] += (n - i)

    # Sort by Borda points descending
    ranked = sorted(points.items(), key=lambda x: -x[1])
    return [{"strategy_id": sid, "borda_points": pts} for sid, pts in ranked]


def swarm_select(state: dict, n_sims: int = DEFAULT_SIMULATIONS,
                 horizon: int = DEFAULT_HORIZON) -> dict:
    """Full swarm intelligence pipeline.

    1. Build transition model from historical data
    2. Monte Carlo simulate each active strategy
    3. Each persona evaluates all simulations independently
    4. Borda count aggregates into consensus
    5. Return recommended strategy with full reasoning
    """
    strategies = [s for s in state.get("strategies", [])
                  if s.get("status") != "EXTINCT"]

    if not strategies:
        return {"error": "No active strategies"}

    current_fitness = state.get("fitness", 0.0)
    model = build_transition_model(state)

    # Monte Carlo simulation for each strategy
    simulations = {}
    for s in strategies:
        sim = monte_carlo_simulate(s, model, current_fitness, n_sims, horizon)
        sim["_strategy"] = s  # Attach for persona evaluation
        simulations[s["id"]] = sim

    # Each persona evaluates independently
    persona_rankings = {}
    for persona_name in PERSONAS:
        persona_rankings[persona_name] = persona_evaluate(persona_name, simulations, state)

    # Borda count consensus
    consensus = borda_count(persona_rankings)

    # Who agreed and who dissented?
    winner_id = consensus[0]["strategy_id"]
    agreement = {}
    for persona_name, ranking in persona_rankings.items():
        top_pick = ranking[0]["strategy_id"]
        agreement[persona_name] = {
            "top_pick": top_pick,
            "agrees_with_consensus": top_pick == winner_id,
        }

    unanimity = sum(1 for a in agreement.values() if a["agrees_with_consensus"])
    confidence = unanimity / len(PERSONAS)

    # Clean simulations for output (remove internal _strategy reference)
    clean_sims = {}
    for sid, sim in simulations.items():
        clean = {k: v for k, v in sim.items() if k != "_strategy"}
        clean_sims[sid] = clean

    return {
        "recommended": winner_id,
        "recommended_name": next(
            (s["name"] for s in strategies if s["id"] == winner_id), ""
        ),
        "consensus": consensus,
        "confidence": round(confidence, 2),
        "unanimity": f"{unanimity}/{len(PERSONAS)}",
        "persona_top_picks": agreement,
        "simulations": clean_sims,
        "model_stats": {
            "strategies_modeled": len([k for k in model if k != "_global"]),
            "total_observations": sum(
                sum(b.get("n", 0) for b in buckets.values())
                for sid, buckets in model.items() if sid != "_global"
            ),
            "fitness_context": _fitness_bucket(current_fitness),
        },
        "method": "monte_carlo_swarm_consensus",
        "simulations_per_strategy": n_sims,
        "horizon_cycles": horizon,
        "timestamp": now(),
    }


# ============================================================================
# FITNESS LANDSCAPE MAPPING
# ============================================================================

def map_landscape(state: dict) -> dict:
    """Map the explored fitness landscape.

    Shows which regions of fitness space have been explored, where strategies
    have visited, and where coverage gaps exist. This is the closest we get
    to a real fitness landscape without a multi-dimensional behavior space.
    """
    cycles = state.get("cycles", [])
    if not cycles:
        return {"message": "No cycles yet — landscape unmapped", "explored": []}

    # Discretize fitness into 20 bins (0.00-0.05, 0.05-0.10, ...)
    bins = 20
    bin_width = 1.0 / bins
    explored = [0] * bins
    strategy_coverage = {}  # which strategies visited which bins
    transitions = []  # (from_bin, to_bin, strategy, kept)

    prev_fitness = 0.0
    for cycle in cycles:
        fitness = cycle.get("fitness", 0.0)
        delta = cycle.get("delta", 0.0)
        sid = cycle.get("strategy", "?")
        kept = cycle.get("kept", False)

        current_bin = min(int(fitness / bin_width), bins - 1)
        prev_bin = min(int(max(0, fitness - delta) / bin_width), bins - 1)

        explored[current_bin] += 1

        if sid not in strategy_coverage:
            strategy_coverage[sid] = set()
        strategy_coverage[sid].add(current_bin)

        transitions.append({
            "from": round(prev_bin * bin_width, 2),
            "to": round(current_bin * bin_width, 2),
            "strategy": sid,
            "kept": kept,
        })

        prev_fitness = fitness

    # Find gaps — unexplored bins between the lowest and highest explored
    explored_indices = [i for i, count in enumerate(explored) if count > 0]
    if explored_indices:
        low = min(explored_indices)
        high = max(explored_indices)
        gaps = [round(i * bin_width, 2) for i in range(low, high + 1) if explored[i] == 0]
    else:
        gaps = []

    # Strategy coverage diversity
    coverage_scores = {}
    for sid, bins_visited in strategy_coverage.items():
        coverage_scores[sid] = {
            "bins_visited": len(bins_visited),
            "coverage": round(len(bins_visited) / bins, 4),
            "range": [
                round(min(bins_visited) * bin_width, 2),
                round((max(bins_visited) + 1) * bin_width, 2),
            ],
        }

    # Build heatmap (ASCII-friendly)
    max_visits = max(explored) if explored else 1
    heatmap = ""
    for i in range(bins):
        bar_len = int((explored[i] / max(max_visits, 1)) * 20)
        label = f"{i * bin_width:.2f}-{(i + 1) * bin_width:.2f}"
        heatmap += f"  {label} |{'#' * bar_len}{' ' * (20 - bar_len)}| {explored[i]}\n"

    return {
        "total_cycles": len(cycles),
        "bins_explored": len(explored_indices),
        "bins_total": bins,
        "coverage_ratio": round(len(explored_indices) / bins, 4),
        "gaps": gaps,
        "current_fitness": round(state.get("fitness", 0.0), 4),
        "fitness_range": {
            "min": round(min(c.get("fitness", 0) for c in cycles), 4),
            "max": round(max(c.get("fitness", 0) for c in cycles), 4),
        },
        "strategy_coverage": coverage_scores,
        "visit_distribution": [
            {"bin": f"{i * bin_width:.2f}-{(i + 1) * bin_width:.2f}", "visits": explored[i]}
            for i in range(bins) if explored[i] > 0
        ],
        "heatmap": heatmap,
        "recent_transitions": transitions[-20:],
    }


# ============================================================================
# LOGGING
# ============================================================================

def log_swarm_decision(decision: dict):
    """Append swarm decision to JSONL log."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Slim down for logging — drop full simulation details
    log_entry = {
        "recommended": decision.get("recommended"),
        "confidence": decision.get("confidence"),
        "unanimity": decision.get("unanimity"),
        "consensus_top3": decision.get("consensus", [])[:3],
        "persona_picks": decision.get("persona_top_picks"),
        "timestamp": decision.get("timestamp", now()),
    }
    line = json.dumps(log_entry, separators=(",", ":"))
    fd = os.open(str(SWARM_LOG), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


# ============================================================================
# CLI COMMANDS
# ============================================================================

def cmd_simulate(n_sims: int = DEFAULT_SIMULATIONS, horizon: int = DEFAULT_HORIZON):
    """Run Monte Carlo simulation for all active strategies."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No evolution state. Run 'init' first."}))
        sys.exit(1)

    strategies = [s for s in state.get("strategies", [])
                  if s.get("status") != "EXTINCT"]
    if not strategies:
        print(json.dumps({"error": "No active strategies to simulate"}))
        sys.exit(1)

    current_fitness = state.get("fitness", 0.0)
    model = build_transition_model(state)

    results = []
    for s in strategies:
        sim = monte_carlo_simulate(s, model, current_fitness, n_sims, horizon)
        results.append(sim)

    # Rank by expected gain
    results.sort(key=lambda x: x["expected_gain"], reverse=True)

    print(json.dumps({
        "simulations": results,
        "current_fitness": round(current_fitness, 4),
        "strategies_simulated": len(results),
        "sims_per_strategy": n_sims,
        "horizon_cycles": horizon,
        "model_observations": sum(
            sum(b.get("n", 0) for b in buckets.values())
            for sid, buckets in model.items() if sid != "_global"
        ),
    }, indent=2))


def cmd_select():
    """Swarm-consensus strategy selection."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No evolution state. Run 'init' first."}))
        sys.exit(1)

    result = swarm_select(state)

    if "error" in result:
        print(json.dumps(result))
        sys.exit(1)

    log_swarm_decision(result)
    print(json.dumps(result, indent=2))


def cmd_landscape():
    """Map the explored fitness landscape."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No evolution state. Run 'init' first."}))
        sys.exit(1)

    landscape = map_landscape(state)
    print(json.dumps(landscape, indent=2))


def cmd_predict(strategy_id: str, steps: int = DEFAULT_HORIZON):
    """Predict trajectory for a single strategy."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No evolution state. Run 'init' first."}))
        sys.exit(1)

    strategy = None
    for s in state.get("strategies", []):
        if s["id"] == strategy_id:
            strategy = s
            break

    if not strategy:
        print(json.dumps({"error": f"Strategy {strategy_id} not found"}))
        sys.exit(1)

    model = build_transition_model(state)
    sim = monte_carlo_simulate(
        strategy, model, state.get("fitness", 0.0),
        n_sims=1000, horizon=steps
    )
    # Also include info gain and momentum
    sim["info_gain"] = round(expected_information_gain(strategy), 4)
    sim["momentum"] = round(momentum_score(strategy, state), 4)
    sim["novelty"] = round(novelty_score(strategy, state), 4)

    print(json.dumps(sim, indent=2))


def cmd_personas():
    """Show swarm personas and their utility weights."""
    output = {}
    for name, persona in PERSONAS.items():
        output[name] = {
            "description": persona["description"],
            "weights": persona["weights"],
        }
    print(json.dumps(output, indent=2))


def cmd_history(n: int = 20):
    """Show recent swarm decisions."""
    if not SWARM_LOG.exists():
        print(json.dumps({"decisions": [], "total": 0}))
        return

    entries = []
    with open(SWARM_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    recent = entries[-n:]
    print(json.dumps({"decisions": recent, "total": len(entries)}, indent=2))


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "simulate":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SIMULATIONS
            h = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_HORIZON
            cmd_simulate(n, h)
        elif cmd == "select":
            cmd_select()
        elif cmd == "landscape":
            cmd_landscape()
        elif cmd == "predict":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: predict <strategy_id> [steps]"}))
                sys.exit(1)
            steps = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_HORIZON
            cmd_predict(sys.argv[2], steps)
        elif cmd == "personas":
            cmd_personas()
        elif cmd == "history":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            cmd_history(n)
        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
