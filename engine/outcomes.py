#!/usr/bin/env python3
"""
EVOLUTION OUTCOME RECORDS — Machine-readable structured action outcomes.

Every agent action gets logged with a structured outcome record that enables
querying, retrospectives, and learning. This goes beyond cycle logs — it
captures individual action-level outcomes with full context for analysis.

The outcome store is a JSONL file (one JSON object per line) for efficient
appending and streaming reads. Queries filter and aggregate over outcomes.

Usage:
    python engine/outcomes.py log <action_type> <description> <outcome> [data_json]
    python engine/outcomes.py query [--type X] [--outcome X] [--since YYYY-MM-DD] [--limit N]
    python engine/outcomes.py stats [--since YYYY-MM-DD]
    python engine/outcomes.py retro [--days N]           Weekly retrospective
    python engine/outcomes.py lessons                     Extract actionable lessons
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from engine.stats import now, wilson_lower
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now, wilson_lower

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
OUTCOMES_FILE = STATE_DIR / "outcomes.jsonl"
LESSONS_FILE = STATE_DIR / "lessons.json"

# Valid outcome types
VALID_OUTCOMES = {"success", "failure", "partial", "skipped", "quarantined"}

# Valid action types (extensible)
VALID_ACTION_TYPES = {
    "code_change", "test_add", "test_fix", "bug_fix", "refactor",
    "dependency_change", "config_change", "deploy", "rollback",
    "api_call", "web_search", "file_create", "file_delete",
    "strategy_select", "strategy_mutate", "strategy_extinct",
    "memory_store", "memory_recall", "skill_extract",
    "checkpoint", "revert", "analysis", "debug", "research",
    "custom",  # Catch-all for actions not in the predefined list
}


def _append_outcome(record: dict):
    """Append a single outcome record to the JSONL file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, separators=(",", ":"))
    fd = os.open(str(OUTCOMES_FILE), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_outcomes(since: str = "", action_type: str = "", outcome: str = "",
                   limit: int = 0) -> list:
    """Read and filter outcomes from the JSONL file."""
    if not OUTCOMES_FILE.exists():
        return []

    results = []
    with open(OUTCOMES_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Apply filters
            if since and record.get("timestamp", "") < since:
                continue
            if action_type and record.get("action_type") != action_type:
                continue
            if outcome and record.get("outcome") != outcome:
                continue

            results.append(record)

    if limit > 0:
        results = results[-limit:]
    return results


# ============================================================================
# COMMANDS
# ============================================================================

def cmd_log(action_type: str, description: str, outcome: str, data: str = "{}"):
    """Log a structured outcome record."""
    if action_type not in VALID_ACTION_TYPES:
        # Allow custom types but warn
        pass  # Soft validation — don't block logging

    if outcome not in VALID_OUTCOMES:
        print(json.dumps({"error": f"Invalid outcome '{outcome}'. Must be one of: {', '.join(sorted(VALID_OUTCOMES))}"}))
        sys.exit(1)

    try:
        extra_data = json.loads(data)
    except json.JSONDecodeError:
        extra_data = {}

    core_fields = {"action_type", "description", "outcome", "timestamp", "epoch"}
    record = {
        "action_type": action_type,
        "description": description,
        "outcome": outcome,
        "timestamp": now(),
        "epoch": time.time(),
    }
    # Merge extra data (strategy, fitness, PnL, etc.) without overwriting core fields
    for k, v in extra_data.items():
        if k not in core_fields:
            record[k] = v

    _append_outcome(record)
    print(json.dumps({"status": "logged", "record": record}))


def cmd_query(action_type: str = "", outcome: str = "", since: str = "", limit: int = 50):
    """Query outcome records with filters."""
    results = _read_outcomes(since=since, action_type=action_type, outcome=outcome, limit=limit)
    print(json.dumps({"outcomes": results, "count": len(results)}, indent=2))


def cmd_stats(since: str = ""):
    """Compute aggregate statistics over outcomes."""
    outcomes = _read_outcomes(since=since)
    if not outcomes:
        print(json.dumps({"message": "No outcomes recorded yet", "total": 0}))
        return

    # By action type
    by_type = {}
    for o in outcomes:
        atype = o.get("action_type", "unknown")
        if atype not in by_type:
            by_type[atype] = {"total": 0, "success": 0, "failure": 0, "partial": 0}
        by_type[atype]["total"] += 1
        result = o.get("outcome", "unknown")
        if result in by_type[atype]:
            by_type[atype][result] += 1

    # Compute success rates with Wilson confidence
    for atype, data in by_type.items():
        if data["total"] > 0:
            data["success_rate"] = round(data["success"] / data["total"], 3)
            data["wilson_lower"] = wilson_lower(data["success"], data["total"])
        else:
            data["success_rate"] = 0
            data["wilson_lower"] = 0

    # By outcome
    by_outcome = {}
    for o in outcomes:
        result = o.get("outcome", "unknown")
        by_outcome[result] = by_outcome.get(result, 0) + 1

    # Overall
    total = len(outcomes)
    successes = sum(1 for o in outcomes if o.get("outcome") == "success")

    print(json.dumps({
        "total": total,
        "overall_success_rate": round(successes / total, 3) if total else 0,
        "overall_wilson_lower": wilson_lower(successes, total),
        "by_outcome": by_outcome,
        "by_action_type": by_type,
        "date_range": {
            "earliest": outcomes[0].get("timestamp", ""),
            "latest": outcomes[-1].get("timestamp", ""),
        } if outcomes else {},
    }, indent=2))


def cmd_retro(days: int = 7):
    """Generate a retrospective over the last N days.

    Analyzes:
    - What action types succeeded most/least?
    - What patterns led to failures?
    - What recurring errors appeared?
    - Concrete recommendations for improvement.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    outcomes = _read_outcomes(since=cutoff)

    if not outcomes:
        print(json.dumps({"message": f"No outcomes in the last {days} days", "total": 0}))
        return

    # Successes and failures by type
    type_outcomes = {}
    for o in outcomes:
        atype = o.get("action_type", "unknown")
        if atype not in type_outcomes:
            type_outcomes[atype] = {"success": 0, "failure": 0, "total": 0}
        type_outcomes[atype]["total"] += 1
        if o.get("outcome") == "success":
            type_outcomes[atype]["success"] += 1
        elif o.get("outcome") == "failure":
            type_outcomes[atype]["failure"] += 1

    # Find best and worst performers
    ranked = []
    for atype, data in type_outcomes.items():
        if data["total"] >= 2:
            data["success_rate"] = round(data["success"] / data["total"], 3)
            data["wilson_lower"] = wilson_lower(data["success"], data["total"])
            ranked.append({"action_type": atype, **data})

    ranked.sort(key=lambda x: x["wilson_lower"], reverse=True)

    # Extract error patterns from failure descriptions
    failure_descriptions = [o.get("description", "") for o in outcomes if o.get("outcome") == "failure"]
    error_words = {}
    for desc in failure_descriptions:
        for word in desc.lower().split():
            if len(word) > 3:
                error_words[word] = error_words.get(word, 0) + 1
    top_error_words = sorted(error_words.items(), key=lambda x: -x[1])[:10]

    # Recommendations
    recommendations = []
    for item in ranked:
        if item["wilson_lower"] < 0.3 and item["total"] >= 3:
            recommendations.append(
                f"Action '{item['action_type']}' has low success rate "
                f"({item['success_rate']*100:.0f}%, Wilson={item['wilson_lower']:.2f}) — "
                f"investigate root cause or change approach"
            )
    for item in ranked[:3]:
        if item["wilson_lower"] > 0.6:
            recommendations.append(
                f"Action '{item['action_type']}' is performing well "
                f"({item['success_rate']*100:.0f}%, Wilson={item['wilson_lower']:.2f}) — "
                f"double down on this approach"
            )

    total = len(outcomes)
    successes = sum(1 for o in outcomes if o.get("outcome") == "success")

    retro = {
        "period_days": days,
        "total_actions": total,
        "overall_success_rate": round(successes / total, 3) if total else 0,
        "best_performers": ranked[:5],
        "worst_performers": ranked[-3:] if len(ranked) > 3 else [],
        "failure_keywords": top_error_words,
        "recommendations": recommendations,
        "timestamp": now(),
    }
    print(json.dumps(retro, indent=2))


def cmd_lessons():
    """Extract actionable lessons from outcome history.

    Reads all outcomes, identifies statistically significant patterns,
    and writes them to lessons.json for loading alongside skills/prompts.
    """
    outcomes = _read_outcomes()
    if len(outcomes) < 10:
        print(json.dumps({"message": "Not enough outcomes for lessons", "total": len(outcomes)}))
        return

    lessons = []
    type_outcomes = {}

    for o in outcomes:
        atype = o.get("action_type", "unknown")
        if atype not in type_outcomes:
            type_outcomes[atype] = {"success": 0, "failure": 0, "total": 0, "descriptions": []}
        type_outcomes[atype]["total"] += 1
        if o.get("outcome") == "success":
            type_outcomes[atype]["success"] += 1
        elif o.get("outcome") == "failure":
            type_outcomes[atype]["failure"] += 1
        type_outcomes[atype]["descriptions"].append(o.get("description", ""))

    base_rate = sum(1 for o in outcomes if o.get("outcome") == "success") / len(outcomes)

    for atype, data in type_outcomes.items():
        if data["total"] < 5:
            continue
        rate = data["success"] / data["total"]
        wl = wilson_lower(data["success"], data["total"])

        if wl > base_rate + 0.15:
            lessons.append({
                "type": "positive",
                "action_type": atype,
                "lesson": f"'{atype}' actions have high success rate ({rate*100:.0f}% over {data['total']}, Wilson={wl:.2f}). Continue this approach.",
                "confidence": wl,
                "sample_size": data["total"],
                "extracted_at": now(),
            })
        elif wl < 0.3 and rate < 0.4:
            lessons.append({
                "type": "negative",
                "action_type": atype,
                "lesson": f"'{atype}' actions have low success rate ({rate*100:.0f}% over {data['total']}, Wilson={wl:.2f}). Change approach or add safeguards.",
                "confidence": 1 - wl,  # Confidence in the negative
                "sample_size": data["total"],
                "extracted_at": now(),
            })

    # Save lessons
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LESSONS_FILE, "w") as f:
        json.dump({"lessons": lessons, "total_outcomes": len(outcomes), "generated_at": now()}, f, indent=2)

    print(json.dumps({
        "status": "lessons_extracted",
        "count": len(lessons),
        "positive": len([l for l in lessons if l["type"] == "positive"]),
        "negative": len([l for l in lessons if l["type"] == "negative"]),
        "lessons": lessons,
    }, indent=2))


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "log":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: log <action_type> <description> <outcome> [data_json]"}))
                sys.exit(1)
            cmd_log(sys.argv[2], sys.argv[3], sys.argv[4],
                    sys.argv[5] if len(sys.argv) > 5 else "{}")
        elif cmd == "query":
            # Parse optional flags
            kwargs = {}
            args = sys.argv[2:]
            i = 0
            while i < len(args):
                if args[i] == "--type" and i + 1 < len(args):
                    kwargs["action_type"] = args[i + 1]
                    i += 2
                elif args[i] == "--outcome" and i + 1 < len(args):
                    kwargs["outcome"] = args[i + 1]
                    i += 2
                elif args[i] == "--since" and i + 1 < len(args):
                    kwargs["since"] = args[i + 1]
                    i += 2
                elif args[i] == "--limit" and i + 1 < len(args):
                    kwargs["limit"] = int(args[i + 1])
                    i += 2
                else:
                    i += 1
            cmd_query(**kwargs)
        elif cmd == "stats":
            since = ""
            if len(sys.argv) > 2 and sys.argv[2] == "--since" and len(sys.argv) > 3:
                since = sys.argv[3]
            cmd_stats(since)
        elif cmd == "retro":
            days = 7
            if len(sys.argv) > 2 and sys.argv[2] == "--days" and len(sys.argv) > 3:
                days = int(sys.argv[3])
            cmd_retro(days)
        elif cmd == "lessons":
            cmd_lessons()
        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
