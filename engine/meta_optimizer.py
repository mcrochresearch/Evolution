#!/usr/bin/env python3
"""
META OPTIMIZER — Three-Optimizer Design + Meta-Prompt Optimization Loop.

Inspired by aiwaves-cn/agents (three separate optimizers) and OpenAI Cookbook
(meta-prompt optimization loop with threshold-gated deployment).

Three independent optimization dimensions:
1. PROMPT OPTIMIZER: Rewrites node prompts based on language gradients
2. TOOL OPTIMIZER: Adjusts which tools are available to each node
3. TOPOLOGY OPTIMIZER: Restructures the pipeline DAG (add/remove/reorder nodes)

Each optimizer operates independently to prevent conflating different kinds
of improvements. The meta-optimization loop:
  1. Run agent on test cases
  2. N independent graders score the output
  3. Meta-prompt agent rewrites the system prompt based on grader feedback
  4. Re-evaluate — if score > threshold, deploy; else loop

Usage:
    python3 engine/meta_optimizer.py optimize-prompt <node_id> <current_prompt> <gradient_json>
    python3 engine/meta_optimizer.py optimize-tools <node_id> <tools_json> <gradient_json>
    python3 engine/meta_optimizer.py optimize-topology <pipeline_json> <gradient_json>
    python3 engine/meta_optimizer.py meta-loop <prompt> <test_results_json> <grader_feedback_json>
    python3 engine/meta_optimizer.py threshold-check <score> [threshold]
    python3 engine/meta_optimizer.py status
    python3 engine/meta_optimizer.py history
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
META_STATE = STATE_DIR / "meta_optimizer.json"

DEFAULT_DEPLOY_THRESHOLD = 0.80
MAX_META_ITERATIONS = 10
MAX_HISTORY = 50


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def load_meta_state() -> dict:
    """Load meta optimizer state."""
    if META_STATE.exists():
        with open(META_STATE) as f:
            return json.load(f)
    return {
        "prompt_optimizations": [],
        "tool_optimizations": [],
        "topology_optimizations": [],
        "meta_loop_runs": [],
        "deploy_threshold": DEFAULT_DEPLOY_THRESHOLD,
        "total_optimizations": 0,
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


def save_meta_state(state: dict):
    """Save meta optimizer state (atomic write)."""
    # Trim history
    for key in ("prompt_optimizations", "tool_optimizations",
                "topology_optimizations", "meta_loop_runs"):
        if key in state and len(state[key]) > MAX_HISTORY:
            state[key] = state[key][-MAX_HISTORY:]
    _atomic_write(META_STATE, state)


# ---------------------------------------------------------------------------
# Optimizer 1: PROMPT OPTIMIZER
# ---------------------------------------------------------------------------

def cmd_optimize_prompt(node_id: str, current_prompt: str, gradient_json: str):
    """Optimize a node's prompt based on its language gradient.

    Takes the gradient (blame attribution + suggested fixes) and produces
    a concrete rewritten prompt.

    Strategy: Apply gradient's suggested fixes while preserving core intent.
    """
    state = load_meta_state()

    try:
        gradient = json.loads(gradient_json)
    except json.JSONDecodeError:
        gradient = {"attribution": gradient_json, "suggested_fix": gradient_json}

    blame = gradient.get("blame_score", 0.5)
    attribution = gradient.get("attribution", "")
    suggested_fix = gradient.get("suggested_fix", "")

    # Build optimized prompt based on gradient signals
    optimized = current_prompt

    # Apply fixes based on attribution analysis
    if "error handling" in suggested_fix.lower():
        optimized += "\n\nIMPORTANT: If you encounter any error, describe it clearly and attempt an alternative approach."

    if "minimum output" in suggested_fix.lower() or "non-empty" in suggested_fix.lower():
        optimized += "\n\nYou MUST produce a substantive, non-empty response."

    if "specific instructions" in suggested_fix.lower() or "more specific" in suggested_fix.lower():
        optimized += "\n\nBe precise and specific in your output. Avoid vague or generic responses."

    if "replace" in suggested_fix.lower() and blame >= 0.7:
        # High blame — restructure the prompt
        optimized = (
            f"[RESTRUCTURED based on failure analysis]\n"
            f"Previous approach failed because: {attribution[:200]}\n"
            f"New instructions: {suggested_fix[:300]}\n\n"
            f"Core task (preserved): {current_prompt[:500]}"
        )

    record = {
        "node_id": node_id,
        "original_prompt_preview": current_prompt[:200],
        "optimized_prompt_preview": optimized[:200],
        "blame_score": blame,
        "attribution": attribution[:200],
        "optimization_type": "REPLACE" if blame >= 0.7 else "AUGMENT",
        "timestamp": now(),
    }
    state["prompt_optimizations"].append(record)
    state["total_optimizations"] += 1
    save_meta_state(state)

    print(json.dumps({
        "status": "prompt_optimized",
        "node_id": node_id,
        "optimization_type": record["optimization_type"],
        "optimized_prompt": optimized,
        "blame_score": blame,
    }))


# ---------------------------------------------------------------------------
# Optimizer 2: TOOL OPTIMIZER
# ---------------------------------------------------------------------------

def cmd_optimize_tools(node_id: str, tools_json: str, gradient_json: str):
    """Optimize which tools a node has access to based on gradients.

    Analyzes:
    - Were tools used that shouldn't have been?
    - Were needed tools missing?
    - Should tool ordering/priority change?
    """
    state = load_meta_state()

    try:
        tools = json.loads(tools_json)
    except json.JSONDecodeError:
        tools = [tools_json]

    try:
        gradient = json.loads(gradient_json)
    except json.JSONDecodeError:
        gradient = {"attribution": gradient_json}

    attribution = gradient.get("attribution", "")
    blame = gradient.get("blame_score", 0.5)

    recommendations = []

    # Analyze tool usage patterns from gradient
    if "error" in attribution.lower() or "failed" in attribution.lower():
        recommendations.append({
            "action": "ADD",
            "tool": "error_recovery",
            "reason": "Node produced errors — add error recovery tool",
        })

    if "empty" in attribution.lower() or "minimal" in attribution.lower():
        recommendations.append({
            "action": "ADD",
            "tool": "output_validator",
            "reason": "Node produced insufficient output — add validation tool",
        })

    if blame < 0.1 and len(tools) > 3:
        recommendations.append({
            "action": "SIMPLIFY",
            "tool": None,
            "reason": "Node is performing well with many tools — consider simplifying",
        })

    if blame >= 0.5:
        recommendations.append({
            "action": "REVIEW",
            "tool": None,
            "reason": f"High blame ({blame}) — review all tool configurations for this node",
        })

    record = {
        "node_id": node_id,
        "current_tools": tools[:10],
        "recommendations": recommendations,
        "blame_score": blame,
        "timestamp": now(),
    }
    state["tool_optimizations"].append(record)
    state["total_optimizations"] += 1
    save_meta_state(state)

    print(json.dumps({
        "status": "tools_optimized",
        "node_id": node_id,
        "recommendations": recommendations,
        "current_tool_count": len(tools),
    }))


# ---------------------------------------------------------------------------
# Optimizer 3: TOPOLOGY OPTIMIZER
# ---------------------------------------------------------------------------

def cmd_optimize_topology(pipeline_json: str, gradient_json: str):
    """Optimize the pipeline DAG structure based on gradients.

    Analyzes whether:
    - Nodes should be added (missing capabilities)
    - Nodes should be removed (unnecessary complexity)
    - Node ordering should change (wrong dependency flow)
    - Nodes should be parallelized (independent operations)
    """
    state = load_meta_state()

    try:
        pipeline = json.loads(pipeline_json)
    except json.JSONDecodeError:
        pipeline = {"nodes": [pipeline_json]}

    try:
        gradients = json.loads(gradient_json)
    except json.JSONDecodeError:
        gradients = [{"attribution": gradient_json}]

    if not isinstance(gradients, list):
        gradients = [gradients]

    recommendations = []

    # Analyze gradient patterns across nodes
    high_blame_nodes = [g for g in gradients if g.get("blame_score", 0) >= 0.5]
    low_blame_nodes = [g for g in gradients if g.get("blame_score", 0) < 0.1]

    # Pattern: Multiple high-blame nodes → pipeline may need restructuring
    if len(high_blame_nodes) >= 2:
        recommendations.append({
            "action": "RESTRUCTURE",
            "detail": f"{len(high_blame_nodes)} nodes with high blame — consider redesigning this section of the pipeline",
            "affected_nodes": [g.get("node_id", "?") for g in high_blame_nodes],
        })

    # Pattern: Early node has high blame → error propagates downstream
    if gradients and gradients[0].get("blame_score", 0) >= 0.5:
        recommendations.append({
            "action": "ADD_VALIDATION",
            "detail": "First node has high blame — add a validation/preprocessing node before it",
            "position": "before_first",
        })

    # Pattern: Many low-blame nodes → pipeline may be over-complicated
    if len(low_blame_nodes) > len(gradients) * 0.7 and len(gradients) > 3:
        recommendations.append({
            "action": "SIMPLIFY",
            "detail": f"{len(low_blame_nodes)}/{len(gradients)} nodes are neutral — consider merging or removing redundant nodes",
        })

    # Pattern: Sequential nodes could be parallelized
    nodes = pipeline.get("nodes", [])
    if len(nodes) >= 3:
        recommendations.append({
            "action": "PARALLELIZE",
            "detail": "Check if any sequential nodes have independent inputs — they could run in parallel",
        })

    record = {
        "pipeline_size": len(nodes) if isinstance(nodes, list) else 1,
        "gradient_count": len(gradients),
        "recommendations": recommendations,
        "high_blame_count": len(high_blame_nodes),
        "timestamp": now(),
    }
    state["topology_optimizations"].append(record)
    state["total_optimizations"] += 1
    save_meta_state(state)

    print(json.dumps({
        "status": "topology_optimized",
        "recommendations": recommendations,
        "pipeline_size": record["pipeline_size"],
    }))


# ---------------------------------------------------------------------------
# Meta-Prompt Optimization Loop (OpenAI Cookbook Pattern)
# ---------------------------------------------------------------------------

def cmd_meta_loop(current_prompt: str, test_results_json: str, grader_feedback_json: str):
    """Run one iteration of the meta-prompt optimization loop.

    1. Receive grader feedback (from multi_grader.py)
    2. Analyze what dimensions are below threshold
    3. Generate an optimized prompt addressing weak dimensions
    4. Return the optimized prompt for re-evaluation

    The caller loops until threshold is met or max iterations reached.
    """
    state = load_meta_state()

    try:
        test_results = json.loads(test_results_json)
    except json.JSONDecodeError:
        test_results = {"results": test_results_json}

    try:
        grader_feedback = json.loads(grader_feedback_json)
    except json.JSONDecodeError:
        grader_feedback = [{"dimension": "overall", "score": 0.5, "feedback": grader_feedback_json}]

    if not isinstance(grader_feedback, list):
        grader_feedback = [grader_feedback]

    # Identify weak dimensions
    threshold = state.get("deploy_threshold", DEFAULT_DEPLOY_THRESHOLD)
    weak_dimensions = [g for g in grader_feedback if g.get("score", 0) < threshold]
    strong_dimensions = [g for g in grader_feedback if g.get("score", 0) >= threshold]

    # Compute aggregate score
    if grader_feedback:
        avg_score = sum(g.get("score", 0) for g in grader_feedback) / len(grader_feedback)
    else:
        avg_score = 0.0

    # Generate optimized prompt
    optimized_prompt = current_prompt

    if weak_dimensions:
        # Add targeted improvements for each weak dimension
        improvements = []
        for dim in weak_dimensions:
            feedback = dim.get("feedback", "")
            dimension = dim.get("dimension", "unknown")
            improvements.append(
                f"[IMPROVEMENT for {dimension}]: {feedback[:200]}"
            )

        optimized_prompt += "\n\n--- Meta-Optimization Improvements ---\n"
        optimized_prompt += "\n".join(improvements)

    # Determine if we should deploy or continue optimizing
    deploy = avg_score >= threshold
    iterations = len(state["meta_loop_runs"]) + 1
    max_reached = iterations >= MAX_META_ITERATIONS

    record = {
        "iteration": iterations,
        "avg_score": round(avg_score, 3),
        "threshold": threshold,
        "weak_dimensions": len(weak_dimensions),
        "strong_dimensions": len(strong_dimensions),
        "deploy": deploy,
        "max_reached": max_reached,
        "timestamp": now(),
    }
    state["meta_loop_runs"].append(record)
    save_meta_state(state)

    print(json.dumps({
        "status": "deploy" if deploy else ("max_iterations" if max_reached else "continue"),
        "iteration": iterations,
        "avg_score": round(avg_score, 3),
        "threshold": threshold,
        "weak_dimensions": [{
            "dimension": d.get("dimension"),
            "score": d.get("score"),
            "feedback": d.get("feedback", "")[:200],
        } for d in weak_dimensions],
        "optimized_prompt": optimized_prompt,
        "deploy": deploy,
    }))


# ---------------------------------------------------------------------------
# Threshold-Gated Deployment
# ---------------------------------------------------------------------------

def cmd_threshold_check(score: float, threshold: float = None):
    """Check if a score meets the deployment threshold.

    This is the gate that prevents deploying underperforming configurations.
    """
    state = load_meta_state()
    if threshold is None:
        threshold = state.get("deploy_threshold", DEFAULT_DEPLOY_THRESHOLD)

    passed = score >= threshold
    margin = round(score - threshold, 3)

    print(json.dumps({
        "score": score,
        "threshold": threshold,
        "passed": passed,
        "margin": margin,
        "recommendation": "DEPLOY" if passed else "CONTINUE_OPTIMIZING",
    }))


# ---------------------------------------------------------------------------
# Status & History
# ---------------------------------------------------------------------------

def cmd_status():
    """Show meta optimizer status."""
    state = load_meta_state()

    print(json.dumps({
        "total_optimizations": state["total_optimizations"],
        "prompt_optimizations": len(state["prompt_optimizations"]),
        "tool_optimizations": len(state["tool_optimizations"]),
        "topology_optimizations": len(state["topology_optimizations"]),
        "meta_loop_runs": len(state["meta_loop_runs"]),
        "deploy_threshold": state.get("deploy_threshold", DEFAULT_DEPLOY_THRESHOLD),
        "last_meta_loop": state["meta_loop_runs"][-1] if state["meta_loop_runs"] else None,
    }))


def cmd_history():
    """Show optimization history."""
    state = load_meta_state()

    print(json.dumps({
        "recent_prompt_opts": state["prompt_optimizations"][-5:],
        "recent_tool_opts": state["tool_optimizations"][-5:],
        "recent_topology_opts": state["topology_optimizations"][-5:],
        "meta_loop_history": state["meta_loop_runs"][-10:],
    }))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "optimize-prompt":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: optimize-prompt <node_id> <current_prompt> <gradient_json>"}))
            sys.exit(1)
        cmd_optimize_prompt(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "optimize-tools":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: optimize-tools <node_id> <tools_json> <gradient_json>"}))
            sys.exit(1)
        cmd_optimize_tools(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "optimize-topology":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: optimize-topology <pipeline_json> <gradient_json>"}))
            sys.exit(1)
        cmd_optimize_topology(sys.argv[2], sys.argv[3])
    elif cmd == "meta-loop":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: meta-loop <prompt> <test_results_json> <grader_feedback_json>"}))
            sys.exit(1)
        cmd_meta_loop(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "threshold-check":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: threshold-check <score> [threshold]"}))
            sys.exit(1)
        threshold = float(sys.argv[3]) if len(sys.argv) > 3 else None
        cmd_threshold_check(float(sys.argv[2]), threshold)
    elif cmd == "status":
        cmd_status()
    elif cmd == "history":
        cmd_history()
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
