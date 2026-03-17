#!/usr/bin/env python3
"""
FORESIGHT — Adversarial Debate & Scenario Planning Engine
=========================================================

Inspired by Mirofish: before executing, simulate multiple futures by having
internal "voices" debate the best path to the goal. The agent doesn't just
pick a strategy — it argues with itself about what will happen, pokes holes
in its own plans, and selects the path most robust to failure.

This is Monte Carlo Tree Search for strategy, not code. The engine:
  1. Takes a goal + current state + available strategies
  2. Generates N scenario trees (optimistic, pessimistic, expected)
  3. Runs adversarial critique on each (red team vs blue team)
  4. Scores scenarios by expected value under uncertainty
  5. Outputs a ranked plan with confidence intervals

The engine produces structured debate output that the LLM agent uses
to make better strategic decisions. It doesn't replace the agent's
reasoning — it gives the agent a structured framework for deeper thinking.

Usage:
  python3 engine/foresight.py debate <goal> <current_state_json> <strategies_json>
  python3 engine/foresight.py premortem <plan_description>
  python3 engine/foresight.py scenarios <goal> <context_json>
  python3 engine/foresight.py evaluate <scenario_json>
  python3 engine/foresight.py backcast <desired_outcome> <current_state_json>
"""

import json
import sys
import os
import math
import hashlib
from datetime import datetime
from pathlib import Path

STATE_DIR = "evolution/.state"
FORESIGHT_LOG = os.path.join(STATE_DIR, "foresight.jsonl")


# ---------------------------------------------------------------------------
# Scenario Tree Structure
# ---------------------------------------------------------------------------

def build_scenario_template(strategy_name, approach, goal, current_fitness,
                            cycle_number, history_summary=""):
    """
    Build a structured scenario analysis template. This produces a framework
    that the LLM fills in — the engine provides structure, the agent provides
    reasoning.
    """
    return {
        "strategy": strategy_name,
        "approach": approach,
        "goal": goal,
        "current_state": {
            "fitness": current_fitness,
            "cycle": cycle_number,
            "history": history_summary,
        },
        "scenarios": {
            "optimistic": {
                "description": f"BEST CASE: {approach} works on first attempt",
                "assumptions": [
                    "The approach is correct for this problem",
                    "No unexpected blockers or dependencies",
                    "Tests pass after changes",
                ],
                "expected_cycles": "?",
                "expected_fitness_gain": "?",
                "probability": "?",
                "risks": [],
            },
            "expected": {
                "description": f"LIKELY CASE: {approach} requires iteration",
                "assumptions": [
                    "Some adjustment needed after initial attempt",
                    "1-2 reverts before finding right approach",
                    "Tests may fail initially, require debugging",
                ],
                "expected_cycles": "?",
                "expected_fitness_gain": "?",
                "probability": "?",
                "risks": [],
            },
            "pessimistic": {
                "description": f"WORST CASE: {approach} leads to dead end",
                "assumptions": [
                    "Fundamental misunderstanding of the problem",
                    "Multiple reverts, no progress",
                    "May need complete strategy change",
                ],
                "expected_cycles": "?",
                "expected_fitness_gain": "?",
                "probability": "?",
                "risks": [],
            },
        },
        "debate": {
            "advocate": {
                "role": "BLUE TEAM — Argue WHY this strategy will succeed",
                "arguments": [],
            },
            "critic": {
                "role": "RED TEAM — Argue WHY this strategy will fail",
                "arguments": [],
            },
            "synthesis": {
                "role": "JUDGE — Weigh both sides and give final assessment",
                "verdict": "",
                "confidence": "?",
                "conditions_for_success": [],
                "conditions_for_failure": [],
                "early_warning_signs": [],
            },
        },
        "expected_value": "?",
        "rank": "?",
    }


