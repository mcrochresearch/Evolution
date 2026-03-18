#!/usr/bin/env python3
"""
EVOLUTION SELF-RECOVERY PROTOCOL — Structured failure escalation.

Instead of crashing or blocking on failure, every operation follows a
structured escalation path:

    1. LOG    — Record error with full context
    2. RETRY  — Exponential backoff (1s, 2s, 4s — max 3 attempts)
    3. FALLBACK — Try simpler/cheaper alternative method
    4. QUARANTINE — Isolate the failed task, continue all other work
    5. ALERT  — Notify via heartbeat alerts

One rate limit or bad API response should never freeze the entire system.

Usage:
    python engine/recover.py attempt <task_name> <command>   Execute with recovery
    python engine/recover.py quarantine <task_name> <reason> Manually quarantine
    python engine/recover.py release <task_name>             Release from quarantine
    python engine/recover.py status                          Show recovery state
    python engine/recover.py history [N]                     Show recent recovery events
"""

import json
import os
import shlex
import sys
import time
import subprocess
from pathlib import Path

try:
    from engine.stats import now
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
RECOVERY_FILE = STATE_DIR / "recovery.json"

# Recovery constants
MAX_RETRIES = 3
BACKOFF_BASE = 1  # seconds: 1, 2, 4
RETRY_TIMEOUT = 120  # seconds per attempt
MAX_QUARANTINE_AGE = 86400  # 24 hours — auto-release stale quarantines
MAX_HISTORY = 200


def default_recovery() -> dict:
    return {
        "version": 1,
        "created": now(),
        "quarantined": [],
        "history": [],
        "stats": {
            "total_attempts": 0,
            "total_retries": 0,
            "total_fallbacks": 0,
            "total_quarantines": 0,
            "total_recoveries": 0,
        },
    }


def load_recovery() -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not RECOVERY_FILE.exists():
        return default_recovery()
    with open(RECOVERY_FILE) as f:
        return json.load(f)


def save_recovery(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if len(state.get("history", [])) > MAX_HISTORY:
        state["history"] = state["history"][-MAX_HISTORY:]
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, RECOVERY_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ============================================================================
# CORE RECOVERY LOGIC
# ============================================================================

def _execute_command(command: str, timeout: int = RETRY_TIMEOUT) -> dict:
    """Execute a command and return structured result."""
    try:
        result = subprocess.run(
            shlex.split(command), capture_output=True, text=True, timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000],  # Truncate to prevent bloat
            "stderr": result.stderr[:2000],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "exit_code": -1, "stdout": "", "stderr": "TIMEOUT"}
    except Exception as e:
        return {"success": False, "exit_code": -1, "stdout": "", "stderr": str(e)}


