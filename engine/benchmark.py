#!/usr/bin/env python3
"""
EVOLUTION BENCHMARK ENGINE — Standardized measurement of agent performance.

Measures Evolution against baseline (naive loop) agents on standardized tasks.
Produces structured evidence: fitness trajectories, autonomy scores, convergence
speed, strategy efficiency, and comparative analysis.

This is the infrastructure that turns "probably yes" into data.

Usage:
    python3 engine/benchmark.py define <name> <description> <success_criteria_json>
    python3 engine/benchmark.py list
    python3 engine/benchmark.py run <name> [--baseline]
    python3 engine/benchmark.py record <name> <mode> <cycles> <final_fitness> <data_json>
    python3 engine/benchmark.py compare <name>
    python3 engine/benchmark.py report
    python3 engine/benchmark.py autonomy [--from-state]
    python3 engine/benchmark.py evidence
"""

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from engine.stats import now, wilson_lower, wilson_score, effect_size, sample_sd
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now, wilson_lower, wilson_score, effect_size, sample_sd

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
BENCHMARK_DIR = STATE_DIR / "benchmarks"
TASKS_FILE = BENCHMARK_DIR / "tasks.json"
RESULTS_FILE = BENCHMARK_DIR / "results.jsonl"
EVIDENCE_FILE = BENCHMARK_DIR / "evidence.json"

# ---------------------------------------------------------------------------
# Benchmark task definitions
# ---------------------------------------------------------------------------

BUILTIN_TASKS = [
    {
        "name": "rest-api-crud",
        "description": "Build a REST API with CRUD endpoints, input validation, and error handling",
        "category": "engineering",
        "difficulty": "medium",
        "success_criteria": {
            "min_fitness": 0.80,
            "required_tests": 8,
            "must_build": True,
            "must_lint": True,
        },
        "max_cycles": 40,
        "baseline_estimate": {"cycles": 35, "fitness": 0.70, "human_interventions": 8},
    },
    {
        "name": "auth-middleware",
        "description": "Implement JWT authentication middleware with token refresh and role-based access",
        "category": "engineering",
        "difficulty": "medium",
        "success_criteria": {
            "min_fitness": 0.85,
            "required_tests": 10,
            "must_build": True,
            "must_lint": True,
        },
        "max_cycles": 50,
        "baseline_estimate": {"cycles": 45, "fitness": 0.65, "human_interventions": 12},
    },
    {
        "name": "rate-limiter",
        "description": "Build a distributed rate limiter with sliding window, per-user limits, and graceful degradation",
        "category": "engineering",
        "difficulty": "hard",
        "success_criteria": {
            "min_fitness": 0.85,
            "required_tests": 12,
            "must_build": True,
            "must_lint": True,
        },
        "max_cycles": 60,
        "baseline_estimate": {"cycles": 55, "fitness": 0.55, "human_interventions": 15},
    },
    {
        "name": "cli-tool",
        "description": "Build a CLI tool with subcommands, flag parsing, help text, and config file support",
        "category": "engineering",
        "difficulty": "easy",
        "success_criteria": {
            "min_fitness": 0.90,
            "required_tests": 6,
            "must_build": True,
        },
        "max_cycles": 25,
        "baseline_estimate": {"cycles": 20, "fitness": 0.75, "human_interventions": 5},
    },
    {
        "name": "data-pipeline",
        "description": "Build an ETL pipeline: CSV ingestion, transformation, validation, and JSON output with error recovery",
        "category": "engineering",
        "difficulty": "medium",
        "success_criteria": {
            "min_fitness": 0.85,
            "required_tests": 8,
            "must_build": True,
        },
        "max_cycles": 40,
        "baseline_estimate": {"cycles": 35, "fitness": 0.60, "human_interventions": 10},
    },
]


def _ensure_dirs():
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)


def _load_tasks() -> list:
    if TASKS_FILE.exists():
        return json.loads(TASKS_FILE.read_text())
    return list(BUILTIN_TASKS)


