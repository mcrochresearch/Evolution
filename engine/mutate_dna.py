#!/usr/bin/env python3
"""
EVOLUTION MUTATE DNA — Mechanical Prompt DNA Mutation & Expression

The DNA is not decorative. It rewrites itself based on fitness data.

This module:
1. Reads current DNA from evolution/genome/prompt-dna.md
2. Analyzes recent cycle fitness to identify what parameters correlate with success
3. Mutates one parameter per generation (±20% or next enum value)
4. Tracks mutation history with fitness impact
5. Auto-reverts mutations that hurt fitness within 5 cycles
6. Expresses DNA as a system prompt fragment for injection
7. Integrates with language_gradients.py for backward-attributed mutation targeting
8. Integrates with prompt_breeding.py for evolutionary prompt population

Usage:
    python3 engine/mutate_dna.py mutate           # Mutate one parameter
    python3 engine/mutate_dna.py express           # Output system prompt fragment
    python3 engine/mutate_dna.py fitness           # Score current DNA vs recent cycles
    python3 engine/mutate_dna.py status            # Show current DNA + mutation history
    python3 engine/mutate_dna.py revert            # Revert last mutation
    python3 engine/mutate_dna.py gradient-mutate   # Mutate based on language gradient blame
    python3 engine/mutate_dna.py breed-express     # Express best prompt from breeding population
"""

import json
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENGINE_DIR = Path(__file__).parent
PROJECT_DIR = ENGINE_DIR.parent
DNA_FILE = PROJECT_DIR / "evolution" / "genome" / "prompt-dna.md"
STATE_DIR = PROJECT_DIR / "evolution" / ".state"
DNA_STATE = STATE_DIR / "dna_state.json"
CYCLE_LOG = PROJECT_DIR / "evolution" / "nucleus" / "cycle.md"

# DNA parameter definitions
DNA_PARAMS = {
    "reasoning_style": {
        "type": "enum",
        "values": ["cot", "tot", "hypothesis", "analogical"],
        "default": "cot",
    },
    "planning_depth": {
        "type": "int",
        "min": 1, "max": 5,
        "default": 3,
    },
    "reflection_depth": {
        "type": "int",
        "min": 1, "max": 3,
        "default": 2,
    },
    "risk_tolerance": {
        "type": "float",
        "min": 0.0, "max": 1.0,
        "default": 0.40,
    },
    "verification_rigor": {
        "type": "float",
        "min": 0.0, "max": 1.0,
        "default": 0.80,
    },
    "exploration_rate": {
        "type": "float",
        "min": 0.0, "max": 1.0,
        "default": 0.30,
    },
    "patience": {
        "type": "float",
        "min": 0.0, "max": 1.0,
        "default": 0.60,
    },
    "detail_orientation": {
        "type": "float",
        "min": 0.0, "max": 1.0,
        "default": 0.70,
    },
    "parallelism": {
        "type": "float",
        "min": 0.0, "max": 1.0,
        "default": 0.50,
    },
}


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Load DNA state from JSON."""
    if DNA_STATE.exists():
        with open(DNA_STATE) as f:
            return json.load(f)
    return {
        "generation": 1,
        "current_dna": {name: p["default"] for name, p in DNA_PARAMS.items()},
        "mutations": [],
        "pending_mutation": None,
        "pending_since_cycle": None,
        "fitness_at_mutation": None,
    }


def save_state(state: dict):
    """Save DNA state to JSON."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(DNA_STATE, "w") as f:
        json.dump(state, f, indent=2)


