#!/usr/bin/env python3
"""
EVOLUTION PATTERN ANALYZER — Metacognition engine.

Analyzes evolution history to discover meta-patterns, detect blind spots,
measure learning velocity, and recommend strategic pivots.

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
"""

import json
import sys
from pathlib import Path
from collections import Counter

STATE_FILE = Path("evolution/.state/evolution.json")


def load_state() -> dict:
    if not STATE_FILE.exists():
        print('{"error": "No evolution state found"}')
        sys.exit(1)
    with open(STATE_FILE) as f:
        return json.load(f)


def cmd_patterns():
    """Mine meta-patterns from cycle history."""
    state = load_state()
    cycles = state["cycles"]

    if len(cycles) < 5:
        print(json.dumps({"status": "insufficient_data", "cycles": len(cycles)}))
        return

    # Analyze success patterns by strategy
    strategy_performance = {}
    for c in cycles:
        sid = c["strategy"]
        if sid not in strategy_performance:
            strategy_performance[sid] = {"kept": 0, "reverted": 0, "deltas": []}
        if c["kept"]:
            strategy_performance[sid]["kept"] += 1
        else:
            strategy_performance[sid]["reverted"] += 1
        strategy_performance[sid]["deltas"].append(c["delta"])

    # Find streaks
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

    # Action word frequency in successes vs failures
    success_actions = " ".join(c["action"] for c in cycles if c["kept"]).lower().split()
    failure_actions = " ".join(c["action"] for c in cycles if not c["kept"]).lower().split()
    success_words = Counter(success_actions).most_common(10)
    failure_words = Counter(failure_actions).most_common(10)

    # Fitness trajectory shape
    history = state["fitness_history"]
    early = history[:len(history)//3] if len(history) >= 3 else history
    mid = history[len(history)//3:2*len(history)//3] if len(history) >= 3 else []
    late = history[2*len(history)//3:] if len(history) >= 3 else []

    trajectory = "unknown"
    if early and late:
        early_avg = sum(early) / len(early)
        late_avg = sum(late) / len(late)
        if late_avg > early_avg + 0.1:
            trajectory = "improving"
        elif late_avg < early_avg - 0.05:
            trajectory = "declining"
        elif mid:
            mid_avg = sum(mid) / len(mid)
            if mid_avg > early_avg and late_avg < mid_avg:
                trajectory = "peaked_then_declined"
            else:
                trajectory = "plateau"
        else:
            trajectory = "flat"

    print(json.dumps({
        "strategy_performance": strategy_performance,
        "max_success_streak": max_success_streak,
        "max_failure_streak": max_failure_streak,
        "trajectory": trajectory,
        "success_keywords": success_words,
        "failure_keywords": failure_words,
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

    # 2. Single-species population (no diversity)
    if len(strategies) > 0:
        approaches = set(s["approach"][:50] for s in strategies)  # rough dedup
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

    # 4. Graveyard patterns — same failure mode repeating
    if len(graveyard) >= 3:
        reasons = Counter(s.get("extinction_reason", "unknown") for s in graveyard)
        repeated = [(r, c) for r, c in reasons.most_common() if c >= 2]
        if repeated:
            blind_spots.append({
                "type": "repeated_failures",
                "severity": "MEDIUM",
                "detail": f"Same failure patterns recurring: {repeated}",
            })

    # 5. Fitness function might be wrong
    if len(cycles) > 15:
        recent_fitness = [c["fitness"] for c in cycles[-5:]]
        if all(f > 0.9 for f in recent_fitness) and state["fitness"] < 1.0:
            blind_spots.append({
                "type": "fitness_ceiling",
                "severity": "LOW",
                "detail": "Fitness consistently >0.9 but goal not achieved — fitness function may not capture remaining work",
            })

    print(json.dumps({"blind_spots": blind_spots}, indent=2))


def cmd_velocity():
    """Measure learning velocity — how fast is fitness improving?"""
    state = load_state()
    history = state["fitness_history"]

    if len(history) < 2:
        print(json.dumps({"velocity": 0, "status": "insufficient_data"}))
        return

    # Calculate velocity in windows of 5
    windows = []
    for i in range(0, len(history) - 4, 5):
        window = history[i:i+5]
        velocity = (window[-1] - window[0]) / len(window)
        windows.append({
            "cycles": f"{i+1}-{i+5}",
            "start_fitness": round(window[0], 4),
            "end_fitness": round(window[-1], 4),
            "velocity": round(velocity, 4),
        })

    # Overall velocity
    overall = (history[-1] - history[0]) / len(history)

    # Acceleration (is velocity increasing or decreasing?)
    acceleration = 0
    if len(windows) >= 2:
        acceleration = windows[-1]["velocity"] - windows[-2]["velocity"]

    # Estimated cycles to completion
    if overall > 0:
        remaining_fitness = 1.0 - state["fitness"]
        estimated_cycles = remaining_fitness / overall
    else:
        estimated_cycles = float("inf")

    print(json.dumps({
        "overall_velocity": round(overall, 4),
        "acceleration": round(acceleration, 4),
        "current_fitness": state["fitness"],
        "windows": windows,
        "estimated_cycles_remaining": round(estimated_cycles, 1) if estimated_cycles != float("inf") else "infinite",
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
    lineages = Counter(s.get("parent", "genesis") for s in strategies)

    # Fitness distribution
    fitnesses = [s["fitness"] for s in strategies]
    fitness_mean = sum(fitnesses) / len(fitnesses)
    fitness_variance = sum((f - fitness_mean) ** 2 for f in fitnesses) / len(fitnesses)

    # Diversity score: higher is more diverse
    n_strategies = len(strategies)
    n_lineages = len(lineages)
    diversity = n_lineages / max(n_strategies, 1)

    print(json.dumps({
        "diversity_score": round(diversity, 3),
        "total_strategies": n_strategies,
        "unique_lineages": n_lineages,
        "generations": dict(generations),
        "fitness_mean": round(fitness_mean, 4),
        "fitness_variance": round(fitness_variance, 4),
        "graveyard_size": len(state["graveyard"]),
        "recommendation": "ADD_DIVERSITY" if diversity < 0.3 else "HEALTHY",
    }, indent=2))


def cmd_recommend():
    """Generate strategic recommendations based on current state."""
    state = load_state()
    recommendations = []
    priority = 0

    # Phase-based recommendations
    phase = state["phase"]
    if phase == "GENESIS":
        recommendations.append({
            "priority": 1,
            "action": "Focus on testing diverse strategies quickly",
            "reason": "Early phase — explore broadly before exploiting",
        })
    elif phase == "PLATEAU":
        priority += 1
        recommendations.append({
            "priority": priority,
            "action": "PIVOT: Try fundamentally different approach",
            "reason": f"Fitness stagnant at {state['fitness']:.3f}",
        })
        recommendations.append({
            "priority": priority + 1,
            "action": "Check graveyard for strategies worth resurrecting",
            "reason": "Context may have changed since they failed",
        })
        recommendations.append({
            "priority": priority + 2,
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

    # Diversity-based recommendations
    active = [s for s in state["strategies"] if s["status"] != "EXTINCT"]
    if len(active) < 3:
        recommendations.append({
            "priority": 2,
            "action": "Generate more strategies — population too small",
            "reason": f"Only {len(active)} active strategies",
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
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
