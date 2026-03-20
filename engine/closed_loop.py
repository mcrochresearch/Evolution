#!/usr/bin/env python3
"""
CLOSED LOOP — Per-Stage Validation + Cross-Model Adversarial Critique.

Inspired by AIAnytime's Self-Healing-RAG (closed-loop feedback architecture)
and cross-model adversarial critique patterns. Moves from open-loop
(execute → hope for the best) to closed-loop (execute → validate → correct).

Two main features:

1. STAGE VALIDATION: Each pipeline stage validates its own output before
   passing to the next stage. If validation fails, the stage retries
   with correction feedback.

2. ADVERSARIAL CRITIQUE: Use a different "model perspective" to critique
   each stage's output. The critic tries to find flaws; the executor
   tries to fix them. This adversarial tension produces more robust output.

Usage:
    python3 engine/closed_loop.py validate <stage_id> <output> <criteria_json>
    python3 engine/closed_loop.py critique <output> <task_description> [perspective]
    python3 engine/closed_loop.py heal <stage_id> <output> <validation_result_json>
    python3 engine/closed_loop.py pipeline-check <pipeline_results_json>
    python3 engine/closed_loop.py configure <stage_id> <max_retries> <validation_criteria_json>
    python3 engine/closed_loop.py status
    python3 engine/closed_loop.py history
"""

import json
import os
import re
import sys
from pathlib import Path

try:
    from engine.stats import now
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now

ENGINE_DIR = Path(__file__).parent
PROJECT_DIR = ENGINE_DIR.parent
STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
CLOSED_LOOP_STATE = STATE_DIR / "closed_loop.json"
MAX_HISTORY = 100