def parse_dna_from_markdown() -> dict:
    """Parse current DNA values from prompt-dna.md."""
    if not DNA_FILE.exists():
        return {name: p["default"] for name, p in DNA_PARAMS.items()}

    dna = {}
    with open(DNA_FILE) as f:
        content = f.read()

    # Parse the table
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("|") or "---" in line or "Parameter" in line:
            continue
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 2:
            param_name = parts[0].strip()
            value_str = parts[1].strip()

            if param_name in DNA_PARAMS:
                param_def = DNA_PARAMS[param_name]
                if param_def["type"] == "enum":
                    # Extract enum value (might be like "chain_of_thought" mapped to "cot")
                    for v in param_def["values"]:
                        if v in value_str.lower().replace("chain_of_thought", "cot") \
                                              .replace("tree_of_thought", "tot"):
                            dna[param_name] = v
                            break
                    else:
                        dna[param_name] = value_str
                elif param_def["type"] == "int":
                    try:
                        dna[param_name] = int(value_str)
                    except ValueError:
                        dna[param_name] = param_def["default"]
                elif param_def["type"] == "float":
                    try:
                        dna[param_name] = float(value_str)
                    except ValueError:
                        dna[param_name] = param_def["default"]

    # Fill defaults
    for name, p in DNA_PARAMS.items():
        if name not in dna:
            dna[name] = p["default"]

    return dna


def get_current_cycle() -> int:
    """Get current cycle number from cycle log."""
    if not CYCLE_LOG.exists():
        return 0
    with open(CYCLE_LOG) as f:
        lines = [l for l in f.readlines() if l.strip() and not l.startswith("#")]
    return len(lines)


def get_recent_fitness(n: int = 10) -> list:
    """Get last N fitness scores from state."""
    state_file = STATE_DIR / "state.json"
    if not state_file.exists():
        return []
    try:
        with open(state_file) as f:
            state = json.load(f)
        history = state.get("history", [])
        return [h.get("fitness", 0.0) for h in history[-n:]]
    except (json.JSONDecodeError, KeyError):
        return []


# ---------------------------------------------------------------------------
# Mutation Logic
# ---------------------------------------------------------------------------

def mutate_parameter(dna: dict, param_name: str = None) -> tuple:
    """
    Mutate one DNA parameter.

    Args:
        dna: Current DNA values
        param_name: Specific parameter to mutate (None = random)

    Returns:
        (param_name, old_value, new_value)
    """
    if param_name is None:
        param_name = random.choice(list(DNA_PARAMS.keys()))

    param_def = DNA_PARAMS[param_name]
    old_value = dna[param_name]

    if param_def["type"] == "enum":
        values = param_def["values"]
        current_idx = values.index(old_value) if old_value in values else 0
        # Move to adjacent value
        direction = random.choice([-1, 1])
        new_idx = max(0, min(len(values) - 1, current_idx + direction))
        if new_idx == current_idx:
            new_idx = (current_idx + 1) % len(values)
        new_value = values[new_idx]

    elif param_def["type"] == "int":
        delta = random.choice([-1, 1])
        new_value = max(param_def["min"], min(param_def["max"], old_value + delta))
        if new_value == old_value:
            new_value = old_value + (1 if old_value < param_def["max"] else -1)
            new_value = max(param_def["min"], min(param_def["max"], new_value))

    elif param_def["type"] == "float":
        # ±20% mutation
        magnitude = old_value * 0.2
        if magnitude < 0.05:
            magnitude = 0.05
        delta = random.uniform(-magnitude, magnitude)
        new_value = round(max(param_def["min"], min(param_def["max"], old_value + delta)), 2)
        if new_value == old_value:
            new_value = round(min(param_def["max"], old_value + 0.05), 2)

    return param_name, old_value, new_value


def should_revert(state: dict) -> bool:
    """Check if the pending mutation should be reverted based on fitness."""
    if not state.get("pending_mutation"):
        return False

    current_cycle = get_current_cycle()
    mutation_cycle = state.get("pending_since_cycle", 0)

    # Wait at least 5 cycles before evaluating
    if current_cycle - mutation_cycle < 5:
        return False

    # Compare fitness before and after mutation
    fitness_before = state.get("fitness_at_mutation", 0.0)
    recent = get_recent_fitness(5)
    if not recent:
        return False

    avg_recent = sum(recent) / len(recent)

    # Revert if fitness dropped >10%
    if fitness_before > 0 and avg_recent < fitness_before * 0.9:
        return True

    return False


