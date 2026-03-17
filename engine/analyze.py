#!/usr/bin/env python3
"""
EVOLUTION PATTERN ANALYZER — Metacognition engine.

Analyzes evolution history to discover meta-patterns, detect blind spots,
measure learning velocity, recommend strategic pivots, and perform
causal analysis of strategy-outcome relationships.

Inspired by:
- Reflexion (Shinn et al., 2023) — verbal self-reflection
- MAP-Elites (Mouret & Clune, 2015) — quality-diversity
- Novelty Search (Lehman & Stanley, 2011) — reward difference, not just fitness
- Curiosity-Driven Exploration (Pathak et al., 2017) — prediction error as reward

Usage:
    python engine/analyze.py patterns      Mine meta-patterns from history
    python engine/analyze.py blind-spots   Detect unknown unknowns
    python engine/analyze.py velocity      Measure learning speed
    python engine/analyze.py diversity     Check strategy diversity
    python engine/analyze.py recommend     Get strategic recommendations
    python engine/analyze.py report        Full analysis report
    python engine/analyze.py correlations  Strategy-outcome correlational analysis
"""

import json
import math
import sys
from pathlib import Path
from collections import Counter

STATE_FILE = Path("evolution/.state/evolution.json")

# --- Named Constants ---
MIN_CYCLES_FOR_PATTERNS = 5
PLATEAU_VARIANCE = 0.02
SIGNIFICANCE_THRESHOLD = 3   # Min observations before drawing conclusions
OSCILLATION_WINDOW = 6       # Cycles to check for flip-flopping
VELOCITY_WINDOW = 5          # Cycles per velocity window


def load_state() -> dict:
    if not STATE_FILE.exists():
        print('{"error": "No evolution state found"}')
        sys.exit(1)
    with open(STATE_FILE) as f:
        return json.load(f)


def wilson_score(successes: int, total: int, z: float = 1.96) -> tuple:
    """Wilson score confidence interval for binomial proportion.

    More statistically rigorous than simple success/total ratio,
    especially for small sample sizes. Returns (lower, upper) bounds.
    """
    if total == 0:
        return (0.0, 1.0)
    phat = successes / total
    denominator = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denominator
    spread = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total) / denominator
    return (max(0, round(center - spread, 4)), min(1, round(center + spread, 4)))


def effect_size(group1: list, group2: list) -> float:
    """Cohen's d effect size between two groups using Bessel-corrected pooled SD.

    Returns magnitude of difference in standard deviation units:
    - < 0.2: negligible
    - 0.2-0.5: small
    - 0.5-0.8: medium
    - > 0.8: large
    """
    if not group1 or not group2:
        return 0.0
    n1, n2 = len(group1), len(group2)
    mean1, mean2 = sum(group1) / n1, sum(group2) / n2
    # Bessel-corrected sample variance (divide by n-1)
    var1 = sum((x - mean1) ** 2 for x in group1) / max(n1 - 1, 1)
    var2 = sum((x - mean2) ** 2 for x in group2) / max(n2 - 1, 1)
    # Pooled SD weighted by degrees of freedom
    pooled_sd = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / max(n1 + n2 - 2, 1))
    if pooled_sd == 0:
        return 0.0
    return round((mean1 - mean2) / pooled_sd, 3)