# Default adversarial perspectives for cross-model critique
CRITIQUE_PERSPECTIVES = {
    "skeptic": {
        "name": "Skeptic",
        "instruction": "Challenge every assumption. What could go wrong? What edge cases are missed? What would a malicious user do? Find the weakest points.",
    },
    "pragmatist": {
        "name": "Pragmatist",
        "instruction": "Is this practical? Is it over-engineered? Could it be simpler? What's the maintenance burden? Would a real user find this usable?",
    },
    "security": {
        "name": "Security Auditor",
        "instruction": "Check for injection vulnerabilities, data leaks, authentication bypasses, improper validation, sensitive data exposure, and OWASP Top 10 issues.",
    },
    "performance": {
        "name": "Performance Engineer",
        "instruction": "Check for O(n^2) algorithms, unnecessary allocations, missing caching, N+1 queries, blocking operations, and memory leaks.",
    },
}


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Load closed loop state."""
    if CLOSED_LOOP_STATE.exists():
        with open(CLOSED_LOOP_STATE) as f:
            return json.load(f)
    return {
        "stage_configs": {},
        "validation_history": [],
        "critique_history": [],
        "healing_history": [],
        "total_validations": 0,
        "total_heals": 0,
        "total_critiques": 0,
    }


def save_state(state: dict):
    """Save closed loop state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    for key in ("validation_history", "critique_history", "healing_history"):
        if key in state and len(state[key]) > MAX_HISTORY:
            state[key] = state[key][-MAX_HISTORY:]
    with open(CLOSED_LOOP_STATE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Stage Validation — Closed-Loop Output Checking
# ---------------------------------------------------------------------------

def cmd_validate(stage_id: str, output: str, criteria_json: str):
    """Validate a stage's output against configurable criteria.

    Criteria is a list of checks, each with:
    - name: Check name
    - type: "non_empty", "no_errors", "contains", "regex", "min_length", "max_length"
    - value: (optional) parameter for the check

    Returns pass/fail per criterion plus overall validation result.
    """
    state = load_state()

    try:
        criteria = json.loads(criteria_json)
    except json.JSONDecodeError:
        criteria = [{"name": "non_empty", "type": "non_empty"}]

    if not isinstance(criteria, list):
        criteria = [criteria]

    results = []
    for check in criteria:
        check_name = check.get("name", check.get("type", "unknown"))
        check_type = check.get("type", "non_empty")
        check_value = check.get("value", "")

        passed, detail = _run_check(output, check_type, check_value)
        results.append({
            "check": check_name,
            "type": check_type,
            "passed": passed,
            "detail": detail,
        })

    all_passed = all(r["passed"] for r in results)
    failed_checks = [r for r in results if not r["passed"]]

    record = {
        "stage_id": stage_id,
        "passed": all_passed,
        "checks": len(results),
        "failures": len(failed_checks),
        "failed_checks": [r["check"] for r in failed_checks],
        "timestamp": now(),
    }
    state["validation_history"].append(record)
    state["total_validations"] += 1
    save_state(state)

    print(json.dumps({
        "status": "passed" if all_passed else "failed",
        "stage_id": stage_id,
        "results": results,
        "all_passed": all_passed,
        "failed_count": len(failed_checks),
        "correction_needed": not all_passed,
        "correction_hints": [r["detail"] for r in failed_checks] if failed_checks else [],
    }))


def _run_check(output: str, check_type: str, check_value: str) -> tuple:
    """Run a single validation check. Returns (passed, detail)."""
    if check_type == "non_empty":
        passed = len(output.strip()) > 0
        return passed, "Output is non-empty" if passed else "Output is empty"

    elif check_type == "no_errors":
        error_keywords = ["error", "traceback", "exception", "failed",
                         "syntaxerror", "typeerror", "referenceerror"]
        found = [kw for kw in error_keywords if kw in output.lower()]
        passed = len(found) == 0
        return passed, "No errors found" if passed else f"Error keywords found: {found}"

    elif check_type == "contains":
        passed = check_value.lower() in output.lower()
        return passed, f"Contains '{check_value}'" if passed else f"Missing '{check_value}'"

    elif check_type == "not_contains":
        passed = check_value.lower() not in output.lower()
        return passed, f"Does not contain '{check_value}'" if passed else f"Unexpectedly contains '{check_value}'"

    elif check_type == "regex":
        try:
            passed = bool(re.search(check_value, output, re.MULTILINE))
            return passed, f"Regex '{check_value}' matched" if passed else f"Regex '{check_value}' not found"
        except re.error as e:
            return False, f"Invalid regex: {e}"

    elif check_type == "min_length":
        min_len = int(check_value) if check_value else 10
        passed = len(output) >= min_len
        return passed, f"Length {len(output)} >= {min_len}" if passed else f"Too short: {len(output)} < {min_len}"

    elif check_type == "max_length":
        max_len = int(check_value) if check_value else 10000
        passed = len(output) <= max_len
        return passed, f"Length {len(output)} <= {max_len}" if passed else f"Too long: {len(output)} > {max_len}"

    elif check_type == "json_valid":
        try:
            json.loads(output)
            return True, "Valid JSON"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"

    elif check_type == "no_passivity":
        passive_patterns = [
            r"would you like",
            r"should i",
            r"what do you think",
            r"option [a-d]",
            r"choose (one|from|between)",
        ]
        found = [p for p in passive_patterns if re.search(p, output.lower())]
        passed = len(found) == 0
        return passed, "No passive patterns" if passed else f"Passive patterns found: {found}"

    else:
        return True, f"Unknown check type '{check_type}' — auto-passed"


# ---------------------------------------------------------------------------
# Adversarial Critique — Cross-Perspective Analysis
# ---------------------------------------------------------------------------

def cmd_critique(output: str, task_description: str, perspective: str = None):
    """Critique output from an adversarial perspective.

    Uses different critique lenses to find weaknesses that a single
    perspective might miss. In production with LLM access, each perspective
    would be a separate LLM call with a different system prompt.
    Here we use heuristic analysis.
    """
    state = load_state()

    if perspective and perspective in CRITIQUE_PERSPECTIVES:
        perspectives = {perspective: CRITIQUE_PERSPECTIVES[perspective]}
    else:
        perspectives = CRITIQUE_PERSPECTIVES

    critiques = []
    for persp_id, persp in perspectives.items():
        issues = _analyze_perspective(output, task_description, persp_id)
        critiques.append({
            "perspective": persp["name"],
            "perspective_id": persp_id,
            "issues": issues,
            "issue_count": len(issues),
            "severity": max((i.get("severity", "low") for i in issues), default="none",
                           key=lambda s: {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}.get(s, 0)),
        })

    total_issues = sum(c["issue_count"] for c in critiques)
    critical_issues = [
        issue for c in critiques for issue in c["issues"]
        if issue.get("severity") in ("high", "critical")
    ]

    record = {
        "total_issues": total_issues,
        "critical_issues": len(critical_issues),
        "perspectives_used": len(critiques),
        "timestamp": now(),
    }
    state["critique_history"].append(record)
    state["total_critiques"] += 1
    save_state(state)

    print(json.dumps({
        "status": "critique_complete",
        "critiques": critiques,
        "total_issues": total_issues,
        "critical_issues": critical_issues,
        "needs_healing": total_issues > 0,
        "task_preview": task_description[:200],
    }))


def _analyze_perspective(output: str, task: str, perspective: str) -> list:
    """Analyze output from a specific adversarial perspective."""
    issues = []
    output_lower = output.lower()

    if perspective == "skeptic":
        # Look for assumptions, missing edge cases
        if "assume" in output_lower or "assuming" in output_lower:
            issues.append({
                "issue": "Contains explicit assumptions — these may be wrong",
                "severity": "medium",
            })
        if len(output) < 50:
            issues.append({
                "issue": "Output suspiciously short — may be oversimplified",
                "severity": "medium",
            })
        if "todo" in output_lower or "fixme" in output_lower:
            issues.append({
                "issue": "Contains TODO/FIXME — incomplete implementation",
                "severity": "high",
            })
        if "hardcod" in output_lower:
            issues.append({
                "issue": "Contains hardcoded values — may not generalize",
                "severity": "medium",
            })

    elif perspective == "pragmatist":
        lines = output.split("\n")
        if len(lines) > 200:
            issues.append({
                "issue": f"Very long output ({len(lines)} lines) — may be over-engineered",
                "severity": "low",
            })
        if output_lower.count("class ") > 5:
            issues.append({
                "issue": "Many class definitions — possible over-abstraction",
                "severity": "low",
            })
        if "abstract" in output_lower and "factory" in output_lower:
            issues.append({
                "issue": "AbstractFactory pattern detected — are we sure this complexity is needed?",
                "severity": "medium",
            })

    elif perspective == "security":
        # OWASP-style checks
        if "eval(" in output_lower or "exec(" in output_lower:
            issues.append({
                "issue": "Dynamic code execution (eval/exec) — potential injection vulnerability",
                "severity": "critical",
            })
        if "password" in output_lower and ("=" in output_lower or ":" in output_lower):
            issues.append({
                "issue": "Possible hardcoded password or credential",
                "severity": "critical",
            })
        if re.search(r'f["\'].*\{.*\}.*["\'].*sql|query', output_lower):
            issues.append({
                "issue": "Possible SQL injection via f-string interpolation",
                "severity": "critical",
            })
        if "innerhtml" in output_lower or "dangerouslysetinnerhtml" in output_lower:
            issues.append({
                "issue": "Direct HTML injection — XSS vulnerability",
                "severity": "high",
            })
        if ".env" in output_lower and ("open" in output_lower or "read" in output_lower):
            issues.append({
                "issue": "Reading .env file — ensure secrets aren't logged or exposed",
                "severity": "medium",
            })

    elif perspective == "performance":
        # Check for performance anti-patterns
        if re.search(r'for.*for.*for', output_lower):
            issues.append({
                "issue": "Triple nested loop — potential O(n^3) complexity",
                "severity": "high",
            })
        elif re.search(r'for.*for', output_lower):
            # Check if it's in a small scope
            issues.append({
                "issue": "Nested loop detected — verify it's not O(n^2) on large input",
                "severity": "medium",
            })
        if "sleep(" in output_lower or "time.sleep" in output_lower:
            issues.append({
                "issue": "Blocking sleep call — consider async alternatives",
                "severity": "low",
            })
        if "+=" in output and "str" in output_lower:
            issues.append({
                "issue": "Possible string concatenation in loop (O(n^2) for strings)",
                "severity": "medium",
            })

    return issues


# ---------------------------------------------------------------------------
# Self-Healing — Automated Correction
# ---------------------------------------------------------------------------

def cmd_heal(stage_id: str, output: str, validation_result_json: str):
    """Generate correction instructions for a failed validation.

    Takes the failed validation result and produces specific instructions
    for how to fix the output. This is the "healing" part of the closed loop.
    """
    state = load_state()

    try:
        validation = json.loads(validation_result_json)
    except json.JSONDecodeError:
        validation = {"failed_checks": ["unknown"]}

    corrections = []

    # Generate specific corrections for each failure
    failed_checks = validation.get("correction_hints", [])
    if not failed_checks:
        failed_checks = validation.get("failed_checks", [])

    for hint in failed_checks:
        hint_lower = hint.lower() if isinstance(hint, str) else ""

        if "empty" in hint_lower:
            corrections.append({
                "issue": "Empty output",
                "action": "Regenerate with stronger output requirements",
                "prompt_addition": "You MUST produce a non-empty, substantive response.",
            })
        elif "error" in hint_lower:
            corrections.append({
                "issue": "Error in output",
                "action": "Add error handling and retry",
                "prompt_addition": "If your approach produces an error, try an alternative approach.",
            })
        elif "missing" in hint_lower:
            corrections.append({
                "issue": "Missing content",
                "action": "Add the missing content",
                "prompt_addition": f"Your output is missing: {hint}. Include it.",
            })
        elif "passive" in hint_lower:
            corrections.append({
                "issue": "Passive output",
                "action": "Remove questions and menus, just execute",
                "prompt_addition": "Do NOT ask questions or present options. Just do it.",
            })
        else:
            corrections.append({
                "issue": hint[:200] if isinstance(hint, str) else str(hint),
                "action": "Address the validation failure",
                "prompt_addition": f"Fix this issue: {hint}" if isinstance(hint, str) else "Fix the validation failure",
            })

    # Combine all prompt additions into a healing prompt
    healing_prompt = "\n".join(
        f"- {c['prompt_addition']}" for c in corrections
    )

    record = {
        "stage_id": stage_id,
        "corrections": len(corrections),
        "timestamp": now(),
    }
    state["healing_history"].append(record)
    state["total_heals"] += 1
    save_state(state)

    print(json.dumps({
        "status": "healing_instructions_generated",
        "stage_id": stage_id,
        "corrections": corrections,
        "healing_prompt": healing_prompt,
        "retry_recommended": len(corrections) > 0,
    }))


# ---------------------------------------------------------------------------
# Pipeline-Level Check
# ---------------------------------------------------------------------------

def cmd_pipeline_check(pipeline_results_json: str):
    """Check all stages of a pipeline for closed-loop health.

    Takes results from all stages and identifies:
    - Which stages passed/failed
    - Whether healing was effective
    - Overall pipeline health score
    """
    try:
        results = json.loads(pipeline_results_json)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON"}))
        sys.exit(1)

    if not isinstance(results, list):
        results = [results]

    passed_stages = [r for r in results if r.get("passed", r.get("all_passed", False))]
    failed_stages = [r for r in results if not r.get("passed", r.get("all_passed", False))]

    health_score = len(passed_stages) / max(len(results), 1)

    print(json.dumps({
        "pipeline_health": round(health_score, 2),
        "total_stages": len(results),
        "passed_stages": len(passed_stages),
        "failed_stages": len(failed_stages),
        "failed_stage_ids": [r.get("stage_id", "?") for r in failed_stages],
        "needs_healing": len(failed_stages) > 0,
        "recommendation": (
            "Pipeline healthy" if health_score >= 0.8
            else "Pipeline needs attention" if health_score >= 0.5
            else "Pipeline critically unhealthy — multiple stages failing"
        ),
    }))


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def cmd_configure(stage_id: str, max_retries: int, criteria_json: str):
    """Configure validation criteria for a pipeline stage."""
    state = load_state()

    try:
        criteria = json.loads(criteria_json)
    except json.JSONDecodeError:
        criteria = [{"name": "non_empty", "type": "non_empty"}]

    state["stage_configs"][stage_id] = {
        "max_retries": max_retries,
        "criteria": criteria,
        "configured_at": now(),
    }
    save_state(state)

    print(json.dumps({
        "status": "configured",
        "stage_id": stage_id,
        "max_retries": max_retries,
        "criteria_count": len(criteria) if isinstance(criteria, list) else 1,
    }))


# ---------------------------------------------------------------------------
# Status & History
# ---------------------------------------------------------------------------

def cmd_status():
    """Show closed loop status."""
    state = load_state()

    print(json.dumps({
        "total_validations": state["total_validations"],
        "total_heals": state["total_heals"],
        "total_critiques": state["total_critiques"],
        "configured_stages": len(state["stage_configs"]),
        "recent_validations": state["validation_history"][-5:],
        "validation_pass_rate": _compute_pass_rate(state["validation_history"]),
    }))


def _compute_pass_rate(history: list) -> float:
    """Compute validation pass rate from history."""
    if not history:
        return 0.0
    passed = sum(1 for h in history if h.get("passed"))
    return round(passed / len(history), 2)


def cmd_history():
    """Show validation, critique, and healing history."""
    state = load_state()
    print(json.dumps({
        "validation_history": state["validation_history"][-10:],
        "critique_history": state["critique_history"][-10:],
        "healing_history": state["healing_history"][-10:],
    }))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "validate":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: validate <stage_id> <output> <criteria_json>"}))
            sys.exit(1)
        cmd_validate(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "critique":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: critique <output> <task_description> [perspective]"}))
            sys.exit(1)
        persp = sys.argv[4] if len(sys.argv) > 4 else None
        cmd_critique(sys.argv[2], sys.argv[3], persp)
    elif cmd == "heal":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: heal <stage_id> <output> <validation_result_json>"}))
            sys.exit(1)
        cmd_heal(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "pipeline-check":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: pipeline-check <pipeline_results_json>"}))
            sys.exit(1)
        cmd_pipeline_check(sys.argv[2])
    elif cmd == "configure":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: configure <stage_id> <max_retries> <validation_criteria_json>"}))
            sys.exit(1)
        cmd_configure(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    elif cmd == "status":
        cmd_status()
    elif cmd == "history":
        cmd_history()
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
