#!/usr/bin/env python3
"""
PROMPT BREEDING — Evolutionary Prompt Population (EvoPrompt Pattern).

Inspired by EvoAgentX's EvoPrompt and Promptbreeder. Treats prompts as a
breeding population where genetic operators (crossover + mutation) evolve
better prompts over generations.

Instead of mutating one DNA parameter at a time (mutate_dna.py's approach),
this module evolves ENTIRE prompt strings as organisms in a population:

1. POPULATION: Maintain N variant prompts for each pipeline role
2. CROSSOVER: Combine two high-fitness prompts into a child
3. MUTATION: Introduce small random variations to a prompt
4. SELECTION: Fitness-proportional selection for next generation
5. ELITISM: Always keep the best-performing prompt
6. SELF-REFERENTIAL: The mutation prompt itself can be evolved (Promptbreeder)

Usage:
    python3 engine/prompt_breeding.py init <role> <seed_prompt>
    python3 engine/prompt_breeding.py breed <role>
    python3 engine/prompt_breeding.py score <role> <prompt_id> <fitness>
    python3 engine/prompt_breeding.py best <role>
    python3 engine/prompt_breeding.py population <role>
    python3 engine/prompt_breeding.py crossover <role> <id1> <id2>
    python3 engine/prompt_breeding.py mutate <role> <prompt_id>
    python3 engine/prompt_breeding.py evolve-mutator        Promptbreeder: evolve the mutation prompt itself
    python3 engine/prompt_breeding.py status
"""

import json
import os
import random
import sys
import tempfile
from pathlib import Path

try:
    from engine.stats import now, wilson_lower
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now, wilson_lower

ENGINE_DIR = Path(__file__).parent
PROJECT_DIR = ENGINE_DIR.parent
STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
BREEDING_STATE = STATE_DIR / "prompt_breeding.json"

MAX_POPULATION_PER_ROLE = 8
MIN_EVALUATIONS = 3  # Minimum evals before a prompt can be culled
ELITISM_COUNT = 1  # Number of top prompts always preserved

# The default mutation meta-prompt — this itself gets evolved by Promptbreeder
DEFAULT_MUTATOR = (
    "Given the following prompt, create a variant that is slightly different "
    "but preserves the core intent. Make ONE of these changes: "
    "(a) rephrase one instruction for clarity, "
    "(b) add a specific constraint or example, "
    "(c) remove unnecessary verbosity, "
    "(d) change the ordering of instructions. "
    "Return ONLY the new prompt text."
)

# The crossover meta-prompt
DEFAULT_CROSSOVER = (
    "Given two high-performing prompts (A and B), create a new prompt that "
    "combines the strengths of both. Take the best elements from each: "
    "clear instructions from A, specific constraints from B, etc. "
    "The result should be a coherent prompt, not a mechanical concatenation. "
    "Return ONLY the new prompt text."
)


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def load_breeding_state() -> dict:
    """Load breeding state from JSON."""
    if BREEDING_STATE.exists():
        with open(BREEDING_STATE) as f:
            return json.load(f)
    return {
        "roles": {},
        "generation": 0,
        "mutator_prompt": DEFAULT_MUTATOR,
        "crossover_prompt": DEFAULT_CROSSOVER,
        "mutator_history": [],
        "total_breeds": 0,
    }