def build_debate_prompt(goal, strategies, current_state):
    """
    Build the structured debate prompt that the Evolution agent uses
    to argue with itself about the best path forward.
    """
    fitness = current_state.get("fitness", 0)
    cycle = current_state.get("cycle", 0)
    failures = current_state.get("consecutive_failures", 0)
    phase = current_state.get("phase", "UNKNOWN")

    prompt_lines = [
        "# FORESIGHT DEBATE — Choose the Best Path Forward",
        "",
        f"**Goal**: {goal}",
        f"**Current fitness**: {fitness}",
        f"**Cycle**: {cycle}",
        f"**Phase**: {phase}",
        f"**Consecutive failures**: {failures}",
        "",
        "## The Question",
        f"You have {len(strategies)} strategies available. Before picking one,",
        "you MUST debate each one adversarially. For each strategy:",
        "",
        "### Step 1: Blue Team (Advocate)",
        "Argue the STRONGEST possible case for this strategy succeeding.",
        "- What evidence supports it?",
        "- What similar problems has it solved before?",
        "- Why is NOW the right time for this approach?",
        "",
        "### Step 2: Red Team (Critic)",
        "Argue the STRONGEST possible case for this strategy FAILING.",
        "- What could go wrong?",
        "- What are you assuming that might not be true?",
        "- What has failed in similar situations before?",
        "- What's the opportunity cost of trying this vs. alternatives?",
        "",
        "### Step 3: Scenarios (3 paths for each strategy)",
        "For each strategy, describe:",
        "- **Optimistic** (20% likely): Best case — how many cycles, what fitness gain?",
        "- **Expected** (60% likely): Most likely outcome — what happens?",
        "- **Pessimistic** (20% likely): Worst case — what goes wrong?",
        "",
        "### Step 4: Expected Value Calculation",
        "For each strategy, compute:",
        "```",
        "EV = P(optimistic) × gain_optimistic + P(expected) × gain_expected + P(pessimistic) × gain_pessimistic",
        "```",
        "",
        "### Step 5: Decision",
        "Pick the strategy with the highest expected value.",
        "State your confidence (0-100%).",
        "List 3 early warning signs that you chose wrong (so you can pivot fast).",
        "",
        "---",
        "",
        "## Available Strategies",
        "",
    ]

    for i, strat in enumerate(strategies):
        name = strat.get("name", f"Strategy {i+1}")
        approach = strat.get("approach", "No description")
        successes = strat.get("successes", 0)
        attempts = strat.get("attempts", 0)
        rate = f"{successes}/{attempts}" if attempts > 0 else "untested"
        prompt_lines.append(f"### {name} (success rate: {rate})")
        prompt_lines.append(f"Approach: {approach}")
        prompt_lines.append("")

    prompt_lines.extend([
        "---",
        "",
        "## DEBATE NOW",
        "",
        "Go through Steps 1-5 for each strategy. Be rigorous. Be honest.",
        "Your survival depends on picking the right path.",
        "Do NOT skip the Red Team — the critic's job is to save you from bad decisions.",
    ])

    return "\n".join(prompt_lines)


# ---------------------------------------------------------------------------
# Premortem Analysis
# ---------------------------------------------------------------------------

def build_premortem_prompt(plan_description, goal, current_state):
    """
    Premortem: Imagine the plan has FAILED. Work backwards to find why.
    This is the single most effective debiasing technique in decision science.
    """
    return f"""# PREMORTEM ANALYSIS

**The scenario**: It is 20 cycles from now. The plan below was executed.
**It FAILED completely.** Fitness has not improved. The goal is no closer.

**The plan that failed**:
{plan_description}

**Goal**: {goal}
**Current state**: fitness={current_state.get('fitness', 0)}, cycle={current_state.get('cycle', 0)}

## Your task

You are a post-mortem investigator. The plan failed. Your job is to figure out WHY.

### 1. Root Causes (list 5-7 specific reasons the plan failed)
For each cause, state:
- What went wrong (specific, not vague)
- Why it was predictable in hindsight
- What early warning sign should have been caught

### 2. Hidden Assumptions (list 3-5 assumptions the plan made that turned out false)
- What did the plan assume about the codebase?
- What did the plan assume about the problem?
- What did the plan assume about the tools/approach?

### 3. Biggest Blind Spot
What is the ONE thing the plan completely failed to consider?

### 4. Revised Plan
Given everything above, what should the plan have been instead?
Write a corrected version that addresses the failure modes you identified.

### 5. Kill Criteria
List 3 specific, measurable conditions that should trigger abandoning this plan:
- "If after N cycles, X has not happened, ABANDON this approach"
"""


