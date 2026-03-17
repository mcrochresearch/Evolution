#!/usr/bin/env python3
"""
EVOLUTION STATE ENGINE — Persistent state management with JSON backing.

Manages the evolution state machine: strategies, fitness history, cycle tracking,
population management, and memory crystallization. This is the computational
backbone that makes Evolution a real system, not just prompts.

Usage:
    python engine/state.py init <goal>           Initialize a new evolution
    python engine/state.py cycle <strategy_id> <action> <tests_pass> <tests_total> <fitness> <kept>
    python engine/state.py select                Select next strategy (Thompson Sampling)
    python engine/state.py add-strategy <name> <approach> [hypothesis]
    python engine/state.py extinct <strategy_id> [reason]
    python engine/state.py mutate <parent_id> <name> [approach]
    python engine/state.py crossover <id1> <id2> <name>  Combine two strategies
    python engine/state.py cull [max_pop]        Remove lowest-fitness strategies
    python engine/state.py status                Show evolution dashboard
    python engine/state.py plateau               Check for stagnation
    python engine/state.py crystallize           Crystallize learnings into principles
    python engine/state.py reset                 Clear all state
    python engine/state.py export                Dump state to stdout
    python engine/state.py import                Load state from stdin
"""

import json
import os
import sys
import math
import random
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path("evolution/.state")
STATE_FILE = STATE_DIR / "evolution.json"

# --- Named Constants ---
# Phase detection thresholds (documented rationale)
GENESIS_CYCLES = 3                  # Minimum cycles before phase detection kicks in
PLATEAU_WINDOW = 5                  # Cycles to check for stagnation
PLATEAU_VARIANCE = 0.02             # Max fitness variance to consider plateau
BREAKTHROUGH_JUMP = 0.15            # Min single-cycle jump for breakthrough
MATURITY_THRESHOLD = 0.85           # Fitness above this = near completion
EXPLORATION_DECAY = 0.95            # Per-cycle decay multiplier for exploration rate
EXPLORATION_FLOOR = 0.10            # Never go below this exploration rate
DEFAULT_EXPLORATION = 0.30          # Starting exploration rate
MAX_POPULATION = 8                  # Auto-cull when population exceeds this
SURPRISE_THRESHOLD = 0.10           # Delta above this is "surprising"


def default_state(goal: str) -> dict:
    """Create a fresh evolution state."""
    return {
        "version": 2,
        "goal": goal,
        "created": now(),
        "cycle": 0,
        "phase": "GENESIS",
        "fitness": 0.0,
        "fitness_history": [],
        "exploration_rate": DEFAULT_EXPLORATION,
        "consecutive_failures": 0,
        "consecutive_successes": 0,
        "strategies": [],
        "graveyard": [],
        "hall_of_fame": [],
        "cycles": [],
        "principles": [],
        "episodes": [],
        "sub_goals": [],
        "success_criteria": [],
    }


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict:
    """Load state from JSON file."""
    if not STATE_FILE.exists():
        print(json.dumps({"error": "No evolution state found. Run 'init' first."}))
        sys.exit(1)
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state: dict):
    """Atomically save state to JSON file (write-to-temp-then-rename)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Write to temp file first, then rename for atomicity
    fd, tmp_path = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, STATE_FILE)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ============================================================================
# VALIDATION
# ============================================================================

def validate_fitness(value: float, name: str = "fitness") -> float:
    """Ensure fitness is within [0.0, 1.0]."""
    if not (0.0 <= value <= 1.0):
        print(json.dumps({"error": f"{name} must be between 0.0 and 1.0, got {value}"}))
        sys.exit(1)
    return value


def validate_tests(passing: int, total: int) -> tuple:
    """Ensure test counts are valid."""
    if passing < 0 or total < 0:
        print(json.dumps({"error": f"Test counts cannot be negative: {passing}/{total}"}))
        sys.exit(1)
    if passing > total:
        print(json.dumps({"error": f"tests_passing ({passing}) > tests_total ({total})"}))
        sys.exit(1)
    return passing, total


def validate_strategy_id(state: dict, sid: str, include_graveyard: bool = False) -> dict:
    """Find and return a strategy by ID, or exit with error."""
    for s in state["strategies"]:
        if s["id"] == sid:
            return s
    if include_graveyard:
        for s in state["graveyard"]:
            if s["id"] == sid:
                return s
    print(json.dumps({"error": f"Strategy {sid} not found"}))
    sys.exit(1)


def safe_int(val: str, name: str) -> int:
    """Parse integer with error handling."""
    try:
        return int(val)
    except (ValueError, TypeError):
        print(json.dumps({"error": f"Invalid integer for {name}: {val}"}))
        sys.exit(1)


def safe_float(val: str, name: str) -> float:
    """Parse float with error handling."""
    try:
        return float(val)
    except (ValueError, TypeError):
        print(json.dumps({"error": f"Invalid number for {name}: {val}"}))
        sys.exit(1)


# ============================================================================
# COMMANDS
# ============================================================================

def cmd_init(goal: str):
    """Initialize a new evolution."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = default_state(goal)
    save_state(state)
    print(json.dumps({"status": "initialized", "goal": goal}))


