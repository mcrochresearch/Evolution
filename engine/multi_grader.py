#!/usr/bin/env python3
"""
MULTI GRADER — N Independent Graders with Dimensional Scoring.

Inspired by the OpenAI Cookbook meta-prompt optimization pattern. Instead of
one evaluator, use N independent graders each assessing a different quality
dimension. This prevents the optimizer from over-indexing on one dimension.

Default grading dimensions:
1. CORRECTNESS: Does the output solve the stated problem?
2. COMPLETENESS: Does it address all aspects of the task?
3. EFFICIENCY: Is the solution efficient (no unnecessary complexity)?
4. ROBUSTNESS: Does it handle edge cases and failure modes?

Custom graders can be added for domain-specific evaluation.

Feed all N scores + critiques to meta_optimizer.py's meta-loop for
multi-dimensional prompt optimization.

Usage:
    python3 engine/multi_grader.py grade <output> <task_description> [test_results_json]
    python3 engine/multi_grader.py add-grader <name> <dimension> <criteria>
    python3 engine/multi_grader.py remove-grader <name>
    python3 engine/multi_grader.py list-graders
    python3 engine/multi_grader.py aggregate <grades_json>
    python3 engine/multi_grader.py history
    python3 engine/multi_grader.py calibrate <grader_name> <actual_score>
"""

import json
import os
import re
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
GRADER_STATE = STATE_DIR / "multi_grader.json"
MAX_HISTORY = 100


# ---------------------------------------------------------------------------
# Default Graders
# ---------------------------------------------------------------------------

