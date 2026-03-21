#!/usr/bin/env python3
"""
LANGUAGE GRADIENTS — Backward Attribution Through Pipeline Stages.

Inspired by aiwaves-cn/agents "Symbolic Learning Enables Self-Evolving Agents"
(arXiv:2406.18532). Maps the neural network training loop onto agent pipelines:

    Forward Pass  → Execute pipeline, record trajectory at each node
    Language Loss  → Textual evaluation of final output quality
    Backpropagation → Propagate blame/credit backward through nodes
    Weight Update  → Rewrite prompts/tools/connections based on gradients

Instead of numeric gradients, we use "language gradients" — structured textual
critiques that localize blame to specific pipeline stages. This is more surgical
than the existing "mutate one thing and hope" approach in mutate_dna.py.

Usage:
    python3 engine/language_gradients.py record <node_id> <input_json> <output_json> <prompt_used>
    python3 engine/language_gradients.py loss <final_output> <expected> <task_description>
    python3 engine/language_gradients.py backward <loss_description>
    python3 engine/language_gradients.py gradients           Show current gradients
    python3 engine/language_gradients.py apply               Apply gradients to update weights
    python3 engine/language_gradients.py trajectory          Show current forward pass trajectory
    python3 engine/language_gradients.py clear               Clear trajectory for new pass
    python3 engine/language_gradients.py history              Show gradient history
"""

import json
import os
import sys
import tempfile
from pathlib import Path

try:
    from engine.stats import now
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now