def cmd_add_strategy(name: str, approach: str, hypothesis: str):
    """Add a new strategy to the population."""
    state = load_state()
    sid = f"S{len(state['strategies']) + len(state['graveyard']) + 1:03d}"
    strategy = {
        "id": sid,
        "name": name,
        "approach": approach,
        "hypothesis": hypothesis,
        "fitness": 0.0,
        "attempts": 0,
        "successes": 0,
        "generation": 1,
        "created": now(),
        "parent": None,
        "status": "CANDIDATE",
    }
    state["strategies"].append(strategy)
    save_state(state)
    print(json.dumps({"status": "added", "strategy": strategy}))


def cmd_select():
    """Select next strategy using Thompson Sampling."""
    state = load_state()
    strategies = [s for s in state["strategies"] if s["status"] != "EXTINCT"]

    if not strategies:
        print(json.dumps({"error": "No strategies available. Add strategies first."}))
        return

    exploration_rate = state["exploration_rate"]

    # Thompson Sampling: for each strategy, sample from Beta distribution
    # based on successes and failures. Beta(alpha, beta) naturally balances
    # exploration (uncertain strategies get wider distributions) vs
    # exploitation (proven strategies cluster near their true success rate).
    scores = []
    for s in strategies:
        alpha = s["successes"] + 1   # +1 prior (optimistic)
        beta_param = (s["attempts"] - s["successes"]) + 1  # +1 prior
        sample = random.betavariate(alpha, beta_param)
        scores.append((sample, s))

    scores.sort(key=lambda x: x[0], reverse=True)

    # With exploration_rate probability, pick randomly instead.
    # This provides an additional exploration mechanism on top of
    # Thompson Sampling's natural exploration.
    if random.random() < exploration_rate:
        selected = random.choice(strategies)
        method = "exploration"
    else:
        selected = scores[0][1]
        method = "exploitation"

    print(json.dumps({
        "selected": selected["id"],
        "name": selected["name"],
        "method": method,
        "fitness": selected["fitness"],
        "attempts": selected["attempts"],
        "exploration_rate": round(exploration_rate, 3),
        "population_size": len(strategies),
    }))


def cmd_cycle(strategy_id: str, action: str, tests_passing: int,
              tests_total: int, fitness: float, kept: bool):
    """Log a completed cycle with full validation."""
    state = load_state()

    # Validate inputs
    validate_fitness(fitness)
    validate_tests(tests_passing, tests_total)
    validate_strategy_id(state, strategy_id)

    state["cycle"] += 1
    cycle_num = state["cycle"]

    prev_fitness = state["fitness"]
    delta = fitness - prev_fitness
    state["fitness"] = fitness
    state["fitness_history"].append(fitness)

    # Update strategy stats
    for s in state["strategies"]:
        if s["id"] == strategy_id:
            s["attempts"] += 1
            if kept:
                s["successes"] += 1
                s["fitness"] = max(s["fitness"], fitness)
            s["status"] = "PROVEN" if s["successes"] >= 2 else s["status"]
            break

    # Track consecutive outcomes
    if kept:
        state["consecutive_successes"] += 1
        state["consecutive_failures"] = 0
    else:
        state["consecutive_failures"] += 1
        state["consecutive_successes"] = 0

    # Decay exploration rate (multiplicative decay with floor)
    state["exploration_rate"] = max(
        EXPLORATION_FLOOR,
        state["exploration_rate"] * EXPLORATION_DECAY
    )

    # Boost exploration on consecutive failures (adaptive)
    if state["consecutive_failures"] >= 3:
        state["exploration_rate"] = min(0.50, state["exploration_rate"] + 0.05)

    # Detect phase transitions
    state["phase"] = detect_phase(state)

    # Log cycle
    cycle_log = {
        "cycle": cycle_num,
        "strategy": strategy_id,
        "action": action,
        "tests_passing": tests_passing,
        "tests_total": tests_total,
        "fitness": fitness,
        "delta": round(delta, 4),
        "kept": kept,
        "timestamp": now(),
    }
    state["cycles"].append(cycle_log)

    # Log episode
    state["episodes"].append({
        "cycle": cycle_num,
        "action": action,
        "outcome": "KEPT" if kept else "REVERTED",
        "fitness": fitness,
        "surprise": abs(delta) > SURPRISE_THRESHOLD,
        "timestamp": now(),
    })

    save_state(state)
    print(json.dumps(cycle_log))


