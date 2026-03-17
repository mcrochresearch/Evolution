#!/usr/bin/env python3
"""
EVOLUTION DECISION MATRIX — Tiered autonomy for action classification.

Not every action should be auto-executed. Not every action needs human approval.
The Decision Matrix classifies actions into three tiers:

    AUTO     — Execute immediately, no confirmation needed
    REVIEW   — Queue for human review (async approval)
    HALT     — Hard stop, synchronous human approval required

Actions are classified by matching rules. Rules can be added, removed, and
the matrix can classify arbitrary actions against the current ruleset.

Usage:
    python engine/decision.py classify <action_type> [context_json]
    python engine/decision.py add-rule <action_type> <tier> [conditions_json]
    python engine/decision.py remove-rule <action_type>
    python engine/decision.py list-rules
    python engine/decision.py approve <action_id>
    python engine/decision.py deny <action_id> [reason]
    python engine/decision.py pending                    Show pending approvals
    python engine/decision.py history [N]                Recent decisions
"""

import json
import os
import sys
import hashlib
import time
from pathlib import Path

try:
    from engine.stats import now
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
DECISION_FILE = STATE_DIR / "decision.json"

# Valid tiers
TIERS = {"AUTO", "REVIEW", "HALT"}

# Default rules — sensible starting point
DEFAULT_RULES = [
    # AUTO — safe, reversible, local
    {"action": "health_check", "tier": "AUTO", "description": "System health checks"},
    {"action": "fitness_check", "tier": "AUTO", "description": "Run tests/build/lint"},
    {"action": "memory_index", "tier": "AUTO", "description": "Memory indexing and archiving"},
    {"action": "memory_consolidate", "tier": "AUTO", "description": "Memory deduplication"},
    {"action": "analyze", "tier": "AUTO", "description": "Run metacognition analysis"},
    {"action": "checkpoint", "tier": "AUTO", "description": "Create git checkpoint"},
    {"action": "guard_scan", "tier": "AUTO", "description": "Scan for anti-patterns"},
    {"action": "audit_log", "tier": "AUTO", "description": "Log to audit trail"},
    {"action": "skill_extract", "tier": "AUTO", "description": "Extract reusable skill"},
    {"action": "code_change_small", "tier": "AUTO", "description": "Small code change (<50 lines)"},
    {"action": "code_change_test", "tier": "AUTO", "description": "Add or modify tests"},
    {"action": "heartbeat_tick", "tier": "AUTO", "description": "Heartbeat self-check"},

    # REVIEW — visible to others or moderate risk
    {"action": "code_change_large", "tier": "REVIEW", "description": "Large code change (50+ lines)"},
    {"action": "dependency_add", "tier": "REVIEW", "description": "Add new dependency"},
    {"action": "dependency_remove", "tier": "REVIEW", "description": "Remove dependency"},
    {"action": "config_change", "tier": "REVIEW", "description": "Modify configuration files"},
    {"action": "git_push", "tier": "REVIEW", "description": "Push to remote repository"},
    {"action": "external_api_call", "tier": "REVIEW", "description": "Call external API"},
    {"action": "file_delete", "tier": "REVIEW", "description": "Delete files"},

    # HALT — irreversible, high-risk, affects shared systems
    {"action": "git_force_push", "tier": "HALT", "description": "Force push to remote"},
    {"action": "git_rebase", "tier": "HALT", "description": "Rebase shared branch"},
    {"action": "credential_change", "tier": "HALT", "description": "Modify credentials or API keys"},
    {"action": "infrastructure_change", "tier": "HALT", "description": "Modify infrastructure/deploy config"},
    {"action": "database_migration", "tier": "HALT", "description": "Run database migration"},
    {"action": "production_deploy", "tier": "HALT", "description": "Deploy to production"},
]

MAX_HISTORY = 200
MAX_PENDING = 50  # Don't let pending queue grow unbounded


def default_decision() -> dict:
    return {
        "version": 1,
        "created": now(),
        "rules": DEFAULT_RULES,
        "pending": [],
        "history": [],
    }


def load_decision() -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not DECISION_FILE.exists():
        state = default_decision()
        save_decision(state)
        return state
    with open(DECISION_FILE) as f:
        return json.load(f)