def _atomic_write(path: Path, data):
    """Write JSON atomically via temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_breeding_state(state: dict):
    """Save breeding state to JSON (atomic write)."""
    # Trim inactive prompts per role to prevent unbounded growth
    for role_data in state.get("roles", {}).values():
        inactive = [p for p in role_data["prompts"] if not p.get("active", True)]
        if len(inactive) > 20:
            inactive_ids = {p["id"] for p in sorted(inactive, key=lambda p: p.get("created", ""))[:len(inactive) - 20]}
            role_data["prompts"] = [p for p in role_data["prompts"] if p.get("active", True) or p["id"] not in inactive_ids]
    _atomic_write(BREEDING_STATE, state)


# ---------------------------------------------------------------------------
# Population Management
# ---------------------------------------------------------------------------

def cmd_init(role: str, seed_prompt: str):
    """Initialize a prompt population for a role with a seed prompt.

    The seed prompt is the starting organism. Mutations will create variants.
    """
    state = load_breeding_state()

    if role not in state["roles"]:
        state["roles"][role] = {"prompts": [], "next_id": 1}

    role_data = state["roles"][role]
    prompt_id = f"P{role_data['next_id']:03d}"
    role_data["next_id"] += 1

    prompt_entry = {
        "id": prompt_id,
        "text": seed_prompt,
        "fitness_sum": 0.0,
        "evaluations": 0,
        "avg_fitness": 0.0,
        "generation": 0,
        "parents": [],
        "origin": "seed",
        "created": now(),
        "active": True,
    }
    role_data["prompts"].append(prompt_entry)
    save_breeding_state(state)

    print(json.dumps({
        "status": "initialized",
        "role": role,
        "prompt_id": prompt_id,
        "population_size": len(role_data["prompts"]),
    }))


def cmd_score(role: str, prompt_id: str, fitness: float):
    """Record a fitness observation for a prompt."""
    fitness = max(0.0, min(1.0, fitness))
    state = load_breeding_state()

    if role not in state["roles"]:
        print(json.dumps({"error": f"Role '{role}' not found"}))
        sys.exit(1)

    for p in state["roles"][role]["prompts"]:
        if p["id"] == prompt_id:
            p["fitness_sum"] += fitness
            p["evaluations"] += 1
            p["avg_fitness"] = round(p["fitness_sum"] / p["evaluations"], 4)
            save_breeding_state(state)
            print(json.dumps({
                "status": "scored",
                "prompt_id": prompt_id,
                "avg_fitness": p["avg_fitness"],
                "evaluations": p["evaluations"],
            }))
            return

    print(json.dumps({"error": f"Prompt '{prompt_id}' not found in role '{role}'"}))
    sys.exit(1)


def cmd_best(role: str):
    """Get the best-performing prompt for a role."""
    state = load_breeding_state()

    if role not in state["roles"]:
        print(json.dumps({"error": f"Role '{role}' not found"}))
        sys.exit(1)

    prompts = [p for p in state["roles"][role]["prompts"] if p["active"]]
    if not prompts:
        print(json.dumps({"error": f"No active prompts for role '{role}'"}))
        sys.exit(1)

    # Use Wilson lower bound for ranking (accounts for sample size)
    def rank_key(p):
        if p["evaluations"] == 0:
            return -1
        # Treat fitness > 0.5 as "success" for Wilson scoring
        successes = int(p["avg_fitness"] * p["evaluations"])
        return wilson_lower(successes, p["evaluations"])

    best = max(prompts, key=rank_key)

    print(json.dumps({
        "role": role,
        "best_prompt_id": best["id"],
        "text": best["text"],
        "avg_fitness": best["avg_fitness"],
        "evaluations": best["evaluations"],
        "generation": best["generation"],
    }))


def cmd_population(role: str):
    """Show the full population for a role."""
    state = load_breeding_state()

    if role not in state["roles"]:
        print(json.dumps({"error": f"Role '{role}' not found"}))
        sys.exit(1)

    prompts = state["roles"][role]["prompts"]
    active = [p for p in prompts if p["active"]]
    inactive = [p for p in prompts if not p["active"]]

    print(json.dumps({
        "role": role,
        "active_count": len(active),
        "inactive_count": len(inactive),
        "prompts": [{
            "id": p["id"],
            "text_preview": p["text"][:100],
            "avg_fitness": p["avg_fitness"],
            "evaluations": p["evaluations"],
            "generation": p["generation"],
            "origin": p["origin"],
            "active": p["active"],
        } for p in prompts],
    }))


# ---------------------------------------------------------------------------
# Genetic Operators
# ---------------------------------------------------------------------------

def cmd_crossover(role: str, id1: str, id2: str):
    """Create a child prompt by crossing two parent prompts.

    In a real system with LLM access, this would call the LLM with the
    crossover meta-prompt. Here we do structural crossover:
    split each prompt into sentences and interleave.
    """
    state = load_breeding_state()

    if role not in state["roles"]:
        print(json.dumps({"error": f"Role '{role}' not found"}))
        sys.exit(1)

    role_data = state["roles"][role]
    parent1 = next((p for p in role_data["prompts"] if p["id"] == id1), None)
    parent2 = next((p for p in role_data["prompts"] if p["id"] == id2), None)

    if not parent1 or not parent2:
        missing = id1 if not parent1 else id2
        print(json.dumps({"error": f"Prompt '{missing}' not found"}))
        sys.exit(1)

    # Structural crossover using shared helper
    child_text = _do_crossover(parent1["text"], parent2["text"],
                               parent1["avg_fitness"], parent2["avg_fitness"])

    prompt_id = f"P{role_data['next_id']:03d}"
    role_data["next_id"] += 1

    child = {
        "id": prompt_id,
        "text": child_text,
        "fitness_sum": 0.0,
        "evaluations": 0,
        "avg_fitness": 0.0,
        "generation": max(parent1["generation"], parent2["generation"]) + 1,
        "parents": [id1, id2],
        "origin": "crossover",
        "created": now(),
        "active": True,
    }
    role_data["prompts"].append(child)

    state["generation"] += 1
    state["total_breeds"] += 1
    save_breeding_state(state)

    print(json.dumps({
        "status": "crossover",
        "child_id": prompt_id,
        "parents": [id1, id2],
        "generation": child["generation"],
        "child_preview": child_text[:200],
    }))


def cmd_mutate(role: str, prompt_id: str):
    """Create a mutated variant of a prompt.

    Applies one of several mutation operators:
    - Sentence shuffle: Reorder instructions
    - Word substitution: Replace key words with synonyms
    - Insertion: Add a new constraint or instruction
    - Deletion: Remove a sentence
    - Emphasis: Capitalize or add emphasis to an instruction
    """
    state = load_breeding_state()

    if role not in state["roles"]:
        print(json.dumps({"error": f"Role '{role}' not found"}))
        sys.exit(1)

    role_data = state["roles"][role]
    parent = next((p for p in role_data["prompts"] if p["id"] == prompt_id), None)

    if not parent:
        print(json.dumps({"error": f"Prompt '{prompt_id}' not found"}))
        sys.exit(1)

    # Apply a random mutation operator
    mutation_type, mutated_text = _apply_mutation(parent["text"])

    new_id = f"P{role_data['next_id']:03d}"
    role_data["next_id"] += 1

    child = {
        "id": new_id,
        "text": mutated_text,
        "fitness_sum": 0.0,
        "evaluations": 0,
        "avg_fitness": 0.0,
        "generation": parent["generation"] + 1,
        "parents": [prompt_id],
        "origin": f"mutation:{mutation_type}",
        "created": now(),
        "active": True,
    }
    role_data["prompts"].append(child)

    state["generation"] += 1
    state["total_breeds"] += 1
    save_breeding_state(state)

    print(json.dumps({
        "status": "mutated",
        "child_id": new_id,
        "parent_id": prompt_id,
        "mutation_type": mutation_type,
        "generation": child["generation"],
        "child_preview": mutated_text[:200],
    }))


def _do_crossover(text1: str, text2: str, fitness1: float, fitness2: float) -> str:
    """Perform structural crossover between two prompt texts.

    Takes ~60% from the fitter parent, ~40% from the other.
    """
    sentences1 = _split_sentences(text1)
    sentences2 = _split_sentences(text2)

    if fitness1 >= fitness2:
        primary, secondary = sentences1, sentences2
    else:
        primary, secondary = sentences2, sentences1

    child_sentences = []
    for i in range(max(len(primary), len(secondary))):
        if i < len(primary) and random.random() < 0.6:
            child_sentences.append(primary[i])
        elif i < len(secondary):
            child_sentences.append(secondary[i])
        elif i < len(primary):
            child_sentences.append(primary[i])

    return " ".join(child_sentences)


def _apply_mutation(text: str) -> tuple:
    """Apply a random mutation operator to prompt text. Returns (type, new_text)."""
    sentences = _split_sentences(text)

    operators = ["shuffle", "delete", "emphasis", "append_constraint"]
    if len(sentences) < 2:
        operators = ["emphasis", "append_constraint"]

    op = random.choice(operators)

    if op == "shuffle" and len(sentences) >= 2:
        # Swap two random sentences
        i, j = random.sample(range(len(sentences)), 2)
        sentences[i], sentences[j] = sentences[j], sentences[i]
        return "shuffle", " ".join(sentences)

    elif op == "delete" and len(sentences) > 2:
        # Remove a random non-first sentence
        idx = random.randint(1, len(sentences) - 1)
        sentences.pop(idx)
        return "delete", " ".join(sentences)

    elif op == "emphasis":
        # Add emphasis to a random sentence
        if sentences:
            idx = random.randint(0, len(sentences) - 1)
            sentences[idx] = "IMPORTANT: " + sentences[idx]
        return "emphasis", " ".join(sentences)

    elif op == "append_constraint":
        # Add a generic quality constraint
        constraints = [
            "Be precise and specific.",
            "Show your reasoning step by step.",
            "Focus on the most impactful change first.",
            "Verify your output before responding.",
            "If uncertain, state your uncertainty explicitly.",
            "Prioritize correctness over speed.",
        ]
        sentences.append(random.choice(constraints))
        return "append_constraint", " ".join(sentences)

    return "noop", text


def _split_sentences(text: str) -> list:
    """Split text into sentences (simple heuristic)."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# Breed — Full evolutionary cycle