def detect_phase(state: dict) -> str:
    """Detect which evolutionary phase we're in.

    Phases:
    - GENESIS:       First few cycles, establishing baseline
    - GROWTH:        Fitness is trending upward
    - PLATEAU:       Fitness stagnant for PLATEAU_WINDOW cycles
    - BREAKTHROUGH:  Sudden large fitness improvement
    - MATURITY:      High fitness, nearing goal completion
    """
    cycle = state["cycle"]
    history = state["fitness_history"]

    if cycle <= GENESIS_CYCLES:
        return "GENESIS"

    # Check for breakthrough (sudden jump)
    if len(history) >= 2 and history[-1] - history[-2] > BREAKTHROUGH_JUMP:
        return "BREAKTHROUGH"

    # Check for maturity (high fitness)
    if state["fitness"] > MATURITY_THRESHOLD:
        return "MATURITY"

    # Check for plateau (low variance in recent window)
    if len(history) >= PLATEAU_WINDOW:
        recent = history[-PLATEAU_WINDOW:]
        if max(recent) - min(recent) < PLATEAU_VARIANCE:
            return "PLATEAU"

    return "GROWTH"


def cmd_plateau():
    """Check if evolution is stagnating and recommend action."""
    state = load_state()
    history = state["fitness_history"]

    if len(history) < PLATEAU_WINDOW:
        print(json.dumps({"stagnating": False, "reason": "Not enough data"}))
        return

    recent = history[-PLATEAU_WINDOW:]
    variance = max(recent) - min(recent)
    stagnating = variance < PLATEAU_VARIANCE

    recommendations = []
    if stagnating:
        recommendations = [
            "Increase exploration rate to 0.50",
            "Check graveyard for strategies worth resurrecting",
            "Try the OPPOSITE of your current approach",
            "Decompose the current sub-goal into smaller pieces",
            "Search for external information (docs, web, similar projects)",
            "Create a completely new strategy species",
        ]

    # Check for oscillation (alternating keep/revert)
    recent_cycles = state["cycles"][-6:]
    if len(recent_cycles) >= 6:
        outcomes = [c["kept"] for c in recent_cycles]
        alternating = all(outcomes[i] != outcomes[i + 1] for i in range(len(outcomes) - 1))
        if alternating:
            recommendations.insert(
                0, "OSCILLATION DETECTED: You're flip-flopping. "
                   "Try a fundamentally different approach.")

    # Check for declining trend
    if len(history) >= 10:
        first_half = history[-10:-5]
        second_half = history[-5:]
        if sum(second_half) / 5 < sum(first_half) / 5 - 0.02:
            recommendations.insert(0, "DECLINING FITNESS: Recent changes are making things worse. Revert to best known state.")

    print(json.dumps({
        "stagnating": stagnating,
        "variance": round(variance, 4),
        "consecutive_failures": state["consecutive_failures"],
        "phase": state["phase"],
        "recommendations": recommendations,
    }))