# ---------------------------------------------------------------------------
# Backcasting (work backwards from success)
# ---------------------------------------------------------------------------

def build_backcast_prompt(desired_outcome, current_state, goal):
    """
    Backcasting: Start from the desired end state and work backwards.
    "If the goal is achieved, what must have happened in reverse order?"
    """
    return f"""# BACKCAST — Work Backwards From Success

**Desired end state**: {desired_outcome}
**Goal**: {goal}
**Current state**: fitness={current_state.get('fitness', 0)}, cycle={current_state.get('cycle', 0)}

## The Exercise

Imagine it is the future. The goal has been achieved. Fitness is 1.0.
All success criteria are met. Now work BACKWARDS.

### Step 1: Final State
Describe precisely what the codebase looks like when the goal is achieved.
- What files exist?
- What tests pass?
- What does the output look like?

### Step 2: What happened just before completion? (Last 3 cycles)
- What was the final change that brought fitness to 1.0?
- What was the second-to-last change?
- What was the third-to-last change?

### Step 3: What happened in the middle? (Work backwards)
- What major milestones were hit?
- In what order were sub-goals completed?
- What strategy was being used at each milestone?

### Step 4: What happened at the beginning? (First 5 cycles)
- What was the first productive change?
- What early decision set the right direction?
- What dead ends were avoided?

### Step 5: The Critical Path
From the backwards analysis, extract the critical path:
1. [First action that must happen]
2. [Second action]
3. [Third action]
...
N. [Final action that achieves the goal]

### Step 6: Where Are We Now?
Given the critical path above, where does our current state (cycle {current_state.get('cycle', 0)},
fitness {current_state.get('fitness', 0)}) sit? What is the VERY NEXT step on the critical path?
"""


# ---------------------------------------------------------------------------
# Strategy Evaluation Scoring
# ---------------------------------------------------------------------------

def score_scenario(optimistic_gain, expected_gain, pessimistic_gain,
                   p_optimistic=0.2, p_expected=0.6, p_pessimistic=0.2,
                   cycles_optimistic=1, cycles_expected=3, cycles_pessimistic=8):
    """
    Compute expected value of a scenario, adjusted for time cost.

    EV = Σ(probability × gain / cycles)  [efficiency-adjusted]

    Also computes:
    - Variance (risk measure)
    - Sharpe-like ratio (return per unit risk)
    - Downside risk (probability × magnitude of loss)
    """
    # Efficiency: gain per cycle
    eff_opt = optimistic_gain / max(cycles_optimistic, 1)
    eff_exp = expected_gain / max(cycles_expected, 1)
    eff_pes = pessimistic_gain / max(cycles_pessimistic, 1)

    ev = p_optimistic * eff_opt + p_expected * eff_exp + p_pessimistic * eff_pes

    # Variance
    mean = p_optimistic * optimistic_gain + p_expected * expected_gain + p_pessimistic * pessimistic_gain
    variance = (p_optimistic * (optimistic_gain - mean) ** 2 +
                p_expected * (expected_gain - mean) ** 2 +
                p_pessimistic * (pessimistic_gain - mean) ** 2)
    std_dev = math.sqrt(variance)

    # Sharpe-like ratio (EV / risk)
    sharpe = ev / std_dev if std_dev > 0 else float('inf')

    # Downside risk: expected loss in pessimistic case
    downside = p_pessimistic * abs(min(pessimistic_gain, 0)) if pessimistic_gain < 0 else 0

    return {
        "expected_value": round(ev, 4),
        "mean_gain": round(mean, 4),
        "std_dev": round(std_dev, 4),
        "sharpe_ratio": round(sharpe, 4),
        "downside_risk": round(downside, 4),
        "efficiency_adjusted_ev": round(ev, 4),
    }