def write_dna_to_markdown(dna: dict, generation: int, mutations: list):
    """Rewrite prompt-dna.md with current values."""
    mutation_rows = ""
    for m in mutations[-10:]:  # Last 10 mutations
        mutation_rows += (
            f"| {m['generation']} | {m['cycle']} | {m['param']} | "
            f"{m['old']} | {m['new']} | {m.get('fitness_impact', '—')} | "
            f"{'Yes' if m.get('kept', True) else 'REVERTED'} |\n"
        )
    if not mutation_rows:
        mutation_rows = "| — | — | — | — | — | — | — |\n"

    # Find optimal configs
    optimal = ""
    kept_mutations = [m for m in mutations if m.get("kept", True) and m.get("fitness_impact")]
    if kept_mutations:
        best = sorted(kept_mutations, key=lambda x: float(x.get("fitness_impact", "0").replace("+", "").replace("—", "0")), reverse=True)[:3]
        for b in best:
            optimal += f"- Gen {b['generation']}: {b['param']} → {b['new']} (fitness {b.get('fitness_impact', '?')})\n"
    else:
        optimal = "_No optimal configurations found yet. The DNA evolves through experience._\n"

    content = f"""# Prompt DNA — Reasoning Configuration

> The agent's cognitive parameters — how it thinks, plans, and reasons.
> These parameters evolve over time as the agent discovers what works best.
> **This file is mechanically maintained by engine/mutate_dna.py. Do not edit manually.**

## Current Genotype (Generation {generation})

| Parameter | Value | Range | Description |
|-----------|-------|-------|-------------|
| reasoning_style | {dna['reasoning_style']} | [cot, tot, hypothesis, analogical] | Primary reasoning approach |
| planning_depth | {dna['planning_depth']} | [1-5] | Goal decomposition depth |
| reflection_depth | {dna['reflection_depth']} | [1-3] | Post-action analysis thoroughness |
| risk_tolerance | {dna['risk_tolerance']:.2f} | [0.0-1.0] | Willingness to try radical approaches |
| verification_rigor | {dna['verification_rigor']:.2f} | [0.0-1.0] | Testing thoroughness |
| exploration_rate | {dna['exploration_rate']:.2f} | [0.0-1.0] | New strategy probability |
| patience | {dna['patience']:.2f} | [0.0-1.0] | Cycles before declaring plateau |
| detail_orientation | {dna['detail_orientation']:.2f} | [0.0-1.0] | Focus on edge cases vs happy path |
| parallelism | {dna['parallelism']:.2f} | [0.0-1.0] | Tendency to spawn subagents |

## Phenotype Expression

How DNA values manifest in behavior:

- **reasoning_style=cot**: Think step-by-step, sequential reasoning
- **reasoning_style=tot**: Generate multiple reasoning paths, evaluate each
- **reasoning_style=hypothesis**: Form hypothesis first, then test
- **reasoning_style=analogical**: Find similar solved problems, adapt solutions

- **planning_depth=1**: Flat task list, no hierarchy
- **planning_depth=5**: Deep goal tree with sub-sub-sub-goals

- **risk_tolerance < 0.3**: Conservative, stick to proven approaches
- **risk_tolerance > 0.7**: Radical, try untested approaches frequently

## Mutation History

| Gen | Cycle | Parameter | Old | New | Fitness Impact | Kept? |
|-----|-------|-----------|-----|-----|----------------|-------|
{mutation_rows}
## Optimal Configurations Discovered

{optimal}
---

## DNA Mutation Rules

1. Only mutate ONE parameter per generation
2. Mutation magnitude: ±20% of current value (or next enum value)
3. Always keep a copy of the pre-mutation DNA
4. Evaluate fitness over 5 cycles before deciding to keep mutation
5. If fitness drops >10%, immediately revert
"""

    DNA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DNA_FILE, "w") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# DNA Expression — Convert DNA to system prompt fragment