def cmd_extinct(strategy_id: str, reason: str):
    """Move a strategy to the graveyard."""
    state = load_state()
    for i, s in enumerate(state["strategies"]):
        if s["id"] == strategy_id:
            s["status"] = "EXTINCT"
            s["extinction_reason"] = reason
            s["extinct_at"] = now()
            state["graveyard"].append(state["strategies"].pop(i))
            save_state(state)
            print(json.dumps({"status": "extinct", "strategy": strategy_id, "reason": reason}))
            return
    print(json.dumps({"error": f"Strategy {strategy_id} not found in active population"}))


def cmd_mutate(parent_id: str, name: str, approach: str):
    """Create a mutated child strategy from a parent."""
    state = load_state()
    parent = None
    for s in state["strategies"]:
        if s["id"] == parent_id:
            parent = s
            break
    if not parent:
        print(json.dumps({"error": f"Strategy {parent_id} not found"}))
        return

    sid = f"S{len(state['strategies']) + len(state['graveyard']) + 1:03d}"
    child = {
        "id": sid,
        "name": name,
        "approach": approach,
        "hypothesis": f"Mutation of {parent_id}: {parent['name']}",
        "fitness": 0.0,
        "attempts": 0,
        "successes": 0,
        "generation": parent["generation"] + 1,
        "created": now(),
        "parent": parent_id,
        "status": "CANDIDATE",
    }
    state["strategies"].append(child)
    save_state(state)
    print(json.dumps({"status": "mutated", "parent": parent_id, "child": child}))


def cmd_crossover(id1: str, id2: str, name: str):
    """Create a new strategy by combining two parent strategies."""
    state = load_state()
    parent1 = None
    parent2 = None
    for s in state["strategies"]:
        if s["id"] == id1:
            parent1 = s
        if s["id"] == id2:
            parent2 = s
    if not parent1 or not parent2:
        missing = id1 if not parent1 else id2
        print(json.dumps({"error": f"Strategy {missing} not found"}))
        return

    sid = f"S{len(state['strategies']) + len(state['graveyard']) + 1:03d}"
    child = {
        "id": sid,
        "name": name,
        "approach": f"Crossover of [{parent1['name']}] × [{parent2['name']}]",
        "hypothesis": f"Combining successful elements of {id1} and {id2}",
        "fitness": 0.0,
        "attempts": 0,
        "successes": 0,
        "generation": max(parent1["generation"], parent2["generation"]) + 1,
        "created": now(),
        "parent": f"{id1}×{id2}",
        "status": "CANDIDATE",
    }
    state["strategies"].append(child)
    save_state(state)
    print(json.dumps({"status": "crossover", "parents": [id1, id2], "child": child}))


def cmd_cull(max_pop: int = MAX_POPULATION):
    """Remove lowest-fitness strategies when population exceeds max."""
    state = load_state()
    active = [s for s in state["strategies"] if s["status"] != "EXTINCT"]

    if len(active) <= max_pop:
        print(json.dumps({
            "status": "no_cull_needed",
            "population": len(active),
            "max": max_pop
        }))
        return

    # Sort by fitness (ascending), cull the weakest
    active.sort(key=lambda s: s["fitness"])
    to_cull = len(active) - max_pop
    culled = []

    for s in active[:to_cull]:
        # Don't cull strategies that haven't been tested enough
        if s["attempts"] < 2:
            continue
        s["status"] = "EXTINCT"
        s["extinction_reason"] = f"Culled: fitness {s['fitness']:.3f}, population overflow"
        s["extinct_at"] = now()
        culled.append(s["id"])
        state["strategies"].remove(s)
        state["graveyard"].append(s)

    save_state(state)
    print(json.dumps({
        "status": "culled",
        "removed": culled,
        "population": len([s for s in state["strategies"] if s["status"] != "EXTINCT"]),
    }))


def cmd_resurrect(strategy_id: str):
    """Resurrect a strategy from the graveyard back into active population."""
    state = load_state()
    for i, s in enumerate(state["graveyard"]):
        if s["id"] == strategy_id:
            s["status"] = "CANDIDATE"
            s["resurrection_reason"] = "Manually resurrected — context may have changed"
            s["resurrected_at"] = now()
            # Reset stats for fresh start
            s["attempts"] = 0
            s["successes"] = 0
            s["fitness"] = 0.0
            state["strategies"].append(state["graveyard"].pop(i))
            save_state(state)
            print(json.dumps({"status": "resurrected", "strategy": strategy_id}))
            return
    print(json.dumps({"error": f"Strategy {strategy_id} not found in graveyard"}))