ENGINE_DIR = Path(__file__).parent
PROJECT_DIR = ENGINE_DIR.parent
STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
GRADIENT_STATE = STATE_DIR / "gradients.json"
GRADIENT_HISTORY = STATE_DIR / "gradient_history.json"
MAX_HISTORY = 100


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def load_gradient_state() -> dict:
    """Load gradient state from JSON."""
    if GRADIENT_STATE.exists():
        with open(GRADIENT_STATE) as f:
            return json.load(f)
    return {
        "trajectory": [],
        "loss": None,
        "gradients": [],
        "pass_number": 0,
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


def save_gradient_state(state: dict):
    """Save gradient state to JSON (atomic write)."""
    _atomic_write(GRADIENT_STATE, state)


def load_gradient_history() -> list:
    """Load gradient history."""
    if GRADIENT_HISTORY.exists():
        with open(GRADIENT_HISTORY) as f:
            return json.load(f)
    return []


def save_gradient_history(history: list):
    """Save gradient history, trimming to MAX_HISTORY."""
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    _atomic_write(GRADIENT_HISTORY, history)


# ---------------------------------------------------------------------------
# Forward Pass — Record trajectory at each pipeline node
# ---------------------------------------------------------------------------

def cmd_record(node_id: str, input_data: str, output_data: str, prompt_used: str):
    """Record a node's execution in the forward pass trajectory.

    Each node in the pipeline records:
    - What input it received
    - What prompt/instructions it used
    - What output it produced
    - Timestamp and ordering

    This creates the "computational graph" that backpropagation traverses.
    """
    state = load_gradient_state()

    node_record = {
        "node_id": node_id,
        "step": len(state["trajectory"]),
        "input": input_data[:2000],  # Truncate to prevent bloat
        "output": output_data[:2000],
        "prompt": prompt_used[:2000],
        "timestamp": now(),
    }
    state["trajectory"].append(node_record)
    save_gradient_state(state)

    print(json.dumps({
        "status": "recorded",
        "node_id": node_id,
        "step": node_record["step"],
        "trajectory_length": len(state["trajectory"]),
    }))


# ---------------------------------------------------------------------------
# Language Loss — Textual evaluation of final output
# ---------------------------------------------------------------------------

def cmd_loss(final_output: str, expected: str, task_description: str):
    """Compute language loss by comparing final output against expectations.

    Unlike numeric loss (MSE, cross-entropy), language loss is a structured
    textual description of what went wrong and how far off the output was.

    When no expected output is available (unsupervised mode), evaluates
    against the task description alone — enabling self-evolution without labels.
    """
    state = load_gradient_state()

    # Compute structured loss dimensions
    loss_dimensions = []

    # Dimension 1: Task completion
    if expected and expected.strip():
        # Supervised mode — compare against ground truth
        exact_match = final_output.strip() == expected.strip()
        partial_match = expected.strip().lower() in final_output.strip().lower()
        if exact_match:
            loss_dimensions.append({
                "dimension": "task_completion",
                "score": 1.0,
                "detail": "Output exactly matches expected result",
            })
        elif partial_match:
            loss_dimensions.append({
                "dimension": "task_completion",
                "score": 0.6,
                "detail": f"Output partially matches expected. Expected: '{expected[:200]}', Got: '{final_output[:200]}'",
            })
        else:
            loss_dimensions.append({
                "dimension": "task_completion",
                "score": 0.0,
                "detail": f"Output does not match expected. Expected: '{expected[:200]}', Got: '{final_output[:200]}'",
            })
    else:
        # Unsupervised mode — evaluate against task description
        task_words = set(task_description.lower().split())
        output_words = set(final_output.lower().split())
        relevance = len(task_words & output_words) / max(len(task_words), 1)
        loss_dimensions.append({
            "dimension": "task_relevance",
            "score": min(1.0, relevance * 2),  # Scale up since partial overlap is expected
            "detail": f"Unsupervised evaluation: {relevance:.0%} keyword overlap with task description",
        })

    # Dimension 2: Output quality heuristics
    has_error_keywords = any(kw in final_output.lower() for kw in
                            ["error", "traceback", "exception", "failed", "undefined"])
    if has_error_keywords:
        loss_dimensions.append({
            "dimension": "error_presence",
            "score": 0.0,
            "detail": "Output contains error indicators",
        })

    is_empty = len(final_output.strip()) == 0
    if is_empty:
        loss_dimensions.append({
            "dimension": "non_empty",
            "score": 0.0,
            "detail": "Output is empty",
        })

    # Aggregate loss
    if loss_dimensions:
        avg_score = sum(d["score"] for d in loss_dimensions) / len(loss_dimensions)
    else:
        avg_score = 0.5

    loss = {
        "aggregate_score": round(avg_score, 3),
        "aggregate_loss": round(1.0 - avg_score, 3),
        "dimensions": loss_dimensions,
        "mode": "supervised" if expected and expected.strip() else "unsupervised",
        "task_description": task_description[:500],
        "output_preview": final_output[:500],
        "timestamp": now(),
    }

    state["loss"] = loss
    save_gradient_state(state)

    print(json.dumps({"status": "loss_computed", **loss}))


# ---------------------------------------------------------------------------
# Backward Propagation — Propagate blame through pipeline nodes
# ---------------------------------------------------------------------------

def cmd_backward(loss_description: str = ""):
    """Propagate language gradients backward through the trajectory.

    For each node (traversed in reverse order), generate a "language gradient"
    that answers: "Given the downstream loss, what did THIS node do wrong,
    and how should its prompt/tools be changed?"

    This localizes blame to specific nodes instead of the generic "something
    went wrong" that forward-only mutation produces.
    """
    state = load_gradient_state()

    if not state["trajectory"]:
        print(json.dumps({"error": "No trajectory recorded. Run forward pass first."}))
        sys.exit(1)

    loss = state.get("loss")
    if not loss and not loss_description:
        print(json.dumps({"error": "No loss computed. Run 'loss' first or provide loss_description."}))
        sys.exit(1)

    # Use explicit loss description or the computed one
    if loss_description:
        loss_text = loss_description
        loss_score = None
    else:
        loss_text = "; ".join(f"{d['dimension']}: {d['detail']}" for d in loss["dimensions"])
        loss_score = loss["aggregate_loss"]

    # Backward pass: traverse nodes in reverse
    gradients = []
    accumulated_blame = loss_text

    for node in reversed(state["trajectory"]):
        gradient = {
            "node_id": node["node_id"],
            "step": node["step"],
            "downstream_loss": accumulated_blame[:1000],
            "node_input": node["input"][:500],
            "node_output": node["output"][:500],
            "node_prompt": node["prompt"][:500],
            "attribution": _compute_attribution(node, accumulated_blame),
            "suggested_fix": _suggest_fix(node, accumulated_blame),
            "blame_score": _compute_blame_score(node, accumulated_blame),
        }
        gradients.append(gradient)

        # Update accumulated blame for upstream nodes
        # Each node's attribution becomes part of the blame for its predecessors
        accumulated_blame = (
            f"Node '{node['node_id']}' (step {node['step']}): "
            f"{gradient['attribution']}. "
            f"Previous blame: {accumulated_blame[:500]}"
        )

    state["gradients"] = gradients
    state["pass_number"] += 1
    save_gradient_state(state)

    # Save to history
    history = load_gradient_history()
    history.append({
        "pass_number": state["pass_number"],
        "loss_score": loss_score,
        "loss_text": loss_text[:500],
        "gradient_count": len(gradients),
        "top_blamed_node": max(gradients, key=lambda g: g["blame_score"])["node_id"] if gradients else None,
        "timestamp": now(),
    })
    save_gradient_history(history)

    print(json.dumps({
        "status": "backward_complete",
        "pass_number": state["pass_number"],
        "gradients_computed": len(gradients),
        "gradients": gradients,
        "loss_score": loss_score,
    }))


def _classify_node_output(node: dict) -> dict:
    """Classify node output for error/empty/alignment patterns.

    Returns a dict with boolean flags reused by attribution, fix suggestion,
    and blame score computation.
    """
    output = node["output"]
    output_lower = output.lower()
    error_keywords = ["error", "failed", "exception", "traceback"]
    has_errors = any(kw in output_lower for kw in error_keywords)
    is_empty = len(output.strip()) < 10
    prompt_words = set(node["prompt"].lower().split())
    output_words = set(output_lower.split())
    if prompt_words and output_words:
        alignment = len(prompt_words & output_words) / max(len(prompt_words), 1)
    else:
        alignment = 0.0
    return {
        "has_errors": has_errors,
        "is_empty": is_empty,
        "alignment": alignment,
        "short_prompt": len(node["prompt"]) < 50,
    }


def _compute_attribution(node: dict, downstream_loss: str) -> str:
    """Compute what this specific node contributed to the downstream loss.

    This is the "language gradient" — a textual description of this node's
    contribution to the error.
    """
    cls = _classify_node_output(node)
    loss_lower = downstream_loss.lower()

    attributions = []

    if cls["has_errors"]:
        attributions.append("Node produced error output that propagated downstream")

    if cls["is_empty"]:
        attributions.append("Node produced minimal/empty output, starving downstream nodes of input")

    if node["node_id"].lower() in loss_lower:
        attributions.append(f"Loss specifically references this node ({node['node_id']})")

    if cls["alignment"] < 0.1:
        attributions.append(
            f"Low prompt-output alignment ({cls['alignment']:.0%}): "
            f"prompt may be poorly specified or model ignored instructions"
        )

    if not attributions:
        attributions.append("No direct attribution detected — node may be a neutral pass-through")

    return "; ".join(attributions)


def _suggest_fix(node: dict, downstream_loss: str) -> str:
    """Suggest concrete changes to this node's prompt/configuration."""
    cls = _classify_node_output(node)
    suggestions = []

    # Error in output → add error handling to prompt
    if cls["has_errors"]:
        suggestions.append("Add explicit error handling instructions to prompt")
        suggestions.append("Add 'If you encounter an error, describe it and attempt recovery' to prompt")

    # Empty output → strengthen output requirements
    if cls["is_empty"]:
        suggestions.append("Add minimum output length requirement to prompt")
        suggestions.append("Add 'You MUST produce a non-empty result' to prompt")

    # Short prompt → may lack specificity
    if cls["short_prompt"]:
        suggestions.append("Prompt is very short — add more specific instructions about expected format and content")

    # Generic suggestion based on loss
    if "task_completion" in downstream_loss.lower() and "0.0" in downstream_loss:
        suggestions.append("Task completely failed — consider replacing this node's approach entirely")

    if not suggestions:
        suggestions.append("No specific fix suggested — node appears functional")

    return "; ".join(suggestions)


def _compute_blame_score(node: dict, downstream_loss: str) -> float:
    """Compute a numeric blame score [0.0, 1.0] for this node.

    Higher = more responsible for the downstream loss.
    """
    cls = _classify_node_output(node)
    score = 0.0

    if cls["has_errors"]:
        score += 0.4

    if cls["is_empty"]:
        score += 0.3

    # Loss mentions this node
    if node["node_id"].lower() in downstream_loss.lower():
        score += 0.2

    if cls["short_prompt"]:
        score += 0.1

    return min(1.0, round(score, 2))


# ---------------------------------------------------------------------------
# Apply Gradients — Update prompts/weights based on computed gradients
# ---------------------------------------------------------------------------

def cmd_apply():
    """Apply computed gradients to update pipeline weights.

    This is the "symbolic optimizer" — it takes language gradients and
    produces concrete updates to prompts and configuration.

    Returns a structured update plan that can be executed by the caller.
    """
    state = load_gradient_state()

    if not state["gradients"]:
        print(json.dumps({"error": "No gradients computed. Run backward pass first."}))
        sys.exit(1)

    updates = []
    for gradient in state["gradients"]:
        if gradient["blame_score"] < 0.1:
            continue  # Skip nodes with negligible blame

        update = {
            "node_id": gradient["node_id"],
            "blame_score": gradient["blame_score"],
            "current_prompt_preview": gradient["node_prompt"][:200],
            "suggested_fix": gradient["suggested_fix"],
            "attribution": gradient["attribution"],
            "update_type": _classify_update(gradient),
        }
        updates.append(update)

    # Sort by blame score descending — fix worst nodes first
    updates.sort(key=lambda u: u["blame_score"], reverse=True)

    print(json.dumps({
        "status": "update_plan_ready",
        "pass_number": state["pass_number"],
        "updates": updates,
        "total_nodes": len(state["trajectory"]),
        "nodes_to_update": len(updates),
        "top_priority": updates[0] if updates else None,
    }))


def _classify_update(gradient: dict) -> str:
    """Classify what kind of update is needed."""
    score = gradient["blame_score"]
    if score >= 0.7:
        return "REPLACE"  # Node needs complete rework
    elif score >= 0.4:
        return "MAJOR_EDIT"  # Significant prompt changes
    elif score >= 0.2:
        return "MINOR_EDIT"  # Small adjustments
    else:
        return "MONITOR"  # Keep watching but no change needed


# ---------------------------------------------------------------------------
# Query Commands
# ---------------------------------------------------------------------------

def cmd_trajectory():
    """Show the current forward pass trajectory."""
    state = load_gradient_state()
    print(json.dumps({
        "pass_number": state["pass_number"],
        "trajectory_length": len(state["trajectory"]),
        "trajectory": state["trajectory"],
    }))


def cmd_gradients():
    """Show current computed gradients."""
    state = load_gradient_state()
    print(json.dumps({
        "pass_number": state["pass_number"],
        "gradients": state["gradients"],
        "loss": state.get("loss"),
    }))


def cmd_clear():
    """Clear trajectory for a new forward pass."""
    state = load_gradient_state()
    state["trajectory"] = []
    state["loss"] = None
    state["gradients"] = []
    save_gradient_state(state)
    print(json.dumps({"status": "cleared", "pass_number": state["pass_number"]}))


def cmd_history():
    """Show gradient computation history."""
    history = load_gradient_history()
    print(json.dumps({
        "total_passes": len(history),
        "recent": history[-10:],
    }))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "record":
        if len(sys.argv) < 6:
            print(json.dumps({"error": "Usage: record <node_id> <input> <output> <prompt>"}))
            sys.exit(1)
        cmd_record(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "loss":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: loss <final_output> <expected> <task_description>"}))
            sys.exit(1)
        expected = sys.argv[3] if len(sys.argv) > 3 else ""
        task_desc = sys.argv[4] if len(sys.argv) > 4 else ""
        cmd_loss(sys.argv[2], expected, task_desc)
    elif cmd == "backward":
        loss_desc = sys.argv[2] if len(sys.argv) > 2 else ""
        cmd_backward(loss_desc)
    elif cmd == "apply":
        cmd_apply()
    elif cmd == "trajectory":
        cmd_trajectory()
    elif cmd == "gradients":
        cmd_gradients()
    elif cmd == "clear":
        cmd_clear()
    elif cmd == "history":
        cmd_history()
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