DEFAULT_GRADERS = [
    {
        "name": "correctness",
        "dimension": "correctness",
        "criteria": "Does the output correctly solve the stated problem? Score 0.0 if wrong, 0.5 if partially correct, 1.0 if fully correct.",
        "weight": 0.35,
        "calibration_offset": 0.0,
    },
    {
        "name": "completeness",
        "dimension": "completeness",
        "criteria": "Does the output address ALL aspects of the task? Score 0.0 if major gaps, 0.5 if some missing, 1.0 if complete.",
        "weight": 0.25,
        "calibration_offset": 0.0,
    },
    {
        "name": "efficiency",
        "dimension": "efficiency",
        "criteria": "Is the solution efficient? No unnecessary complexity, redundancy, or over-engineering? Score 0.0 if bloated, 0.5 if acceptable, 1.0 if clean and minimal.",
        "weight": 0.20,
        "calibration_offset": 0.0,
    },
    {
        "name": "robustness",
        "dimension": "robustness",
        "criteria": "Does it handle edge cases and failure modes? Error handling, validation, fallbacks? Score 0.0 if fragile, 0.5 if basic, 1.0 if robust.",
        "weight": 0.20,
        "calibration_offset": 0.0,
    },
]


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def load_grader_state() -> dict:
    """Load grader state."""
    if GRADER_STATE.exists():
        with open(GRADER_STATE) as f:
            return json.load(f)
    return {
        "graders": DEFAULT_GRADERS,
        "grading_history": [],
        "calibration_data": {},
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


def save_grader_state(state: dict):
    """Save grader state (atomic write)."""
    if len(state.get("grading_history", [])) > MAX_HISTORY:
        state["grading_history"] = state["grading_history"][-MAX_HISTORY:]
    # Trim calibration data per grader to prevent unbounded growth
    for grader_name, cal_data in state.get("calibration_data", {}).items():
        if len(cal_data) > 50:
            state["calibration_data"][grader_name] = cal_data[-50:]
    _atomic_write(GRADER_STATE, state)


# ---------------------------------------------------------------------------
# Grading Engine
# ---------------------------------------------------------------------------

def cmd_grade(output: str, task_description: str, test_results: dict = None):
    """Grade output across all dimensions using all configured graders.

    Each grader independently scores the output on its dimension.
    Returns individual grades plus a weighted aggregate score.
    """
    state = load_grader_state()
    graders = state["graders"]

    grades = []
    for grader in graders:
        score, feedback = _grade_dimension(
            output, task_description, grader, test_results
        )
        # Apply calibration offset
        calibrated_score = max(0.0, min(1.0, score + grader.get("calibration_offset", 0.0)))

        grades.append({
            "dimension": grader["dimension"],
            "grader": grader["name"],
            "score": round(calibrated_score, 3),
            "raw_score": round(score, 3),
            "feedback": feedback,
            "weight": grader["weight"],
        })

    # Compute weighted aggregate
    total_weight = sum(g["weight"] for g in grades)
    if total_weight > 0:
        aggregate = sum(g["score"] * g["weight"] for g in grades) / total_weight
    else:
        aggregate = sum(g["score"] for g in grades) / max(len(grades), 1)

    result = {
        "aggregate_score": round(aggregate, 3),
        "grades": grades,
        "grader_count": len(grades),
        "task_preview": task_description[:200],
        "output_preview": output[:200],
        "timestamp": now(),
    }

    # Save to history
    state["grading_history"].append({
        "aggregate_score": result["aggregate_score"],
        "dimension_scores": {g["dimension"]: g["score"] for g in grades},
        "timestamp": now(),
    })
    save_grader_state(state)

    print(json.dumps(result))


def _grade_dimension(output: str, task_desc: str, grader: dict,
                     test_results: dict = None) -> tuple:
    """Grade a single dimension using heuristic analysis.

    In production with LLM access, this would be an LLM call with the
    grader's criteria as the evaluation prompt. Here we use heuristics.

    Returns (score, feedback).
    """
    dimension = grader["dimension"]
    output_lower = output.lower()
    task_lower = task_desc.lower()

    if dimension == "correctness":
        return _grade_correctness(output_lower, task_lower, test_results)
    elif dimension == "completeness":
        return _grade_completeness(output_lower, task_lower)
    elif dimension == "efficiency":
        return _grade_efficiency(output)
    elif dimension == "robustness":
        return _grade_robustness(output_lower)
    else:
        # Custom grader — use generic keyword analysis
        return _grade_generic(output_lower, task_lower, grader)


def _grade_correctness(output: str, task: str, test_results: dict = None) -> tuple:
    """Grade correctness."""
    score = 0.5  # Default: assume partially correct

    # If test results available, use them directly
    if test_results:
        passed = test_results.get("tests_passing", 0)
        total = test_results.get("tests_total", 1)
        if total > 0:
            score = passed / total
            return score, f"Test results: {passed}/{total} passing"

    # Heuristic: check for error indicators
    errors = ["error", "traceback", "exception", "failed", "syntaxerror",
              "typeerror", "nameerror", "valueerror"]
    error_count = sum(1 for e in errors if e in output)
    if error_count >= 2:
        score = 0.1
        return score, f"Multiple error indicators found ({error_count})"
    elif error_count == 1:
        score = 0.3
        return score, "One error indicator found"

    # Check if output is empty
    if len(output.strip()) < 10:
        return 0.0, "Output is empty or trivially short"

    # Check task keyword coverage
    task_words = set(task.split()) - {"the", "a", "an", "is", "to", "and", "or", "in", "of"}
    output_words = set(output.split())
    coverage = len(task_words & output_words) / max(len(task_words), 1)
    if coverage > 0.5:
        score = 0.7
    elif coverage > 0.3:
        score = 0.5

    return score, f"Task keyword coverage: {coverage:.0%}"


def _grade_completeness(output: str, task: str) -> tuple:
    """Grade completeness — does it address all aspects?"""
    # Split task into sub-requirements (sentences)
    task_sentences = [s.strip() for s in re.split(r'[.;]', task) if len(s.strip()) > 10]
    if not task_sentences:
        return 0.7, "Could not parse task requirements"

    addressed = 0
    for req in task_sentences:
        req_words = set(req.split()) - {"the", "a", "an", "is", "to", "and", "or"}
        output_words = set(output.split())
        if len(req_words & output_words) / max(len(req_words), 1) > 0.3:
            addressed += 1

    score = addressed / len(task_sentences) if task_sentences else 0.5
    return round(score, 2), f"Addressed {addressed}/{len(task_sentences)} task requirements"


def _grade_efficiency(output: str) -> tuple:
    """Grade efficiency — is it clean and minimal?"""
    lines = output.split("\n")
    total_lines = len(lines)

    # Check for duplication (repeated lines)
    unique_lines = set(l.strip() for l in lines if l.strip())
    duplication_ratio = 1 - (len(unique_lines) / max(total_lines, 1))

    # Check for excessive verbosity
    word_count = len(output.split())

    if duplication_ratio > 0.3:
        score = 0.3
        feedback = f"High duplication ({duplication_ratio:.0%} repeated lines)"
    elif word_count > 5000:
        score = 0.4
        feedback = f"Very verbose ({word_count} words) — may contain unnecessary content"
    elif word_count > 2000:
        score = 0.6
        feedback = f"Moderately verbose ({word_count} words)"
    else:
        score = 0.8
        feedback = f"Concise ({word_count} words, {duplication_ratio:.0%} duplication)"

    return round(score, 2), feedback


def _grade_robustness(output: str) -> tuple:
    """Grade robustness — error handling, edge cases."""
    robustness_signals = 0
    total_signals = 5

    # Check for error handling keywords
    if any(kw in output for kw in ["try", "except", "catch", "error", "handle"]):
        robustness_signals += 1
    if any(kw in output for kw in ["validate", "check", "verify", "assert"]):
        robustness_signals += 1
    if any(kw in output for kw in ["edge case", "boundary", "limit", "overflow"]):
        robustness_signals += 1
    if any(kw in output for kw in ["fallback", "default", "recovery", "retry"]):
        robustness_signals += 1
    if any(kw in output for kw in ["null", "none", "empty", "missing"]):
        robustness_signals += 1

    score = robustness_signals / total_signals
    return round(score, 2), f"Robustness signals: {robustness_signals}/{total_signals}"


def _grade_generic(output: str, task: str, grader: dict) -> tuple:
    """Grade using a custom grader's criteria via keyword matching."""
    criteria = grader.get("criteria", "").lower()

    # Extract key evaluation words from criteria
    eval_words = set(criteria.split()) - {"the", "a", "an", "is", "to", "and", "or",
                                           "score", "if", "does", "0.0", "0.5", "1.0"}
    output_words = set(output.split())
    overlap = len(eval_words & output_words) / max(len(eval_words), 1)

    score = min(1.0, overlap * 3)  # Scale up
    return round(score, 2), f"Custom grader '{grader['name']}': {overlap:.0%} criteria signal coverage"


# ---------------------------------------------------------------------------
# Grader Management
# ---------------------------------------------------------------------------

def cmd_add_grader(name: str, dimension: str, criteria: str):
    """Add a custom grader."""
    state = load_grader_state()

    # Check for duplicate
    if any(g["name"] == name for g in state["graders"]):
        print(json.dumps({"error": f"Grader '{name}' already exists"}))
        sys.exit(1)

    # Compute weight (equal distribution with existing)
    num_graders = len(state["graders"]) + 1
    new_weight = round(1.0 / num_graders, 2)

    grader = {
        "name": name,
        "dimension": dimension,
        "criteria": criteria,
        "weight": new_weight,
        "calibration_offset": 0.0,
    }
    state["graders"].append(grader)

    # Rebalance weights
    for g in state["graders"]:
        g["weight"] = round(1.0 / num_graders, 2)

    save_grader_state(state)
    print(json.dumps({"status": "grader_added", "grader": grader, "total_graders": num_graders}))


def cmd_remove_grader(name: str):
    """Remove a grader."""
    state = load_grader_state()

    state["graders"] = [g for g in state["graders"] if g["name"] != name]

    # Rebalance weights
    if state["graders"]:
        for g in state["graders"]:
            g["weight"] = round(1.0 / len(state["graders"]), 2)

    save_grader_state(state)
    print(json.dumps({"status": "grader_removed", "name": name, "remaining": len(state["graders"])}))


def cmd_list_graders():
    """List all configured graders."""
    state = load_grader_state()
    print(json.dumps({
        "graders": state["graders"],
        "total": len(state["graders"]),
    }))


def cmd_aggregate(grades_json: str):
    """Aggregate multiple grades into a single score."""
    try:
        grades = json.loads(grades_json)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON"}))
        sys.exit(1)

    if not isinstance(grades, list):
        grades = [grades]

    total_weight = sum(g.get("weight", 1.0) for g in grades)
    if total_weight > 0:
        weighted_sum = sum(g.get("score", 0) * g.get("weight", 1.0) for g in grades)
        aggregate = weighted_sum / total_weight
    else:
        aggregate = sum(g.get("score", 0) for g in grades) / max(len(grades), 1)

    print(json.dumps({
        "aggregate_score": round(aggregate, 3),
        "grade_count": len(grades),
        "dimension_scores": {g.get("dimension", f"dim_{i}"): g.get("score", 0)
                            for i, g in enumerate(grades)},
    }))


def cmd_calibrate(grader_name: str, actual_score: float):
    """Calibrate a grader by recording actual vs predicted score.

    Over time, accumulates calibration data and adjusts the grader's
    offset to reduce systematic bias.
    """
    state = load_grader_state()

    if grader_name not in state["calibration_data"]:
        state["calibration_data"][grader_name] = []

    # Find grader's last predicted score
    last_history = state["grading_history"][-1] if state["grading_history"] else None
    predicted = 0.5
    if last_history and grader_name in last_history.get("dimension_scores", {}):
        predicted = last_history["dimension_scores"][grader_name]

    state["calibration_data"][grader_name].append({
        "predicted": predicted,
        "actual": actual_score,
        "timestamp": now(),
    })

    # Compute and apply calibration offset
    cal_data = state["calibration_data"][grader_name]
    if len(cal_data) >= 3:
        errors = [d["actual"] - d["predicted"] for d in cal_data[-10:]]
        avg_error = sum(errors) / len(errors)

        for g in state["graders"]:
            if g["name"] == grader_name:
                g["calibration_offset"] = round(avg_error, 3)
                break

    save_grader_state(state)
    print(json.dumps({
        "status": "calibrated",
        "grader": grader_name,
        "predicted": predicted,
        "actual": actual_score,
        "data_points": len(state["calibration_data"][grader_name]),
    }))


def cmd_history():
    """Show grading history."""
    state = load_grader_state()
    print(json.dumps({
        "total_gradings": len(state["grading_history"]),
        "recent": state["grading_history"][-10:],
        "calibration_data": {k: len(v) for k, v in state.get("calibration_data", {}).items()},
    }))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "grade":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: grade <output> <task_description> [test_results_json]"}))
            sys.exit(1)
        test_results = None
        if len(sys.argv) > 4:
            try:
                test_results = json.loads(sys.argv[4])
            except json.JSONDecodeError:
                test_results = None
        cmd_grade(sys.argv[2], sys.argv[3], test_results)
    elif cmd == "add-grader":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: add-grader <name> <dimension> <criteria>"}))
            sys.exit(1)
        cmd_add_grader(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "remove-grader":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: remove-grader <name>"}))
            sys.exit(1)
        cmd_remove_grader(sys.argv[2])
    elif cmd == "list-graders":
        cmd_list_graders()
    elif cmd == "aggregate":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: aggregate <grades_json>"}))
            sys.exit(1)
        cmd_aggregate(sys.argv[2])
    elif cmd == "calibrate":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: calibrate <grader_name> <actual_score>"}))
            sys.exit(1)
        cmd_calibrate(sys.argv[2], float(sys.argv[3]))
    elif cmd == "history":
        cmd_history()
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