def cmd_crystallize():
    """Crystallize learnings: extract causal principles from episodes."""
    state = load_state()
    episodes = state["episodes"]
    cycles = state["cycles"]

    if len(episodes) < 5:
        print(json.dumps({"status": "not_enough_data", "episodes": len(episodes)}))
        return

    successes = [e for e in episodes if e["outcome"] == "KEPT"]
    failures = [e for e in episodes if e["outcome"] == "REVERTED"]

    # Count action keywords in successes vs failures
    success_words = {}
    failure_words = {}
    for e in successes:
        for word in e["action"].lower().split():
            if len(word) > 3:  # Skip short words
                success_words[word] = success_words.get(word, 0) + 1
    for e in failures:
        for word in e["action"].lower().split():
            if len(word) > 3:
                failure_words[word] = failure_words.get(word, 0) + 1

    # Find strategy-outcome correlations (causal analysis)
    strategy_outcomes = {}
    for c in cycles:
        sid = c["strategy"]
        if sid not in strategy_outcomes:
            strategy_outcomes[sid] = {"kept": 0, "reverted": 0, "avg_delta": []}
        if c["kept"]:
            strategy_outcomes[sid]["kept"] += 1
        else:
            strategy_outcomes[sid]["reverted"] += 1
        strategy_outcomes[sid]["avg_delta"].append(c["delta"])

    for sid, data in strategy_outcomes.items():
        deltas = data["avg_delta"]
        data["avg_delta"] = round(sum(deltas) / len(deltas), 4) if deltas else 0
        total = data["kept"] + data["reverted"]
        data["success_rate"] = round(data["kept"] / total, 2) if total else 0

    # Extract principles from high-confidence patterns
    new_principles = []
    for sid, data in strategy_outcomes.items():
        total = data["kept"] + data["reverted"]
        if total >= 3 and data["success_rate"] >= 0.7:
            strat = next((s for s in state["strategies"] if s["id"] == sid), None)
            if strat:
                new_principles.append({
                    "source": sid,
                    "principle": f"Strategy '{strat['name']}' works reliably ({data['success_rate']*100:.0f}% over {total} attempts)",
                    "confidence": round(min(0.95, 0.5 + total * 0.05), 2),
                    "extracted_at": now(),
                })
        elif total >= 3 and data["success_rate"] <= 0.3:
            strat = next((s for s in state["strategies"] if s["id"] == sid),
                         next((s for s in state["graveyard"] if s["id"] == sid), None))
            if strat:
                new_principles.append({
                    "source": sid,
                    "principle": f"Strategy '{strat['name']}' is unreliable ({data['success_rate']*100:.0f}% over {total} attempts) — avoid",
                    "confidence": round(min(0.95, 0.5 + total * 0.05), 2),
                    "extracted_at": now(),
                })

    state["principles"].extend(new_principles)
    save_state(state)

    print(json.dumps({
        "status": "crystallized",
        "total_episodes": len(episodes),
        "successes": len(successes),
        "failures": len(failures),
        "success_rate": round(len(successes) / max(len(episodes), 1), 2),
        "strategy_correlations": strategy_outcomes,
        "new_principles": new_principles,
        "total_principles": len(state["principles"]),
        "success_keywords": dict(sorted(success_words.items(), key=lambda x: -x[1])[:10]),
        "failure_keywords": dict(sorted(failure_words.items(), key=lambda x: -x[1])[:10]),
        "timestamp": now(),
    }))