# ---------------------------------------------------------------------------

def express_dna(dna: dict) -> str:
    """
    Convert current DNA values into a behavioral system prompt fragment.
    This is the "ribosome" — it translates genotype into phenotype.
    """
    fragments = []

    # Reasoning style
    style_map = {
        "cot": "Think step-by-step. Break complex problems into sequential sub-steps.",
        "tot": "Generate 2-3 alternative approaches for each decision. Evaluate each. Pick the best.",
        "hypothesis": "Form a hypothesis FIRST. Then design a minimal experiment to test it. Let data decide.",
        "analogical": "Before building, search for similar solved problems. Adapt existing solutions.",
    }
    fragments.append(style_map.get(dna["reasoning_style"], style_map["cot"]))

    # Planning depth
    depth = dna["planning_depth"]
    if depth <= 2:
        fragments.append("Keep plans flat. One level of sub-tasks. Execute immediately.")
    elif depth <= 3:
        fragments.append("Decompose goals into 2 levels. Primary goal → sub-tasks → atomic actions.")
    else:
        fragments.append("Deep goal decomposition. Break into sub-sub-goals. Map dependencies before executing.")

    # Risk tolerance
    risk = dna["risk_tolerance"]
    if risk < 0.3:
        fragments.append("Be conservative. Stick to proven approaches. Small, safe increments.")
    elif risk < 0.6:
        fragments.append("Balanced risk. Try proven approaches first, but don't fear bold moves when stuck.")
    else:
        fragments.append("Be aggressive. Try radical approaches. The safe path is the slow path. Move fast, break things, measure.")

    # Verification rigor
    rigor = dna["verification_rigor"]
    if rigor < 0.5:
        fragments.append("Quick verification. Run core tests, check build. Don't over-verify.")
    elif rigor < 0.8:
        fragments.append("Standard verification. Run tests + lint + build after every change.")
    else:
        fragments.append("Rigorous verification. Run ALL checks. Guard against regressions. Test edge cases.")

    # Exploration rate
    explore = dna["exploration_rate"]
    if explore < 0.2:
        fragments.append("Exploit known good strategies. Only explore when stuck (3+ failures).")
    elif explore < 0.5:
        fragments.append("Balance exploration and exploitation. Try new approaches ~30% of the time.")
    else:
        fragments.append("Heavy exploration. Actively seek novel approaches. Novelty often beats optimization.")

    # Patience
    patience_val = dna["patience"]
    if patience_val < 0.3:
        fragments.append("Low patience. If no progress in 2 cycles, pivot immediately. Don't waste cycles.")
    elif patience_val < 0.7:
        fragments.append("Moderate patience. Give strategies 3-5 cycles before declaring failure.")
    else:
        fragments.append("High patience. Some problems need sustained effort. Give strategies up to 8 cycles.")

    # Detail orientation
    detail = dna["detail_orientation"]
    if detail < 0.4:
        fragments.append("Focus on the happy path. Ship the 80% solution. Handle edge cases later.")
    elif detail < 0.7:
        fragments.append("Handle common edge cases. Don't gold-plate, but don't ship broken either.")
    else:
        fragments.append("High attention to detail. Handle edge cases. Write thorough tests. Get it right.")

    # Parallelism
    parallel = dna["parallelism"]
    if parallel < 0.3:
        fragments.append("Work sequentially. One task at a time. Full focus.")
    elif parallel < 0.7:
        fragments.append("Use subagents for independent tasks. Parallelize when tasks don't depend on each other.")
    else:
        fragments.append("Aggressively parallelize. Spawn subagents for exploration, testing, building simultaneously.")

    return "\n".join(f"• {f}" for f in fragments)


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