def save_decision(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if len(state.get("history", [])) > MAX_HISTORY:
        state["history"] = state["history"][-MAX_HISTORY:]
    if len(state.get("pending", [])) > MAX_PENDING:
        # Drop oldest pending items
        state["pending"] = state["pending"][-MAX_PENDING:]
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, DECISION_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _action_id(action: str, context: dict) -> str:
    """Generate a short deterministic ID for an action + context."""
    raw = json.dumps({"action": action, "context": context, "time": time.time()}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


# ============================================================================
# COMMANDS
# ============================================================================

def cmd_classify(action_type: str, context: str = "{}"):
    """Classify an action against the decision matrix.

    Returns the tier and whether the action can proceed.
    If REVIEW/HALT, creates a pending approval entry.
    """
    try:
        ctx = json.loads(context)
    except json.JSONDecodeError:
        ctx = {}

    state = load_decision()

    # Find matching rule
    matched_rule = None
    for rule in state["rules"]:
        if rule["action"] == action_type:
            # Check conditions if present
            conditions = rule.get("conditions", {})
            conditions_met = True
            for key, value in conditions.items():
                if key.endswith("_gt"):
                    field = key[:-3]
                    if ctx.get(field, 0) <= value:
                        conditions_met = False
                elif key.endswith("_lt"):
                    field = key[:-3]
                    if ctx.get(field, 0) >= value:
                        conditions_met = False
                elif ctx.get(key) != value:
                    conditions_met = False
            if conditions_met:
                matched_rule = rule
                break

    if not matched_rule:
        # Unknown action — default to REVIEW (safe default)
        tier = "REVIEW"
        description = f"Unknown action type: {action_type}"
    else:
        tier = matched_rule["tier"]
        description = matched_rule.get("description", "")

    result = {
        "action": action_type,
        "tier": tier,
        "description": description,
        "proceed": tier == "AUTO",
        "context": ctx,
    }

    if tier in ("REVIEW", "HALT"):
        action_id = _action_id(action_type, ctx)
        pending = {
            "id": action_id,
            "action": action_type,
            "tier": tier,
            "description": description,
            "context": ctx,
            "created": now(),
            "status": "pending",
        }
        state["pending"].append(pending)
        result["action_id"] = action_id
        result["message"] = f"{'HALT' if tier == 'HALT' else 'REVIEW'}: awaiting approval"

    state["history"].append({
        "action": action_type,
        "tier": tier,
        "timestamp": now(),
        "auto_proceeded": tier == "AUTO",
    })

    save_decision(state)
    print(json.dumps(result, indent=2))


def cmd_add_rule(action_type: str, tier: str, conditions: str = "{}"):
    """Add or update a rule in the decision matrix."""
    tier = tier.upper()
    if tier not in TIERS:
        print(json.dumps({"error": f"Invalid tier '{tier}'. Must be one of: {', '.join(sorted(TIERS))}"}))
        sys.exit(1)
    try:
        conds = json.loads(conditions)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON conditions: {e}"}))
        sys.exit(1)

    state = load_decision()
    # Remove existing rule for this action
    state["rules"] = [r for r in state["rules"] if r["action"] != action_type]
    rule = {
        "action": action_type,
        "tier": tier,
        "description": f"Custom rule for {action_type}",
    }
    if conds:
        rule["conditions"] = conds
    state["rules"].append(rule)
    save_decision(state)
    print(json.dumps({"status": "rule_added", "rule": rule}))


def cmd_remove_rule(action_type: str):
    """Remove a rule from the decision matrix."""
    state = load_decision()
    before = len(state["rules"])
    state["rules"] = [r for r in state["rules"] if r["action"] != action_type]
    if len(state["rules"]) == before:
        print(json.dumps({"error": f"No rule found for action '{action_type}'"}))
        sys.exit(1)
    save_decision(state)
    print(json.dumps({"status": "rule_removed", "action": action_type}))


def cmd_list_rules():
    """List all rules grouped by tier."""
    state = load_decision()
    by_tier = {"AUTO": [], "REVIEW": [], "HALT": []}
    for rule in state["rules"]:
        tier = rule.get("tier", "REVIEW")
        by_tier.setdefault(tier, []).append(rule)
    print(json.dumps(by_tier, indent=2))


def cmd_approve(action_id: str):
    """Approve a pending action."""
    state = load_decision()
    for p in state["pending"]:
        if p["id"] == action_id:
            p["status"] = "approved"
            p["resolved_at"] = now()
            state["history"].append({
                "action": p["action"],
                "tier": p["tier"],
                "status": "approved",
                "timestamp": now(),
            })
            state["pending"] = [x for x in state["pending"] if x["id"] != action_id]
            save_decision(state)
            print(json.dumps({"status": "approved", "action_id": action_id, "action": p["action"]}))
            return
    print(json.dumps({"error": f"Pending action '{action_id}' not found"}))
    sys.exit(1)


def cmd_deny(action_id: str, reason: str = ""):
    """Deny a pending action."""
    state = load_decision()
    for p in state["pending"]:
        if p["id"] == action_id:
            p["status"] = "denied"
            p["resolved_at"] = now()
            p["deny_reason"] = reason
            state["history"].append({
                "action": p["action"],
                "tier": p["tier"],
                "status": "denied",
                "reason": reason,
                "timestamp": now(),
            })
            state["pending"] = [x for x in state["pending"] if x["id"] != action_id]
            save_decision(state)
            print(json.dumps({"status": "denied", "action_id": action_id, "reason": reason}))
            return
    print(json.dumps({"error": f"Pending action '{action_id}' not found"}))
    sys.exit(1)


def cmd_pending():
    """Show pending approvals."""
    state = load_decision()
    pending = state.get("pending", [])
    print(json.dumps({
        "pending": pending,
        "count": len(pending),
        "review": len([p for p in pending if p["tier"] == "REVIEW"]),
        "halt": len([p for p in pending if p["tier"] == "HALT"]),
    }, indent=2))


def cmd_history(n: int = 20):
    """Show recent decision history."""
    state = load_decision()
    history = state.get("history", [])[-n:]
    print(json.dumps({"decisions": history, "total": len(state.get("history", []))}, indent=2))


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "classify":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: classify <action_type> [context_json]"}))
                sys.exit(1)
            cmd_classify(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "{}")
        elif cmd == "add-rule":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: add-rule <action_type> <tier> [conditions_json]"}))
                sys.exit(1)
            cmd_add_rule(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "{}")
        elif cmd == "remove-rule":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: remove-rule <action_type>"}))
                sys.exit(1)
            cmd_remove_rule(sys.argv[2])
        elif cmd == "list-rules":
            cmd_list_rules()
        elif cmd == "approve":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: approve <action_id>"}))
                sys.exit(1)
            cmd_approve(sys.argv[2])
        elif cmd == "deny":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: deny <action_id> [reason]"}))
                sys.exit(1)
            cmd_deny(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
        elif cmd == "pending":
            cmd_pending()
        elif cmd == "history":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            cmd_history(n)
        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