def cmd_status():
    """Show evolution dashboard."""
    state = load_state()
    active_strategies = [s for s in state["strategies"] if s["status"] != "EXTINCT"]
    best = max(active_strategies, key=lambda s: s["fitness"]) if active_strategies else None

    total_cycles = state["cycle"]
    kept = sum(1 for c in state["cycles"] if c.get("kept"))
    success_rate = round(kept / max(total_cycles, 1), 2)

    # Fitness trend (using confidence threshold)
    history = state["fitness_history"]
    trend = "—"
    if len(history) >= 3:
        recent_avg = sum(history[-3:]) / 3
        older_avg = sum(history[-6:-3]) / 3 if len(history) >= 6 else sum(history[:3]) / max(len(history[:3]), 1)
        diff = recent_avg - older_avg
        if diff > PLATEAU_VARIANCE:
            trend = "IMPROVING"
        elif diff < -PLATEAU_VARIANCE:
            trend = "DECLINING"
        else:
            trend = "STABLE"

    dashboard = {
        "goal": state["goal"],
        "phase": state["phase"],
        "cycle": total_cycles,
        "fitness": round(state["fitness"], 4),
        "trend": trend,
        "success_rate": success_rate,
        "active_strategies": len(active_strategies),
        "graveyard_size": len(state["graveyard"]),
        "best_strategy": {
            "id": best["id"], "name": best["name"], "fitness": best["fitness"]
        } if best else None,
        "exploration_rate": round(state["exploration_rate"], 3),
        "episodes": len(state["episodes"]),
        "principles": len(state["principles"]),
        "consecutive_failures": state["consecutive_failures"],
    }
    print(json.dumps(dashboard, indent=2))


def cmd_reset():
    """Clear all evolution state. Destructive — requires confirmation."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    checkpoints = STATE_DIR / "checkpoints.jsonl"
    if checkpoints.exists():
        checkpoints.unlink()
    skill_reg = STATE_DIR / "skill-registry.json"
    if skill_reg.exists():
        skill_reg.unlink()
    print(json.dumps({"status": "reset", "message": "All state cleared"}))


def cmd_export():
    """Export full state as JSON to stdout for backup."""
    state = load_state()
    print(json.dumps(state, indent=2))


def cmd_import():
    """Import state from stdin."""
    try:
        data = json.load(sys.stdin)
        if "goal" not in data or "cycle" not in data:
            print(json.dumps({"error": "Invalid state: missing required fields"}))
            sys.exit(1)
        save_state(data)
        print(json.dumps({"status": "imported", "goal": data["goal"], "cycle": data["cycle"]}))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    try:
        if cmd == "init":
            cmd_init(sys.argv[2] if len(sys.argv) > 2 else "No goal specified")
        elif cmd == "add-strategy":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: add-strategy <name> <approach> [hypothesis]"}))
                sys.exit(1)
            cmd_add_strategy(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
        elif cmd == "select":
            cmd_select()
        elif cmd == "cycle":
            if len(sys.argv) < 8:
                print(json.dumps({"error": "Usage: cycle <strategy_id> <action> <tests_passing> <tests_total> <fitness> <kept>"}))
                sys.exit(1)
            cmd_cycle(
                sys.argv[2],
                sys.argv[3],
                safe_int(sys.argv[4], "tests_passing"),
                safe_int(sys.argv[5], "tests_total"),
                validate_fitness(safe_float(sys.argv[6], "fitness")),
                sys.argv[7].lower() == "true"
            )
        elif cmd == "plateau":
            cmd_plateau()
        elif cmd == "extinct":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: extinct <strategy_id> [reason]"}))
                sys.exit(1)
            cmd_extinct(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "low fitness")
        elif cmd == "mutate":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: mutate <parent_id> <name> [approach]"}))
                sys.exit(1)
            cmd_mutate(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
        elif cmd == "crossover":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: crossover <id1> <id2> <name>"}))
                sys.exit(1)
            cmd_crossover(sys.argv[2], sys.argv[3], sys.argv[4])
        elif cmd == "cull":
            max_pop = safe_int(sys.argv[2], "max_pop") if len(sys.argv) > 2 else MAX_POPULATION
            cmd_cull(max_pop)
        elif cmd == "resurrect":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: resurrect <strategy_id>"}))
                sys.exit(1)
            cmd_resurrect(sys.argv[2])
        elif cmd == "crystallize":
            cmd_crystallize()
        elif cmd == "status":
            cmd_status()
        elif cmd == "fitness":
            state = load_state()
            print(json.dumps({"fitness": state["fitness"], "history": state["fitness_history"][-20:]}))
        elif cmd == "reset":
            cmd_reset()
        elif cmd == "export":
            cmd_export()
        elif cmd == "import":
            cmd_import()
        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)
    except IndexError:
        print(json.dumps({"error": f"Missing arguments for '{cmd}'. Run without args for usage."}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