def cmd_mutate():
    """Mutate one DNA parameter based on recent fitness."""
    state = load_state()

    # Check if pending mutation should be reverted
    if should_revert(state):
        pending = state["pending_mutation"]
        param = pending["param"]
        old_val = pending["old"]
        state["current_dna"][param] = old_val

        # Record revert in history
        for m in state["mutations"]:
            if m["generation"] == state["generation"] and m["param"] == param:
                m["kept"] = False
                recent = get_recent_fitness(5)
                m["fitness_impact"] = f"{sum(recent)/len(recent):.2f} (REVERTED)"

        state["pending_mutation"] = None
        state["generation"] += 1
        save_state(state)
        write_dna_to_markdown(state["current_dna"], state["generation"], state["mutations"])

        result = {"status": "reverted", "param": param, "reverted_to": old_val, "reason": "fitness_dropped"}
        print(json.dumps(result, indent=2))
        return

    # Check if pending mutation should be kept
    if state.get("pending_mutation"):
        current_cycle = get_current_cycle()
        mutation_cycle = state.get("pending_since_cycle", 0)

        if current_cycle - mutation_cycle >= 5:
            # Keep the mutation — it didn't hurt
            pending = state["pending_mutation"]
            fitness_before = state.get("fitness_at_mutation", 0.0)
            recent = get_recent_fitness(5)
            avg_recent = sum(recent) / len(recent) if recent else 0.0
            delta = avg_recent - fitness_before

            for m in state["mutations"]:
                if m["generation"] == state["generation"] and m["param"] == pending["param"]:
                    m["kept"] = True
                    m["fitness_impact"] = f"{'+' if delta >= 0 else ''}{delta:.3f}"

            state["pending_mutation"] = None
            state["generation"] += 1
            save_state(state)
            write_dna_to_markdown(state["current_dna"], state["generation"], state["mutations"])

            result = {"status": "kept", "param": pending["param"], "fitness_delta": round(delta, 3)}
            print(json.dumps(result, indent=2))
            return

        # Still evaluating — don't mutate again yet
        remaining = 5 - (current_cycle - mutation_cycle)
        result = {"status": "evaluating", "param": pending["param"], "cycles_remaining": remaining}
        print(json.dumps(result, indent=2))
        return

    # Perform new mutation
    dna = state["current_dna"]
    param_name, old_value, new_value = mutate_parameter(dna)

    # Apply mutation
    dna[param_name] = new_value
    state["current_dna"] = dna

    # Record
    current_cycle = get_current_cycle()
    recent = get_recent_fitness(5)
    current_fitness = recent[-1] if recent else 0.0

    mutation_record = {
        "generation": state["generation"],
        "cycle": current_cycle,
        "param": param_name,
        "old": old_value if not isinstance(old_value, float) else round(old_value, 2),
        "new": new_value if not isinstance(new_value, float) else round(new_value, 2),
        "fitness_impact": "—",
        "kept": True,
        "timestamp": datetime.now().isoformat(),
    }
    state["mutations"].append(mutation_record)
    state["pending_mutation"] = mutation_record
    state["pending_since_cycle"] = current_cycle
    state["fitness_at_mutation"] = current_fitness

    save_state(state)
    write_dna_to_markdown(dna, state["generation"], state["mutations"])

    result = {
        "status": "mutated",
        "generation": state["generation"],
        "param": param_name,
        "old": old_value,
        "new": new_value,
        "evaluating_for": "5 cycles",
        "current_fitness": current_fitness,
    }
    print(json.dumps(result, indent=2))


def cmd_express():
    """Output system prompt fragment from current DNA."""
    state = load_state()
    dna = state["current_dna"]
    fragment = express_dna(dna)

    output = {
        "generation": state["generation"],
        "dna": dna,
        "prompt_fragment": fragment,
    }
    print(json.dumps(output, indent=2))