def cmd_attempt(task_name: str, command: str, fallback: str = ""):
    """Execute command with full recovery protocol.

    Steps:
      1. Check if task is quarantined — skip if so
      2. Try command up to MAX_RETRIES with exponential backoff
      3. If all retries fail and fallback provided, try fallback
      4. If everything fails, quarantine the task
    """
    state = load_recovery()
    state["stats"]["total_attempts"] += 1

    # Check quarantine
    for q in state["quarantined"]:
        if q["task"] == task_name:
            # Check if quarantine has expired (auto-release)
            age = time.time() - q.get("epoch", 0)
            if age > MAX_QUARANTINE_AGE:
                state["quarantined"] = [x for x in state["quarantined"] if x["task"] != task_name]
                # Fall through to retry
                break
            result = {
                "task": task_name,
                "status": "quarantined",
                "reason": q.get("reason", "previously failed"),
                "quarantined_at": q.get("quarantined_at"),
                "message": "Task is quarantined. Use 'release' to retry.",
            }
            print(json.dumps(result))
            save_recovery(state)
            return

    # Retry with exponential backoff
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        result = _execute_command(command)
        if result["success"]:
            event = {
                "task": task_name,
                "status": "success",
                "attempt": attempt,
                "timestamp": now(),
            }
            if attempt > 1:
                state["stats"]["total_retries"] += attempt - 1
                state["stats"]["total_recoveries"] += 1
            state["history"].append(event)
            save_recovery(state)
            print(json.dumps({
                "task": task_name,
                "status": "success",
                "attempt": attempt,
                "output": result["stdout"],
            }))
            return

        last_error = result["stderr"]
        if attempt < MAX_RETRIES:
            backoff = BACKOFF_BASE * (2 ** (attempt - 1))
            state["stats"]["total_retries"] += 1
            time.sleep(backoff)

    # All retries failed — try fallback
    if fallback:
        state["stats"]["total_fallbacks"] += 1
        fb_result = _execute_command(fallback)
        if fb_result["success"]:
            event = {
                "task": task_name,
                "status": "fallback_success",
                "timestamp": now(),
            }
            state["stats"]["total_recoveries"] += 1
            state["history"].append(event)
            save_recovery(state)
            print(json.dumps({
                "task": task_name,
                "status": "fallback_success",
                "output": fb_result["stdout"],
            }))
            return
        last_error = fb_result["stderr"]

    # Everything failed — quarantine
    state["stats"]["total_quarantines"] += 1
    quarantine_entry = {
        "task": task_name,
        "reason": last_error or "all retries exhausted",
        "quarantined_at": now(),
        "epoch": time.time(),
        "retries": MAX_RETRIES,
        "had_fallback": bool(fallback),
    }
    # Deduplicate
    state["quarantined"] = [q for q in state["quarantined"] if q["task"] != task_name]
    state["quarantined"].append(quarantine_entry)

    event = {
        "task": task_name,
        "status": "quarantined",
        "reason": last_error,
        "timestamp": now(),
    }
    state["history"].append(event)
    save_recovery(state)

    print(json.dumps({
        "task": task_name,
        "status": "quarantined",
        "reason": last_error,
        "message": "Task quarantined after all recovery attempts failed. Other work continues.",
    }))


def cmd_quarantine(task_name: str, reason: str):
    """Manually quarantine a task."""
    state = load_recovery()
    state["quarantined"] = [q for q in state["quarantined"] if q["task"] != task_name]
    state["quarantined"].append({
        "task": task_name,
        "reason": reason,
        "quarantined_at": now(),
        "epoch": time.time(),
        "manual": True,
    })
    state["stats"]["total_quarantines"] += 1
    state["history"].append({
        "task": task_name,
        "status": "manual_quarantine",
        "reason": reason,
        "timestamp": now(),
    })
    save_recovery(state)
    print(json.dumps({"status": "quarantined", "task": task_name, "reason": reason}))


def cmd_release(task_name: str):
    """Release a task from quarantine."""
    state = load_recovery()
    before = len(state["quarantined"])
    state["quarantined"] = [q for q in state["quarantined"] if q["task"] != task_name]
    if len(state["quarantined"]) == before:
        print(json.dumps({"error": f"Task '{task_name}' not found in quarantine"}))
        sys.exit(1)
    state["history"].append({
        "task": task_name,
        "status": "released",
        "timestamp": now(),
    })
    save_recovery(state)
    print(json.dumps({"status": "released", "task": task_name}))


def cmd_status():
    """Show recovery state."""
    state = load_recovery()
    # Auto-release stale quarantines
    current = time.time()
    stale = [q for q in state["quarantined"] if current - q.get("epoch", 0) > MAX_QUARANTINE_AGE]
    if stale:
        state["quarantined"] = [q for q in state["quarantined"]
                                 if current - q.get("epoch", 0) <= MAX_QUARANTINE_AGE]
        save_recovery(state)

    print(json.dumps({
        "quarantined": state["quarantined"],
        "quarantine_count": len(state["quarantined"]),
        "stats": state["stats"],
        "auto_released": len(stale),
    }, indent=2))


def cmd_history(n: int = 20):
    """Show recent recovery events."""
    state = load_recovery()
    history = state.get("history", [])[-n:]
    print(json.dumps({"events": history, "total": len(state.get("history", []))}, indent=2))


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "attempt":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: attempt <task_name> <command> [fallback_command]"}))
                sys.exit(1)
            cmd_attempt(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
        elif cmd == "quarantine":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: quarantine <task_name> <reason>"}))
                sys.exit(1)
            cmd_quarantine(sys.argv[2], sys.argv[3])
        elif cmd == "release":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: release <task_name>"}))
                sys.exit(1)
            cmd_release(sys.argv[2])
        elif cmd == "status":
            cmd_status()
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