def cmd_patterns():
    """Mine meta-patterns from cycle history."""
    state = load_state()
    cycles = state["cycles"]

    if len(cycles) < MIN_CYCLES_FOR_PATTERNS:
        print(json.dumps({"status": "insufficient_data", "cycles": len(cycles),
                          "need": MIN_CYCLES_FOR_PATTERNS}))
        return

    # 1. Strategy performance with confidence intervals
    strategy_performance = {}
    for c in cycles:
        sid = c["strategy"]
        if sid not in strategy_performance:
            strategy_performance[sid] = {"kept": 0, "reverted": 0, "deltas": [], "fitnesses": []}
        if c["kept"]:
            strategy_performance[sid]["kept"] += 1
        else:
            strategy_performance[sid]["reverted"] += 1
        strategy_performance[sid]["deltas"].append(c["delta"])
        strategy_performance[sid]["fitnesses"].append(c["fitness"])

    # Add confidence intervals
    for sid, data in strategy_performance.items():
        total = data["kept"] + data["reverted"]
        lower, upper = wilson_score(data["kept"], total)
        data["success_rate"] = round(data["kept"] / max(total, 1), 3)
        data["confidence_interval"] = [lower, upper]
        data["sample_size"] = total
        data["avg_delta"] = round(sum(data["deltas"]) / len(data["deltas"]), 4) if data["deltas"] else 0
        data["statistically_significant"] = total >= SIGNIFICANCE_THRESHOLD

    # 2. Find streaks
    max_success_streak = 0
    max_failure_streak = 0
    current_streak = 0
    current_type = None
    for c in cycles:
        if c["kept"] == current_type:
            current_streak += 1
        else:
            current_type = c["kept"]
            current_streak = 1
        if current_type:
            max_success_streak = max(max_success_streak, current_streak)
        else:
            max_failure_streak = max(max_failure_streak, current_streak)

    # 3. Detect oscillation pattern
    oscillating = False
    if len(cycles) >= OSCILLATION_WINDOW:
        recent = [c["kept"] for c in cycles[-OSCILLATION_WINDOW:]]
        oscillating = all(recent[i] != recent[i + 1] for i in range(len(recent) - 1))

    # 4. Fitness trajectory analysis
    history = state["fitness_history"]
    thirds = len(history) // 3
    early = history[:thirds] if thirds > 0 else history
    mid = history[thirds:2 * thirds] if thirds > 0 else []
    late = history[2 * thirds:] if thirds > 0 else []

    trajectory = "unknown"
    if early and late:
        early_avg = sum(early) / len(early)
        late_avg = sum(late) / len(late)
        d = effect_size(late, early)
        if d > 0.5:
            trajectory = "improving"
        elif d < -0.5:
            trajectory = "declining"
        elif mid:
            mid_avg = sum(mid) / len(mid)
            if mid_avg > early_avg and late_avg < mid_avg:
                trajectory = "peaked_then_declined"
            else:
                trajectory = "plateau"
        else:
            trajectory = "flat"

    # 5. Action-outcome correlations (what kinds of actions succeed?)
    success_actions = " ".join(c["action"] for c in cycles if c["kept"]).lower().split()
    failure_actions = " ".join(c["action"] for c in cycles if not c["kept"]).lower().split()
    # Filter short/common words
    success_words = Counter(w for w in success_actions if len(w) > 3).most_common(10)
    failure_words = Counter(w for w in failure_actions if len(w) > 3).most_common(10)

    print(json.dumps({
        "strategy_performance": strategy_performance,
        "max_success_streak": max_success_streak,
        "max_failure_streak": max_failure_streak,
        "oscillating": oscillating,
        "trajectory": trajectory,
        "success_keywords": success_words,
        "failure_keywords": failure_words,
    }, indent=2))