# ---------------------------------------------------------------------------

def cmd_breed(role: str):
    """Run one full breeding cycle for a role's prompt population.

    1. Select parents (fitness-proportional)
    2. Apply crossover or mutation
    3. Cull weakest members if population exceeds max
    4. Report results
    """
    state = load_breeding_state()

    if role not in state["roles"]:
        print(json.dumps({"error": f"Role '{role}' not found"}))
        sys.exit(1)

    role_data = state["roles"][role]
    active = [p for p in role_data["prompts"] if p["active"]]

    if len(active) < 2:
        print(json.dumps({"error": "Need at least 2 active prompts to breed"}))
        sys.exit(1)

    # Fitness-proportional parent selection
    total_fitness = sum(max(p["avg_fitness"], 0.01) for p in active)
    weights = [max(p["avg_fitness"], 0.01) / total_fitness for p in active]

    # Select two parents (weighted random)
    parents = _weighted_sample(active, weights, 2)

    # Decide: crossover (70%) or mutation (30%)
    if random.random() < 0.7 and len(parents) == 2:
        # Crossover using shared helper
        child_text = _do_crossover(parents[0]["text"], parents[1]["text"],
                                   parents[0]["avg_fitness"], parents[1]["avg_fitness"])
        origin = "crossover"
        parent_ids = [parents[0]["id"], parents[1]["id"]]
    else:
        # Mutation
        parent = parents[0]
        mutation_type, child_text = _apply_mutation(parent["text"])
        origin = f"mutation:{mutation_type}"
        parent_ids = [parent["id"]]

    # Create child
    new_id = f"P{role_data['next_id']:03d}"
    role_data["next_id"] += 1

    child = {
        "id": new_id,
        "text": child_text,
        "fitness_sum": 0.0,
        "evaluations": 0,
        "avg_fitness": 0.0,
        "generation": state["generation"] + 1,
        "parents": parent_ids,
        "origin": origin,
        "created": now(),
        "active": True,
    }
    role_data["prompts"].append(child)

    # Cull if over max population
    culled = []
    active = [p for p in role_data["prompts"] if p["active"]]
    if len(active) > MAX_POPULATION_PER_ROLE:
        # Sort by Wilson-scored fitness, keep top N
        def rank(p):
            if p["evaluations"] < MIN_EVALUATIONS:
                return float('inf')  # Protect young prompts
            successes = int(p["avg_fitness"] * p["evaluations"])
            return wilson_lower(successes, p["evaluations"])

        ranked = sorted(active, key=rank)
        to_cull = len(active) - MAX_POPULATION_PER_ROLE

        for p in ranked[:to_cull]:
            if p["evaluations"] >= MIN_EVALUATIONS:  # Only cull evaluated prompts
                p["active"] = False
                culled.append(p["id"])

    state["generation"] += 1
    state["total_breeds"] += 1
    save_breeding_state(state)

    print(json.dumps({
        "status": "bred",
        "child_id": new_id,
        "origin": origin,
        "parent_ids": parent_ids,
        "generation": state["generation"],
        "child_preview": child_text[:200],
        "culled": culled,
        "population_size": len([p for p in role_data["prompts"] if p["active"]]),
    }))