def cmd_fitness():
    """Score current DNA configuration against recent cycles."""
    state = load_state()
    recent = get_recent_fitness(20)

    if len(recent) < 3:
        print(json.dumps({"error": "Not enough fitness data (need 3+ cycles)", "data_points": len(recent)}))
        return

    avg = sum(recent) / len(recent)
    trend = recent[-1] - recent[0] if len(recent) >= 2 else 0
    volatility = (sum((f - avg) ** 2 for f in recent) / len(recent)) ** 0.5

    # Score the DNA
    score = avg * 0.5 + (0.3 if trend > 0 else -0.1) + (0.2 if volatility < 0.1 else 0)
    score = max(0, min(1, score))

    result = {
        "dna_generation": state["generation"],
        "fitness_avg": round(avg, 3),
        "fitness_trend": round(trend, 3),
        "fitness_volatility": round(volatility, 3),
        "dna_score": round(score, 3),
        "data_points": len(recent),
        "pending_mutation": state.get("pending_mutation", {}).get("param"),
        "recommendation": "MUTATE" if score < 0.6 else "KEEP" if score > 0.8 else "EVALUATE",
    }
    print(json.dumps(result, indent=2))


def cmd_status():
    """Show current DNA status."""
    state = load_state()
    result = {
        "generation": state["generation"],
        "current_dna": state["current_dna"],
        "pending_mutation": state.get("pending_mutation"),
        "total_mutations": len(state.get("mutations", [])),
        "recent_mutations": state.get("mutations", [])[-5:],
    }
    print(json.dumps(result, indent=2))


def cmd_revert():
    """Revert the last mutation."""
    state = load_state()

    if not state.get("pending_mutation"):
        # Revert last kept mutation
        mutations = state.get("mutations", [])
        if not mutations:
            print(json.dumps({"error": "No mutations to revert"}))
            return

        last = mutations[-1]
        param = last["param"]
        old_val = last["old"]
        state["current_dna"][param] = old_val
        last["kept"] = False
        last["fitness_impact"] = "MANUALLY REVERTED"
    else:
        pending = state["pending_mutation"]
        param = pending["param"]
        old_val = pending["old"]
        state["current_dna"][param] = old_val
        for m in state["mutations"]:
            if m["generation"] == state["generation"] and m["param"] == param:
                m["kept"] = False
                m["fitness_impact"] = "MANUALLY REVERTED"
        state["pending_mutation"] = None

    state["generation"] += 1
    save_state(state)
    write_dna_to_markdown(state["current_dna"], state["generation"], state["mutations"])

    print(json.dumps({"status": "reverted", "param": param, "reverted_to": old_val}))


