#!/usr/bin/env python3
"""
EVOLUTION STATE ENGINE — Persistent state management with JSON backing.

Manages the evolution state machine: strategies, fitness history, cycle tracking,
and memory crystallization. This is the computational backbone that makes
Evolution a real system, not just prompts.

Usage:
    python engine/state.py init <goal>           Initialize a new evolution
    python engine/state.py cycle <action> <result> Log a cycle outcome
    python engine/state.py select                 Select next strategy (Thompson Sampling)
    python engine/state.py fitness                Show current fitness
    python engine/state.py status                 Show evolution dashboard
    python engine/state.py plateau                Check for stagnation
    python engine/state.py crystallize            Crystallize learnings into principles
"""

import json
import os
import sys
import math
import random
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path("evolution/.state")
STATE_FILE = STATE_DIR / "evolution.json"


def default_state(goal: str) -> dict:
    """Create a fresh evolution state."""
    return {
        "version": 1,
        "goal": goal,
        "created": now(),
        "cycle": 0,
        "phase": "GENESIS",
        "fitness": 0.0,
        "fitness_history": [],
        "exploration_rate": 0.30,
        "consecutive_failures": 0,
        "consecutive_successes": 0,
        "strategies": [],
        "graveyard": [],
        "hall_of_fame": [],
        "cycles": [],
        "principles": [],
        "recipes": [],
        "episodes": [],
        "hypotheses": [],
        "blind_spots": [],
        "meta_patterns": [],
        "sub_goals": [],
        "success_criteria": [],
    }


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict:
    """Load state from JSON file."""
    if not STATE_FILE.exists():
        print("ERROR: No evolution state found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state: dict):
    """Save state to JSON file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


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
        print(json.dumps({"error": "No strategies available"}))
        return

    exploration_rate = state["exploration_rate"]

    # Thompson Sampling: for each strategy, sample from Beta distribution
    # based on successes and failures
    scores = []
    for s in strategies:
        alpha = s["successes"] + 1  # prior: 1 success
        beta = (s["attempts"] - s["successes"]) + 1  # prior: 1 failure
        # Sample from Beta(alpha, beta) — this naturally balances explore/exploit
        sample = random.betavariate(alpha, beta)
        scores.append((sample, s))

    # Sort by sampled score (highest first)
    scores.sort(key=lambda x: x[0], reverse=True)

    # With exploration_rate probability, pick randomly instead
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
        "exploration_rate": exploration_rate,
    }))


def cmd_cycle(strategy_id: str, action: str, tests_passing: int,
              tests_total: int, fitness: float, kept: bool):
    """Log a completed cycle."""
    state = load_state()
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
            break

    # Track consecutive outcomes
    if kept:
        state["consecutive_successes"] += 1
        state["consecutive_failures"] = 0
    else:
        state["consecutive_failures"] += 1
        state["consecutive_successes"] = 0

    # Decay exploration rate
    state["exploration_rate"] = max(0.10, state["exploration_rate"] * 0.95)

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
        "surprise": abs(delta) > 0.1,
        "timestamp": now(),
    })

    save_state(state)
    print(json.dumps(cycle_log))


def detect_phase(state: dict) -> str:
    """Detect which evolutionary phase we're in."""
    cycle = state["cycle"]
    history = state["fitness_history"]

    if cycle <= 3:
        return "GENESIS"

    # Check for plateau (last 5 cycles, fitness change < 0.02)
    if len(history) >= 5:
        recent = history[-5:]
        if max(recent) - min(recent) < 0.02:
            return "PLATEAU"

    # Check for breakthrough (sudden jump > 0.15)
    if len(history) >= 2 and history[-1] - history[-2] > 0.15:
        return "BREAKTHROUGH"

    # Check for maturity (fitness > 0.85)
    if state["fitness"] > 0.85:
        return "MATURITY"

    return "GROWTH"


def cmd_plateau():
    """Check if evolution is stagnating and recommend action."""
    state = load_state()
    history = state["fitness_history"]

    if len(history) < 5:
        print(json.dumps({"stagnating": False, "reason": "Not enough data"}))
        return

    recent = history[-5:]
    variance = max(recent) - min(recent)
    stagnating = variance < 0.02

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
        alternating = all(outcomes[i] != outcomes[i+1] for i in range(len(outcomes)-1))
        if alternating:
            recommendations.insert(0, "OSCILLATION DETECTED: You're flip-flopping. Try a fundamentally different approach.")

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
            break
    save_state(state)
    print(json.dumps({"status": "extinct", "strategy": strategy_id, "reason": reason}))


def cmd_mutate(parent_id: str, name: str, approach: str):
    """Create a mutated child strategy from a parent."""
    state = load_state()
    parent = next((s for s in state["strategies"] if s["id"] == parent_id), None)
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


def cmd_crystallize():
    """Crystallize learnings: extract principles from episodes."""
    state = load_state()
    episodes = state["episodes"]

    if len(episodes) < 5:
        print(json.dumps({"status": "not_enough_data", "episodes": len(episodes)}))
        return

    # Find patterns in successful episodes
    successes = [e for e in episodes if e["outcome"] == "KEPT"]
    failures = [e for e in episodes if e["outcome"] == "REVERTED"]

    # Count action keywords in successes vs failures
    success_words = {}
    failure_words = {}
    for e in successes:
        for word in e["action"].lower().split():
            success_words[word] = success_words.get(word, 0) + 1
    for e in failures:
        for word in e["action"].lower().split():
            failure_words[word] = failure_words.get(word, 0) + 1

    print(json.dumps({
        "status": "crystallized",
        "total_episodes": len(episodes),
        "successes": len(successes),
        "failures": len(failures),
        "success_rate": round(len(successes) / max(len(episodes), 1), 2),
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

    # Fitness trend
    history = state["fitness_history"]
    trend = "—"
    if len(history) >= 3:
        recent_avg = sum(history[-3:]) / 3
        older_avg = sum(history[-6:-3]) / 3 if len(history) >= 6 else sum(history[:3]) / max(len(history[:3]), 1)
        if recent_avg > older_avg + 0.02:
            trend = "IMPROVING"
        elif recent_avg < older_avg - 0.02:
            trend = "DECLINING"
        else:
            trend = "STABLE"

    dashboard = {
        "goal": state["goal"],
        "phase": state["phase"],
        "cycle": total_cycles,
        "fitness": state["fitness"],
        "trend": trend,
        "success_rate": success_rate,
        "active_strategies": len(active_strategies),
        "graveyard_size": len(state["graveyard"]),
        "best_strategy": {"id": best["id"], "name": best["name"], "fitness": best["fitness"]} if best else None,
        "exploration_rate": round(state["exploration_rate"], 3),
        "episodes": len(state["episodes"]),
        "principles": len(state["principles"]),
        "recipes": len(state["recipes"]),
        "consecutive_failures": state["consecutive_failures"],
    }
    print(json.dumps(dashboard, indent=2))


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        cmd_init(sys.argv[2] if len(sys.argv) > 2 else "No goal specified")
    elif cmd == "add-strategy":
        cmd_add_strategy(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    elif cmd == "select":
        cmd_select()
    elif cmd == "cycle":
        # cycle <strategy_id> <action> <tests_passing> <tests_total> <fitness> <kept>
        cmd_cycle(sys.argv[2], sys.argv[3], int(sys.argv[4]),
                  int(sys.argv[5]), float(sys.argv[6]), sys.argv[7].lower() == "true")
    elif cmd == "plateau":
        cmd_plateau()
    elif cmd == "extinct":
        cmd_extinct(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "low fitness")
    elif cmd == "mutate":
        cmd_mutate(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    elif cmd == "crystallize":
        cmd_crystallize()
    elif cmd == "status":
        cmd_status()
    elif cmd == "fitness":
        state = load_state()
        print(json.dumps({"fitness": state["fitness"], "history": state["fitness_history"][-20:]}))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