def _save_tasks(tasks: list):
    _ensure_dirs()
    TASKS_FILE.write_text(json.dumps(tasks, indent=2))


def _append_result(record: dict):
    _ensure_dirs()
    fd = os.open(str(RESULTS_FILE), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (json.dumps(record, separators=(",", ":")) + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def _load_results() -> list:
    if not RESULTS_FILE.exists():
        return []
    results = []
    for line in RESULTS_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return results


# ---------------------------------------------------------------------------
# Autonomy metrics
# ---------------------------------------------------------------------------

def compute_autonomy_metrics(state: dict = None) -> dict:
    """Compute autonomy score from evolution state.

    Measures how independently the agent operates:
    - Cycles completed without human intervention
    - Strategy decisions made autonomously
    - Self-corrections (reverts + re-approaches)
    - Stagnation recoveries (plateau detection + pivot)

    Returns a score from 0.0 (fully dependent) to 1.0 (fully autonomous).
    """
    if state is None:
        state_file = STATE_DIR / "evolution.json"
        if not state_file.exists():
            return {"error": "No evolution state found. Run a task first."}
        state = json.loads(state_file.read_text())

    cycles = state.get("cycles", [])
    strategies = state.get("strategies", [])
    graveyard = state.get("graveyard", [])
    total_cycles = len(cycles)

    if total_cycles == 0:
        return {"autonomy_score": 0.0, "total_cycles": 0, "verdict": "No data"}

    # --- Metric 1: Continuous execution (no gaps suggesting human intervention) ---
    # Measure timestamp gaps — large gaps suggest human had to step in
    continuous_runs = 0
    if total_cycles >= 2:
        for i in range(1, len(cycles)):
            try:
                t1 = datetime.fromisoformat(cycles[i - 1].get("timestamp", ""))
                t2 = datetime.fromisoformat(cycles[i].get("timestamp", ""))
                gap = (t2 - t1).total_seconds()
                # Under 5 minutes between cycles = autonomous
                if gap < 300:
                    continuous_runs += 1
            except (ValueError, TypeError):
                continuous_runs += 1  # Missing timestamps = assume autonomous
    continuity_score = continuous_runs / max(total_cycles - 1, 1)

    # --- Metric 2: Strategy diversity (agent makes its own decisions) ---
    unique_strategies_used = len(set(c.get("strategy", "") for c in cycles))
    total_strategies_created = len(strategies) + len(graveyard)
    strategy_score = min(1.0, unique_strategies_used / max(3, 1))  # Using 3+ strategies = full score

    # --- Metric 3: Self-correction rate ---
    reverts = sum(1 for c in cycles if not c.get("kept", True))
    kept = sum(1 for c in cycles if c.get("kept", True))
    # Good agents revert bad changes. Revert rate between 10-40% is healthy.
    if total_cycles > 0:
        revert_rate = reverts / total_cycles
        # Peak at 25% revert rate — too low means not testing, too high means flailing
        self_correction_score = 1.0 - min(1.0, abs(revert_rate - 0.25) * 4)
    else:
        self_correction_score = 0.0

    # --- Metric 4: Fitness trajectory (actually improving without help) ---
    fitness_history = state.get("fitness_history", [])
    if len(fitness_history) >= 5:
        # Linear regression slope on fitness history
        n = len(fitness_history)
        x_mean = (n - 1) / 2
        y_mean = sum(fitness_history) / n
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(fitness_history))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator > 0 else 0
        # Positive slope = improving. Normalize: slope of 0.02/cycle = full score
        trajectory_score = min(1.0, max(0.0, slope / 0.02))
    else:
        trajectory_score = 0.5  # Insufficient data, neutral

    # --- Metric 5: Extinction decisions (agent kills failing strategies) ---
    extinction_count = len(graveyard)
    # Making extinction decisions = autonomous judgment
    extinction_score = min(1.0, extinction_count / max(2, 1))

    # --- Composite autonomy score ---
    weights = {
        "continuity": 0.25,
        "strategy_diversity": 0.20,
        "self_correction": 0.20,
        "fitness_trajectory": 0.20,
        "extinction_decisions": 0.15,
    }

    autonomy_score = (
        weights["continuity"] * continuity_score
        + weights["strategy_diversity"] * strategy_score
        + weights["self_correction"] * self_correction_score
        + weights["fitness_trajectory"] * trajectory_score
        + weights["extinction_decisions"] * extinction_score
    )

    # Verdict
    if autonomy_score >= 0.80:
        verdict = "FULLY AUTONOMOUS — agent operates independently"
    elif autonomy_score >= 0.60:
        verdict = "MOSTLY AUTONOMOUS — occasional human guidance beneficial"
    elif autonomy_score >= 0.40:
        verdict = "SEMI-AUTONOMOUS — regular human oversight needed"
    elif autonomy_score >= 0.20:
        verdict = "SUPERVISED — agent requires frequent direction"
    else:
        verdict = "DEPENDENT — agent cannot operate without constant direction"

    return {
        "autonomy_score": round(autonomy_score, 3),
        "components": {
            "continuity": round(continuity_score, 3),
            "strategy_diversity": round(strategy_score, 3),
            "self_correction": round(self_correction_score, 3),
            "fitness_trajectory": round(trajectory_score, 3),
            "extinction_decisions": round(extinction_score, 3),
        },
        "raw_data": {
            "total_cycles": total_cycles,
            "continuous_runs": continuous_runs,
            "unique_strategies": unique_strategies_used,
            "total_strategies_created": total_strategies_created,
            "reverts": reverts,
            "kept": kept,
            "extinctions": extinction_count,
            "final_fitness": state.get("fitness", 0),
        },
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Benchmark recording and comparison
# ---------------------------------------------------------------------------

def record_run(task_name: str, mode: str, cycles: int, final_fitness: float,
               data: dict = None):
    """Record a benchmark run result.

    Args:
        task_name: Name of the benchmark task
        mode: "evolution" or "baseline"
        cycles: Number of cycles to complete (or max if not completed)
        final_fitness: Final fitness score achieved
        data: Additional data (human_interventions, strategy_count, etc.)
    """
    tasks = _load_tasks()
    task = next((t for t in tasks if t["name"] == task_name), None)

    record = {
        "task": task_name,
        "mode": mode,
        "cycles": cycles,
        "final_fitness": final_fitness,
        "completed": False,
        "timestamp": now(),
        "data": data or {},
    }

    if task:
        criteria = task.get("success_criteria", {})
        record["completed"] = final_fitness >= criteria.get("min_fitness", 0.8)

    _append_result(record)

    result = {"status": "recorded", "task": task_name, "mode": mode}
    if record["completed"]:
        result["note"] = f"Task completed: fitness {final_fitness:.2f} meets threshold"
    else:
        min_f = task["success_criteria"]["min_fitness"] if task else 0.8
        result["note"] = f"Task incomplete: fitness {final_fitness:.2f} below {min_f:.2f}"

    return result


def compare_task(task_name: str) -> dict:
    """Compare Evolution vs baseline results for a specific task."""
    results = _load_results()
    evo_runs = [r for r in results if r["task"] == task_name and r["mode"] == "evolution"]
    base_runs = [r for r in results if r["task"] == task_name and r["mode"] == "baseline"]

    if not evo_runs and not base_runs:
        return {"error": f"No results for task '{task_name}'"}

    comparison = {"task": task_name}

    for label, runs in [("evolution", evo_runs), ("baseline", base_runs)]:
        if not runs:
            comparison[label] = {"runs": 0, "note": "No data"}
            continue

        fitnesses = [r["final_fitness"] for r in runs]
        cycles = [r["cycles"] for r in runs]
        completions = sum(1 for r in runs if r.get("completed", False))
        interventions = [r.get("data", {}).get("human_interventions", 0) for r in runs]

        comparison[label] = {
            "runs": len(runs),
            "completion_rate": round(completions / len(runs), 3),
            "completion_ci": list(wilson_score(completions, len(runs))),
            "avg_fitness": round(sum(fitnesses) / len(fitnesses), 3),
            "fitness_sd": round(sample_sd(fitnesses), 3) if len(fitnesses) > 1 else 0,
            "avg_cycles": round(sum(cycles) / len(cycles), 1),
            "avg_interventions": round(sum(interventions) / len(interventions), 1) if interventions else 0,
        }

    # Statistical comparison
    if evo_runs and base_runs:
        evo_fit = [r["final_fitness"] for r in evo_runs]
        base_fit = [r["final_fitness"] for r in base_runs]
        evo_cyc = [r["cycles"] for r in evo_runs]
        base_cyc = [r["cycles"] for r in base_runs]

        fitness_effect = effect_size(evo_fit, base_fit)
        cycle_effect = effect_size(base_cyc, evo_cyc)  # Reversed: fewer cycles = better

        def interpret_effect(d):
            d_abs = abs(d)
            if d_abs < 0.2:
                return "negligible"
            elif d_abs < 0.5:
                return "small"
            elif d_abs < 0.8:
                return "medium"
            else:
                return "large"

        comparison["statistical_comparison"] = {
            "fitness_effect_size": fitness_effect,
            "fitness_effect_interpretation": interpret_effect(fitness_effect),
            "fitness_favors": "evolution" if fitness_effect > 0 else "baseline",
            "cycle_efficiency_effect": cycle_effect,
            "cycle_effect_interpretation": interpret_effect(cycle_effect),
            "cycle_favors": "evolution" if cycle_effect > 0 else "baseline",
        }

        # Autonomy comparison
        evo_interventions = [r.get("data", {}).get("human_interventions", 0) for r in evo_runs]
        base_interventions = [r.get("data", {}).get("human_interventions", 0) for r in base_runs]
        if any(base_interventions):
            avg_evo_int = sum(evo_interventions) / len(evo_interventions)
            avg_base_int = sum(base_interventions) / len(base_interventions)
            intervention_reduction = 1 - (avg_evo_int / max(avg_base_int, 1))
            comparison["autonomy_improvement"] = {
                "intervention_reduction_pct": round(intervention_reduction * 100, 1),
                "evolution_avg_interventions": round(avg_evo_int, 1),
                "baseline_avg_interventions": round(avg_base_int, 1),
            }

    return comparison


# ---------------------------------------------------------------------------
# Evidence compilation
# ---------------------------------------------------------------------------

def compile_evidence() -> dict:
    """Compile all benchmark data into a structured evidence report.

    This is the document that answers: "Does Evolution measurably outperform
    baseline agents on standardized tasks?"
    """
    results = _load_results()
    tasks = _load_tasks()

    if not results:
        return {
            "status": "insufficient_data",
            "message": "No benchmark results recorded yet. Run benchmarks first.",
            "instructions": [
                "1. Define tasks: python3 engine/benchmark.py list",
                "2. Run Evolution: python3 engine/benchmark.py record <task> evolution <cycles> <fitness> '{}'",
                "3. Run baseline: python3 engine/benchmark.py record <task> baseline <cycles> <fitness> '{\"human_interventions\": N}'",
                "4. Compare: python3 engine/benchmark.py compare <task>",
                "5. Full report: python3 engine/benchmark.py evidence",
            ],
        }

    # Aggregate across all tasks
    evo_results = [r for r in results if r["mode"] == "evolution"]
    base_results = [r for r in results if r["mode"] == "baseline"]

    evidence = {
        "generated_at": now(),
        "total_runs": len(results),
        "evolution_runs": len(evo_results),
        "baseline_runs": len(base_results),
        "tasks_benchmarked": len(set(r["task"] for r in results)),
    }

    # Per-task comparisons
    task_names = set(r["task"] for r in results)
    evidence["per_task"] = {}
    for name in sorted(task_names):
        evidence["per_task"][name] = compare_task(name)

    # Aggregate statistics
    if evo_results:
        evo_fitnesses = [r["final_fitness"] for r in evo_results]
        evo_completions = sum(1 for r in evo_results if r.get("completed"))
        evidence["evolution_aggregate"] = {
            "avg_fitness": round(sum(evo_fitnesses) / len(evo_fitnesses), 3),
            "completion_rate": round(evo_completions / len(evo_results), 3),
            "completion_ci": list(wilson_score(evo_completions, len(evo_results))),
            "total_cycles": sum(r["cycles"] for r in evo_results),
        }

    if base_results:
        base_fitnesses = [r["final_fitness"] for r in base_results]
        base_completions = sum(1 for r in base_results if r.get("completed"))
        evidence["baseline_aggregate"] = {
            "avg_fitness": round(sum(base_fitnesses) / len(base_fitnesses), 3),
            "completion_rate": round(base_completions / len(base_results), 3),
            "completion_ci": list(wilson_score(base_completions, len(base_results))),
            "total_cycles": sum(r["cycles"] for r in base_results),
        }

    # Overall verdict
    if evo_results and base_results:
        evo_fit = [r["final_fitness"] for r in evo_results]
        base_fit = [r["final_fitness"] for r in base_results]
        d = effect_size(evo_fit, base_fit)

        evo_comp_rate = sum(1 for r in evo_results if r.get("completed")) / len(evo_results)
        base_comp_rate = sum(1 for r in base_results if r.get("completed")) / len(base_results)

        if d > 0.8 and evo_comp_rate > base_comp_rate:
            verdict = "DEFINITIVE YES — Evolution significantly outperforms baseline agents"
            confidence = "high"
        elif d > 0.5 and evo_comp_rate >= base_comp_rate:
            verdict = "YES — Evolution measurably outperforms baseline agents"
            confidence = "moderate"
        elif d > 0.2:
            verdict = "PROBABLY YES — Evolution shows improvement but more data needed"
            confidence = "low"
        elif d > -0.2:
            verdict = "INCONCLUSIVE — No significant difference detected"
            confidence = "none"
        else:
            verdict = "NO — Baseline outperforms Evolution on these tasks"
            confidence = "moderate"

        evidence["verdict"] = {
            "answer": verdict,
            "confidence": confidence,
            "effect_size": d,
            "effect_interpretation": (
                "large" if abs(d) > 0.8 else
                "medium" if abs(d) > 0.5 else
                "small" if abs(d) > 0.2 else
                "negligible"
            ),
            "sample_size": len(results),
            "recommendation": (
                f"Run {max(0, 30 - len(results))} more benchmarks for robust conclusions"
                if len(results) < 30
                else "Sample size sufficient for statistical claims"
            ),
        }
    else:
        evidence["verdict"] = {
            "answer": "INSUFFICIENT DATA — Need both Evolution and baseline runs",
            "confidence": "none",
            "recommendation": "Record baseline runs to enable comparison",
        }

    return evidence


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report() -> str:
    """Generate a human-readable benchmark report."""
    evidence = compile_evidence()

    if evidence.get("status") == "insufficient_data":
        return json.dumps(evidence, indent=2)

    lines = [
        "=" * 70,
        "EVOLUTION BENCHMARK REPORT",
        "=" * 70,
        f"Generated: {evidence['generated_at']}",
        f"Total runs: {evidence['total_runs']} "
        f"(Evolution: {evidence['evolution_runs']}, Baseline: {evidence['baseline_runs']})",
        f"Tasks benchmarked: {evidence['tasks_benchmarked']}",
        "",
    ]

    # Per-task results
    for name, comp in evidence.get("per_task", {}).items():
        lines.append(f"--- {name} ---")
        for mode in ["evolution", "baseline"]:
            data = comp.get(mode, {})
            if data.get("runs", 0) == 0:
                lines.append(f"  {mode}: no data")
                continue
            lines.append(
                f"  {mode}: {data['runs']} runs | "
                f"fitness={data['avg_fitness']:.3f} (±{data.get('fitness_sd', 0):.3f}) | "
                f"cycles={data['avg_cycles']:.0f} | "
                f"completion={data['completion_rate']:.0%}"
            )
        stat = comp.get("statistical_comparison", {})
        if stat:
            lines.append(
                f"  effect: d={stat['fitness_effect_size']:.3f} "
                f"({stat['fitness_effect_interpretation']}, "
                f"favors {stat['fitness_favors']})"
            )
        auto = comp.get("autonomy_improvement", {})
        if auto:
            lines.append(
                f"  autonomy: {auto['intervention_reduction_pct']:.0f}% fewer interventions"
            )
        lines.append("")

    # Aggregate
    for label in ["evolution_aggregate", "baseline_aggregate"]:
        agg = evidence.get(label, {})
        if agg:
            mode = label.split("_")[0]
            lines.append(
                f"{mode.upper()} AGGREGATE: "
                f"fitness={agg['avg_fitness']:.3f} | "
                f"completion={agg['completion_rate']:.0%} "
                f"CI={agg['completion_ci']}"
            )

    # Verdict
    verdict = evidence.get("verdict", {})
    if verdict:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"VERDICT: {verdict['answer']}")
        lines.append(f"Confidence: {verdict.get('confidence', 'N/A')}")
        if "effect_size" in verdict:
            lines.append(
                f"Effect size: d={verdict['effect_size']:.3f} "
                f"({verdict['effect_interpretation']})"
            )
        lines.append(f"Recommendation: {verdict.get('recommendation', '')}")
        lines.append("=" * 70)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Task management
# ---------------------------------------------------------------------------

def define_task(name: str, description: str, criteria: dict) -> dict:
    tasks = _load_tasks()
    existing = next((t for t in tasks if t["name"] == name), None)
    if existing:
        return {"error": f"Task '{name}' already exists"}

    task = {
        "name": name,
        "description": description,
        "category": criteria.pop("category", "engineering"),
        "difficulty": criteria.pop("difficulty", "medium"),
        "success_criteria": criteria,
        "max_cycles": criteria.pop("max_cycles", 50),
        "baseline_estimate": criteria.pop("baseline_estimate", {}),
    }
    tasks.append(task)
    _save_tasks(tasks)
    return {"status": "created", "task": task}


def list_tasks() -> list:
    return _load_tasks()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "define":
        if len(sys.argv) < 5:
            print("Usage: benchmark.py define <name> <description> <criteria_json>")
            sys.exit(1)
        criteria = json.loads(sys.argv[4])
        result = define_task(sys.argv[2], sys.argv[3], criteria)
        print(json.dumps(result, indent=2))

    elif cmd == "list":
        tasks = list_tasks()
        print(json.dumps(tasks, indent=2))

    elif cmd == "record":
        if len(sys.argv) < 6:
            print("Usage: benchmark.py record <task> <mode> <cycles> <fitness> [data_json]")
            sys.exit(1)
        data = json.loads(sys.argv[6]) if len(sys.argv) > 6 else {}
        result = record_run(sys.argv[2], sys.argv[3], int(sys.argv[4]),
                            float(sys.argv[5]), data)
        print(json.dumps(result, indent=2))

    elif cmd == "compare":
        if len(sys.argv) < 3:
            print("Usage: benchmark.py compare <task>")
            sys.exit(1)
        result = compare_task(sys.argv[2])
        print(json.dumps(result, indent=2))

    elif cmd == "report":
        print(generate_report())

    elif cmd == "autonomy":
        state = None
        if "--from-state" in sys.argv:
            state_file = STATE_DIR / "evolution.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
        result = compute_autonomy_metrics(state)
        print(json.dumps(result, indent=2))

    elif cmd == "evidence":
        evidence = compile_evidence()
        # Also save to file
        _ensure_dirs()
        EVIDENCE_FILE.write_text(json.dumps(evidence, indent=2))
        print(json.dumps(evidence, indent=2))
        print(f"\nEvidence saved to {EVIDENCE_FILE}", file=sys.stderr)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