def _weighted_sample(items: list, weights: list, n: int) -> list:
    """Sample n items with weights (without replacement)."""
    result = []
    remaining = list(zip(items, weights))
    for _ in range(min(n, len(remaining))):
        total = sum(w for _, w in remaining)
        r = random.random() * total
        cumulative = 0
        for i, (item, w) in enumerate(remaining):
            cumulative += w
            if r <= cumulative:
                result.append(item)
                remaining.pop(i)
                break
    return result


# ---------------------------------------------------------------------------
# Promptbreeder — Self-referential meta-prompt evolution
# ---------------------------------------------------------------------------

def cmd_evolve_mutator():
    """Evolve the mutation meta-prompt itself (Promptbreeder pattern).

    The meta-prompt that instructs how to mutate prompts is ITSELF a prompt
    that can be evolved. This creates a self-referential improvement loop:
    the system improves its own ability to improve.

    Process:
    1. Take current mutator prompt
    2. Apply mutation operators to IT
    3. Track which mutator version produced the best offspring
    4. Keep the best-performing mutator
    """
    state = load_breeding_state()

    current_mutator = state["mutator_prompt"]
    mutation_type, new_mutator = _apply_mutation(current_mutator)

    # Track history
    state["mutator_history"].append({
        "previous": current_mutator[:200],
        "mutation_type": mutation_type,
        "new": new_mutator[:200],
        "timestamp": now(),
    })

    # Keep only last 20 mutator versions
    if len(state["mutator_history"]) > 20:
        state["mutator_history"] = state["mutator_history"][-20:]

    state["mutator_prompt"] = new_mutator
    save_breeding_state(state)

    print(json.dumps({
        "status": "mutator_evolved",
        "mutation_type": mutation_type,
        "new_mutator_preview": new_mutator[:300],
        "mutator_versions": len(state["mutator_history"]),
    }))


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def cmd_status():
    """Show overall breeding status."""
    state = load_breeding_state()

    roles_summary = {}
    for role, data in state["roles"].items():
        active = [p for p in data["prompts"] if p["active"]]
        best = max(active, key=lambda p: p["avg_fitness"]) if active else None
        roles_summary[role] = {
            "active_prompts": len(active),
            "total_prompts": len(data["prompts"]),
            "best_fitness": best["avg_fitness"] if best else 0,
            "best_id": best["id"] if best else None,
        }

    print(json.dumps({
        "generation": state["generation"],
        "total_breeds": state["total_breeds"],
        "roles": roles_summary,
        "mutator_preview": state["mutator_prompt"][:200],
        "mutator_versions": len(state["mutator_history"]),
    }))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: init <role> <seed_prompt>"}))
            sys.exit(1)
        cmd_init(sys.argv[2], sys.argv[3])
    elif cmd == "breed":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: breed <role>"}))
            sys.exit(1)
        cmd_breed(sys.argv[2])
    elif cmd == "score":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: score <role> <prompt_id> <fitness>"}))
            sys.exit(1)
        cmd_score(sys.argv[2], sys.argv[3], float(sys.argv[4]))
    elif cmd == "best":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: best <role>"}))
            sys.exit(1)
        cmd_best(sys.argv[2])
    elif cmd == "population":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: population <role>"}))
            sys.exit(1)
        cmd_population(sys.argv[2])
    elif cmd == "crossover":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: crossover <role> <id1> <id2>"}))
            sys.exit(1)
        cmd_crossover(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "mutate":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: mutate <role> <prompt_id>"}))
            sys.exit(1)
        cmd_mutate(sys.argv[2], sys.argv[3])
    elif cmd == "evolve-mutator":
        cmd_evolve_mutator()
    elif cmd == "status":
        cmd_status()
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