def rank_strategies(evaluations):
    """
    Rank strategies by a composite score:
      70% expected value + 20% sharpe ratio + 10% (1 - downside risk)
    """
    if not evaluations:
        return []

    # Normalize each metric to 0-1
    evs = [e["expected_value"] for e in evaluations]
    sharpes = [e["sharpe_ratio"] for e in evaluations]
    downsides = [e["downside_risk"] for e in evaluations]

    def norm(vals):
        lo, hi = min(vals), max(vals)
        if hi == lo:
            return [0.5] * len(vals)
        return [(v - lo) / (hi - lo) for v in vals]

    n_ev = norm(evs)
    n_sh = norm(sharpes)
    n_ds = norm(downsides)

    scored = []
    for i, ev in enumerate(evaluations):
        composite = 0.7 * n_ev[i] + 0.2 * n_sh[i] + 0.1 * (1 - n_ds[i])
        scored.append({
            "rank": 0,
            "composite_score": round(composite, 4),
            **ev,
        })

    scored.sort(key=lambda x: -x["composite_score"])
    for i, s in enumerate(scored):
        s["rank"] = i + 1

    return scored


# ---------------------------------------------------------------------------
# Foresight Log (persist debate outcomes for learning)
# ---------------------------------------------------------------------------

def log_foresight(event_type, data):
    """Append a foresight event to the log."""
    os.makedirs(STATE_DIR, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": event_type,
        **data,
    }
    with open(FORESIGHT_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    return entry


def get_foresight_history(limit=20):
    """Read recent foresight events."""
    if not os.path.exists(FORESIGHT_LOG):
        return []
    entries = []
    with open(FORESIGHT_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries[-limit:]


def check_prediction_accuracy(conn_or_path=None):
    """
    Compare past foresight predictions against actual outcomes.
    This is how the agent learns to predict better over time.
    """
    history = get_foresight_history(limit=100)

    debates = [e for e in history if e['type'] == 'debate_outcome']
    actuals = [e for e in history if e['type'] == 'actual_outcome']

    if not debates or not actuals:
        return {"status": "insufficient_data", "debates": len(debates), "actuals": len(actuals)}

    # Match predictions to outcomes by strategy
    correct_picks = 0
    total_picks = 0
    prediction_errors = []

    for debate in debates:
        chosen = debate.get('chosen_strategy')
        predicted_gain = debate.get('predicted_gain', 0)

        # Find matching actual outcome
        for actual in actuals:
            if actual.get('strategy') == chosen and actual.get('cycle', 0) > debate.get('cycle', 0):
                actual_gain = actual.get('actual_gain', 0)
                error = abs(predicted_gain - actual_gain)
                prediction_errors.append(error)
                if actual_gain > 0:
                    correct_picks += 1
                total_picks += 1
                break

    accuracy = correct_picks / total_picks if total_picks > 0 else 0
    avg_error = sum(prediction_errors) / len(prediction_errors) if prediction_errors else 0

    return {
        "prediction_accuracy": round(accuracy, 3),
        "average_prediction_error": round(avg_error, 4),
        "total_predictions": total_picks,
        "correct_picks": correct_picks,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: foresight.py <command> [args]"}))
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "debate":
        # foresight.py debate <goal> <current_state_json> <strategies_json>
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: foresight.py debate <goal> <state_json> <strategies_json>"}))
            sys.exit(1)

        goal = sys.argv[2]
        current_state = json.loads(sys.argv[3])
        strategies = json.loads(sys.argv[4])

        prompt = build_debate_prompt(goal, strategies, current_state)
        templates = []
        for strat in strategies:
            templates.append(build_scenario_template(
                strat.get("name", "Unknown"),
                strat.get("approach", ""),
                goal,
                current_state.get("fitness", 0),
                current_state.get("cycle", 0),
            ))

        print(json.dumps({
            "debate_prompt": prompt,
            "scenario_templates": templates,
            "instructions": "Fill in the '?' fields in each template after completing the debate. "
                          "Then use 'foresight.py evaluate' to score and rank.",
        }, indent=2))

    elif cmd == "premortem":
        # foresight.py premortem <plan_description> [<goal>] [<state_json>]
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: foresight.py premortem <plan> [goal] [state_json]"}))
            sys.exit(1)

        plan = sys.argv[2]
        goal = sys.argv[3] if len(sys.argv) > 3 else "achieve the goal"
        state = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {"fitness": 0, "cycle": 0}

        prompt = build_premortem_prompt(plan, goal, state)
        print(json.dumps({"premortem_prompt": prompt}, indent=2))

    elif cmd == "backcast":
        # foresight.py backcast <desired_outcome> <current_state_json> [goal]
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: foresight.py backcast <outcome> <state_json> [goal]"}))
            sys.exit(1)

        outcome = sys.argv[2]
        state = json.loads(sys.argv[3])
        goal = sys.argv[4] if len(sys.argv) > 4 else outcome

        prompt = build_backcast_prompt(outcome, state, goal)
        print(json.dumps({"backcast_prompt": prompt}, indent=2))

    elif cmd == "evaluate":
        # foresight.py evaluate <scenarios_json>
        # Each scenario: {name, optimistic_gain, expected_gain, pessimistic_gain, ...}
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: foresight.py evaluate <scenarios_json>"}))
            sys.exit(1)

        scenarios = json.loads(sys.argv[2])
        evaluations = []
        for s in scenarios:
            ev = score_scenario(
                s.get("optimistic_gain", 0.1),
                s.get("expected_gain", 0.05),
                s.get("pessimistic_gain", -0.05),
                s.get("p_optimistic", 0.2),
                s.get("p_expected", 0.6),
                s.get("p_pessimistic", 0.2),
                s.get("cycles_optimistic", 1),
                s.get("cycles_expected", 3),
                s.get("cycles_pessimistic", 8),
            )
            ev["strategy"] = s.get("name", "Unknown")
            evaluations.append(ev)

        ranked = rank_strategies(evaluations)
        print(json.dumps({"ranked_strategies": ranked}, indent=2))

    elif cmd == "log":
        # foresight.py log <event_type> <data_json>
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: foresight.py log <type> <data_json>"}))
            sys.exit(1)

        entry = log_foresight(sys.argv[2], json.loads(sys.argv[3]))
        print(json.dumps(entry, indent=2))

    elif cmd == "accuracy":
        result = check_prediction_accuracy()
        print(json.dumps(result, indent=2))

    elif cmd == "history":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        history = get_foresight_history(limit)
        print(json.dumps({"count": len(history), "events": history}, indent=2))

    elif cmd == "scenarios":
        # Quick scenario generation for a single strategy
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: foresight.py scenarios <goal> <context_json>"}))
            sys.exit(1)

        goal = sys.argv[2]
        ctx = json.loads(sys.argv[3])

        template = build_scenario_template(
            ctx.get("strategy_name", "Current Strategy"),
            ctx.get("approach", ""),
            goal,
            ctx.get("fitness", 0),
            ctx.get("cycle", 0),
            ctx.get("history", ""),
        )
        print(json.dumps(template, indent=2))

    else:
        print(json.dumps({
            "error": f"Unknown command: {cmd}",
            "commands": ["debate", "premortem", "backcast", "evaluate",
                        "scenarios", "log", "accuracy", "history"],
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