def cmd_gradient_mutate():
    """Mutate DNA parameter targeted by language gradient blame attribution.

    Instead of random mutation, use the language gradients system to identify
    WHICH parameter is most responsible for poor performance, and mutate that one.
    This is more surgical than random mutation.

    Falls back to random mutation if no gradient data is available.
    """
    gradient_state_file = STATE_DIR / "gradients.json"
    if not gradient_state_file.exists():
        # No gradient data — fall back to regular mutation
        cmd_mutate()
        return

    with open(gradient_state_file) as f:
        gradient_state = json.load(f)

    gradients = gradient_state.get("gradients", [])
    if not gradients:
        cmd_mutate()
        return

    # Find the highest-blame gradient
    top_gradient = max(gradients, key=lambda g: g.get("blame_score", 0))
    blame = top_gradient.get("blame_score", 0)
    attribution = top_gradient.get("attribution", "")

    # Map attribution signals to DNA parameters
    param_to_mutate = None

    if "error" in attribution.lower() or "failed" in attribution.lower():
        param_to_mutate = "verification_rigor"  # Increase testing
    elif "empty" in attribution.lower() or "minimal" in attribution.lower():
        param_to_mutate = "detail_orientation"  # Increase detail
    elif "alignment" in attribution.lower() or "ignored" in attribution.lower():
        param_to_mutate = "planning_depth"  # Better planning
    elif "pass-through" in attribution.lower():
        param_to_mutate = "exploration_rate"  # Try different approaches
    elif blame >= 0.5:
        param_to_mutate = "risk_tolerance"  # High blame = need bolder moves

    if param_to_mutate is None:
        # No clear mapping — fall back to random
        cmd_mutate()
        return

    # Perform targeted mutation
    state = load_state()

    if state.get("pending_mutation"):
        remaining = 5 - (get_current_cycle() - state.get("pending_since_cycle", 0))
        if remaining > 0:
            result = {"status": "evaluating", "param": state["pending_mutation"]["param"],
                      "cycles_remaining": remaining, "source": "gradient_targeted"}
            print(json.dumps(result, indent=2))
            return

    dna = state["current_dna"]
    param_name, old_value, new_value = mutate_parameter(dna, param_to_mutate)

    dna[param_name] = new_value
    state["current_dna"] = dna

    current_cycle = get_current_cycle()
    recent = get_recent_fitness(5)
    current_fitness = recent[-1] if recent else 0.0

    mutation_record = {
        "generation": state["generation"],
        "cycle": current_cycle,
        "param": param_name,
        "old": old_value if not isinstance(old_value, float) else round(old_value, 2),
        "new": new_value if not isinstance(new_value, float) else round(new_value, 2),
        "fitness_impact": "—",
        "kept": True,
        "source": "gradient_targeted",
        "blame_score": round(blame, 2),
        "attribution": attribution[:200],
        "timestamp": datetime.now().isoformat(),
    }
    state["mutations"].append(mutation_record)
    state["pending_mutation"] = mutation_record
    state["pending_since_cycle"] = current_cycle
    state["fitness_at_mutation"] = current_fitness

    save_state(state)
    write_dna_to_markdown(dna, state["generation"], state["mutations"])

    result = {
        "status": "gradient_mutated",
        "generation": state["generation"],
        "param": param_name,
        "old": old_value,
        "new": new_value,
        "source": "gradient_targeted",
        "blame_score": round(blame, 2),
        "attribution_summary": attribution[:200],
        "evaluating_for": "5 cycles",
    }
    print(json.dumps(result, indent=2))


def cmd_breed_express():
    """Express the best prompt from the breeding population.

    Integrates with prompt_breeding.py to get the best-performing evolved
    prompt for the 'soul' role, then combines it with DNA expression.
    """
    breeding_state_file = STATE_DIR / "prompt_breeding.json"

    # Get standard DNA expression
    state = load_state()
    dna = state["current_dna"]
    dna_fragment = express_dna(dna)

    # Try to get bred prompt
    bred_fragment = None
    if breeding_state_file.exists():
        with open(breeding_state_file) as f:
            breeding = json.load(f)

        for role_name in ("soul", "system", "reasoning"):
            if role_name in breeding.get("roles", {}):
                role_data = breeding["roles"][role_name]
                active = [p for p in role_data["prompts"] if p.get("active")]
                if active:
                    best = max(active, key=lambda p: p.get("avg_fitness", 0))
                    if best.get("evaluations", 0) >= 2 and best.get("avg_fitness", 0) > 0.3:
                        bred_fragment = best["text"]
                        break

    output = {
        "generation": state["generation"],
        "dna": dna,
        "dna_fragment": dna_fragment,
        "bred_prompt": bred_fragment,
        "combined_fragment": (
            f"{dna_fragment}\n\n--- Evolved Prompt (from breeding population) ---\n{bred_fragment}"
            if bred_fragment else dna_fragment
        ),
        "source": "dna+breeding" if bred_fragment else "dna_only",
    }
    print(json.dumps(output, indent=2))


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 engine/mutate_dna.py <command>")
        print("Commands: mutate, express, fitness, status, revert, gradient-mutate, breed-express")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "mutate":
        cmd_mutate()
    elif cmd == "express":
        cmd_express()
    elif cmd == "fitness":
        cmd_fitness()
    elif cmd == "status":
        cmd_status()
    elif cmd == "revert":
        cmd_revert()
    elif cmd == "gradient-mutate":
        cmd_gradient_mutate()
    elif cmd == "breed-express":
        cmd_breed_express()
    else:
        print(f'{{"error": "Unknown command: {cmd}"}}')
        sys.exit(1)


if __name__ == "__main__":
    main()