def cmd_correlations():
    """Correlational analysis: which strategies associate with success in which contexts?"""
    state = load_state()
    cycles = state["cycles"]

    if len(cycles) < MIN_CYCLES_FOR_PATTERNS:
        print(json.dumps({"status": "insufficient_data"}))
        return

    # 1. Strategy × fitness_range interaction
    # Do some strategies work better at low fitness vs high fitness?
    interactions = {}
    for c in cycles:
        sid = c["strategy"]
        fitness_bucket = "low" if c["fitness"] < 0.33 else ("mid" if c["fitness"] < 0.66 else "high")
        key = f"{sid}@{fitness_bucket}"
        if key not in interactions:
            interactions[key] = {"kept": 0, "total": 0}
        interactions[key]["total"] += 1
        if c["kept"]:
            interactions[key]["kept"] += 1

    for key, data in interactions.items():
        data["success_rate"] = round(data["kept"] / max(data["total"], 1), 3)

    # 2. Sequential patterns: does strategy A followed by B succeed more?
    sequential = {}
    for i in range(1, len(cycles)):
        prev_sid = cycles[i - 1]["strategy"]
        curr_sid = cycles[i]["strategy"]
        key = f"{prev_sid}->{curr_sid}"
        if key not in sequential:
            sequential[key] = {"kept": 0, "total": 0}
        sequential[key]["total"] += 1
        if cycles[i]["kept"]:
            sequential[key]["kept"] += 1

    # Filter to significant patterns
    significant_sequences = {
        k: {**v, "success_rate": round(v["kept"] / v["total"], 3)}
        for k, v in sequential.items()
        if v["total"] >= 2
    }

    # 3. Time-of-evolution patterns (do early strategies differ from late?)
    midpoint = len(cycles) // 2
    early_success = sum(1 for c in cycles[:midpoint] if c["kept"])
    late_success = sum(1 for c in cycles[midpoint:] if c["kept"])
    early_total = max(midpoint, 1)
    late_total = max(len(cycles) - midpoint, 1)

    print(json.dumps({
        "strategy_context_interactions": interactions,
        "significant_sequences": significant_sequences,
        "early_vs_late": {
            "early_success_rate": round(early_success / early_total, 3),
            "late_success_rate": round(late_success / late_total, 3),
            "learning_effect": effect_size(
                [1 if c["kept"] else 0 for c in cycles[midpoint:]],
                [1 if c["kept"] else 0 for c in cycles[:midpoint]]
            ),
        },
    }, indent=2))


def cmd_blind_spots():
    """Detect potential blind spots in the evolution."""
    state = load_state()
    strategies = state["strategies"]
    graveyard = state["graveyard"]
    cycles = state["cycles"]

    blind_spots = []

    # 1. Untested strategies
    untested = [s for s in strategies if s["attempts"] == 0]
    if untested:
        blind_spots.append({
            "type": "untested_strategies",
            "severity": "HIGH",
            "detail": f"{len(untested)} strategies have never been tried",
            "strategies": [s["id"] for s in untested],
        })

    # 2. Low diversity (approaches too similar)
    if len(strategies) > 0:
        approaches = set(s["approach"][:50] for s in strategies)
        if len(approaches) < max(2, len(strategies) // 3):
            blind_spots.append({
                "type": "low_diversity",
                "severity": "HIGH",
                "detail": f"Only {len(approaches)} distinct approaches among {len(strategies)} strategies",
            })

    # 3. Never-explored mutation types
    has_mutation = any(s.get("parent") for s in strategies)
    if len(cycles) > 10 and not has_mutation:
        blind_spots.append({
            "type": "no_mutations",
            "severity": "MEDIUM",
            "detail": "No strategy mutations have been attempted after 10+ cycles",
        })

    # 4. Repeated failure modes
    if len(graveyard) >= 3:
        reasons = Counter(s.get("extinction_reason", "unknown") for s in graveyard)
        repeated = [(r, c) for r, c in reasons.most_common() if c >= 2]
        if repeated:
            blind_spots.append({
                "type": "repeated_failures",
                "severity": "MEDIUM",
                "detail": f"Same failure patterns recurring: {repeated}",
            })

    # 5. Fitness ceiling
    if len(cycles) > 15:
        recent_fitness = [c["fitness"] for c in cycles[-5:]]
        if all(f > 0.9 for f in recent_fitness) and state["fitness"] < 1.0:
            blind_spots.append({
                "type": "fitness_ceiling",
                "severity": "LOW",
                "detail": "Fitness consistently >0.9 but goal not achieved — fitness function may not capture remaining work",
            })

    # 6. Over-reliance on one strategy
    if len(cycles) >= 10:
        recent_strategies = [c["strategy"] for c in cycles[-10:]]
        strategy_counts = Counter(recent_strategies)
        dominant = strategy_counts.most_common(1)[0]
        if dominant[1] >= 8:  # 80%+ of recent cycles use same strategy
            blind_spots.append({
                "type": "over_reliance",
                "severity": "MEDIUM",
                "detail": f"Strategy {dominant[0]} used in {dominant[1]}/10 recent cycles — explore alternatives",
            })

    # 7. No crystallization
    if len(cycles) >= 15 and not state.get("principles"):
        blind_spots.append({
            "type": "no_crystallization",
            "severity": "LOW",
            "detail": "15+ cycles completed but no principles crystallized — run 'crystallize' to extract learnings",
        })

    print(json.dumps({"blind_spots": blind_spots}, indent=2))


def cmd_velocity():
    """Measure learning velocity — how fast is fitness improving?"""
    state = load_state()
    history = state["fitness_history"]

    if len(history) < 2:
        print(json.dumps({"velocity": 0, "status": "insufficient_data"}))
        return

    # Calculate velocity in windows
    windows = []
    for i in range(0, len(history) - VELOCITY_WINDOW + 1, VELOCITY_WINDOW):
        window = history[i:i + VELOCITY_WINDOW]
        if len(window) >= 2:
            velocity = (window[-1] - window[0]) / len(window)
            windows.append({
                "cycles": f"{i + 1}-{i + len(window)}",
                "start_fitness": round(window[0], 4),
                "end_fitness": round(window[-1], 4),
                "velocity": round(velocity, 4),
            })

    # Overall velocity
    overall = (history[-1] - history[0]) / len(history)

    # Acceleration (is velocity increasing or decreasing?)
    acceleration = 0.0
    if len(windows) >= 2:
        acceleration = windows[-1]["velocity"] - windows[-2]["velocity"]

    # Estimated cycles to completion
    if overall > 0:
        remaining_fitness = 1.0 - state["fitness"]
        estimated_cycles = remaining_fitness / overall
    else:
        estimated_cycles = float("inf")

    # Efficiency: what % of cycles actually improved fitness?
    productive_cycles = sum(1 for c in state["cycles"] if c["kept"])
    total_cycles = max(len(state["cycles"]), 1)
    efficiency = round(productive_cycles / total_cycles, 3)

    print(json.dumps({
        "overall_velocity": round(overall, 4),
        "acceleration": round(acceleration, 4),
        "current_fitness": state["fitness"],
        "windows": windows,
        "estimated_cycles_remaining": round(estimated_cycles, 1) if estimated_cycles != float("inf") else "infinite",
        "efficiency": efficiency,
        "productive_cycles": productive_cycles,
        "total_cycles": total_cycles,
        "phase": state["phase"],
    }, indent=2))


def cmd_diversity():
    """Measure strategy population diversity (Quality-Diversity check)."""
    state = load_state()
    strategies = state["strategies"]

    if not strategies:
        print(json.dumps({"diversity": 0, "strategies": 0}))
        return

    # Group by generation
    generations = Counter(s["generation"] for s in strategies)

    # Group by parent lineage
    lineages = Counter(s.get("parent", "genesis") or "genesis" for s in strategies)

    # Fitness distribution
    fitnesses = [s["fitness"] for s in strategies]
    fitness_mean = sum(fitnesses) / len(fitnesses)
    fitness_variance = sum((f - fitness_mean) ** 2 for f in fitnesses) / len(fitnesses)

    # Diversity score: higher is more diverse
    n_strategies = len(strategies)
    n_lineages = len(lineages)
    diversity = n_lineages / max(n_strategies, 1)

    # Status distribution
    statuses = Counter(s["status"] for s in strategies)

    recommendation = "HEALTHY"
    if diversity < 0.3:
        recommendation = "ADD_DIVERSITY — too many strategies from same lineage"
    elif n_strategies < 3:
        recommendation = "ADD_STRATEGIES — population too small for effective selection"
    elif fitness_variance < 0.001 and n_strategies > 3:
        recommendation = "DIFFERENTIATE — strategies are too similar in fitness"

    print(json.dumps({
        "diversity_score": round(diversity, 3),
        "total_strategies": n_strategies,
        "unique_lineages": n_lineages,
        "generations": dict(generations),
        "statuses": dict(statuses),
        "fitness_mean": round(fitness_mean, 4),
        "fitness_variance": round(fitness_variance, 4),
        "graveyard_size": len(state["graveyard"]),
        "recommendation": recommendation,
    }, indent=2))


def cmd_recommend():
    """Generate strategic recommendations based on current state."""
    state = load_state()
    recommendations = []

    # Phase-based recommendations
    phase = state["phase"]
    if phase == "GENESIS":
        recommendations.append({
            "priority": 1,
            "action": "Focus on testing diverse strategies quickly",
            "reason": "Early phase — explore broadly before exploiting",
        })
    elif phase == "PLATEAU":
        recommendations.append({
            "priority": 0,
            "action": "PIVOT: Try fundamentally different approach",
            "reason": f"Fitness stagnant at {state['fitness']:.3f}",
        })
        recommendations.append({
            "priority": 1,
            "action": "Check graveyard for strategies worth resurrecting",
            "reason": "Context may have changed since they failed",
        })
        recommendations.append({
            "priority": 2,
            "action": "Increase exploration rate to 0.50",
            "reason": "Need more randomness to escape local optimum",
        })
    elif phase == "GROWTH":
        recommendations.append({
            "priority": 1,
            "action": "Refine current best strategy with small mutations",
            "reason": "Fitness is improving — exploit the current approach",
        })
    elif phase == "MATURITY":
        recommendations.append({
            "priority": 1,
            "action": "Focus on remaining success criteria",
            "reason": f"Fitness at {state['fitness']:.3f} — near completion",
        })

    # Failure-based recommendations
    if state["consecutive_failures"] >= 3:
        recommendations.insert(0, {
            "priority": 0,
            "action": "STOP current approach — 3+ consecutive failures",
            "reason": "Current strategy is not working. Mutate or replace.",
        })
    if state["consecutive_failures"] >= 5:
        recommendations.insert(0, {
            "priority": 0,
            "action": "ESCALATION: Re-read all source files, re-examine goal tree, try opposite approach",
            "reason": "5+ consecutive failures — fundamental reassessment needed",
        })

    # Diversity-based recommendations
    active = [s for s in state["strategies"] if s["status"] != "EXTINCT"]
    if len(active) < 3:
        recommendations.append({
            "priority": 2,
            "action": "Generate more strategies — population too small",
            "reason": f"Only {len(active)} active strategies",
        })
    elif len(active) > 8:
        recommendations.append({
            "priority": 2,
            "action": "Cull weakest strategies — population too large",
            "reason": f"{len(active)} active strategies — reduce to focus",
        })

    # Crystallization recommendation
    if state["cycle"] >= 10 and state["cycle"] % 10 == 0 and not state.get("principles"):
        recommendations.append({
            "priority": 3,
            "action": "Run crystallize to extract learnings into principles",
            "reason": f"{state['cycle']} cycles completed — time to consolidate knowledge",
        })

    recommendations.sort(key=lambda r: r["priority"])
    print(json.dumps({"recommendations": recommendations}, indent=2))


def cmd_report():
    """Full analysis report combining all analyses."""
    state = load_state()
    print("=" * 60)
    print("EVOLUTION ANALYSIS REPORT")
    print("=" * 60)
    print(f"\nGoal: {state['goal']}")
    print(f"Phase: {state['phase']}")
    print(f"Cycle: {state['cycle']}")
    print(f"Fitness: {state['fitness']:.4f}")
    print(f"Exploration Rate: {state['exploration_rate']:.3f}")
    print(f"\n{'—' * 60}")
    print("\n## Velocity")
    cmd_velocity()
    print(f"\n{'—' * 60}")
    print("\n## Diversity")
    cmd_diversity()
    print(f"\n{'—' * 60}")
    print("\n## Blind Spots")
    cmd_blind_spots()
    print(f"\n{'—' * 60}")
    print("\n## Correlations")
    cmd_correlations()
    print(f"\n{'—' * 60}")
    print("\n## Recommendations")
    cmd_recommend()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    commands = {
        "patterns": cmd_patterns,
        "blind-spots": cmd_blind_spots,
        "velocity": cmd_velocity,
        "diversity": cmd_diversity,
        "recommend": cmd_recommend,
        "report": cmd_report,
        "correlations": cmd_correlations,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
