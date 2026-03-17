#!/usr/bin/env python3
"""
EVOLUTION HEARTBEAT — Persistent periodic self-check loop.

The heartbeat is the spine of autonomy. Without it, you have a reactive agent.
With it, you have an autonomous operator that never silently dies.

Every tick, the heartbeat:
  1. Checks system health (state file, disk, engine integrity)
  2. Processes the task queue (deferred/scheduled work)
  3. Fires scheduled tasks based on cadence (hourly, daily, weekly)
  4. Logs cycle completion for liveness monitoring

The heartbeat is NOT the evolution cycle — it's the background pulse that
ensures the system stays alive, healthy, and on-schedule between cycles.

Usage:
    python engine/heartbeat.py tick                  Run one heartbeat tick
    python engine/heartbeat.py schedule <task> <cadence> [data_json]
    python engine/heartbeat.py queue <task> [data_json]
    python engine/heartbeat.py status                Show heartbeat state
    python engine/heartbeat.py due                   List tasks due now
    python engine/heartbeat.py history [N]           Show last N ticks
"""

import json
import os
import sys
import time
from pathlib import Path

try:
    from engine.stats import now
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
HEARTBEAT_FILE = STATE_DIR / "heartbeat.json"
HEARTBEAT_LOG = STATE_DIR / "heartbeat.log"

# Cadence definitions in seconds
CADENCES = {
    "every_tick": 0,           # Every heartbeat tick
    "hourly": 3600,
    "every_4h": 14400,
    "daily": 86400,
    "weekly": 604800,
}

MAX_HISTORY = 200  # Rolling window for tick history


def default_heartbeat() -> dict:
    """Create fresh heartbeat state."""
    return {
        "version": 1,
        "created": now(),
        "last_tick": None,
        "tick_count": 0,
        "consecutive_healthy": 0,
        "consecutive_unhealthy": 0,
        "scheduled_tasks": [],
        "task_queue": [],
        "tick_history": [],
    }


def load_heartbeat() -> dict:
    """Load heartbeat state, creating if needed."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not HEARTBEAT_FILE.exists():
        return default_heartbeat()
    with open(HEARTBEAT_FILE) as f:
        return json.load(f)


def save_heartbeat(state: dict):
    """Atomically save heartbeat state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Trim history
    if len(state.get("tick_history", [])) > MAX_HISTORY:
        state["tick_history"] = state["tick_history"][-MAX_HISTORY:]
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, HEARTBEAT_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ============================================================================
# HEALTH CHECKS
# ============================================================================

def check_health() -> dict:
    """Run system health checks. Returns {healthy: bool, checks: {...}}."""
    checks = {}

    # 1. State file exists and is valid JSON
    state_file = STATE_DIR / "evolution.json"
    try:
        if state_file.exists():
            with open(state_file) as f:
                json.load(f)
            checks["state_file"] = {"ok": True}
        else:
            checks["state_file"] = {"ok": True, "note": "no active evolution"}
    except (json.JSONDecodeError, IOError) as e:
        checks["state_file"] = {"ok": False, "error": str(e)}

    # 2. Disk space (warn if <100MB free)
    try:
        stat = os.statvfs(str(STATE_DIR))
        free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        checks["disk"] = {"ok": free_mb > 100, "free_mb": round(free_mb)}
    except OSError:
        checks["disk"] = {"ok": True, "note": "statvfs unavailable"}

    # 3. Audit log integrity (quick check — just verify file exists)
    audit_log = STATE_DIR / "audit.log"
    checks["audit_log"] = {"ok": True, "exists": audit_log.exists()}

    # 4. Memory database accessible
    cortex_db = STATE_DIR / "cortex.db"
    checks["cortex_db"] = {"ok": True, "exists": cortex_db.exists()}

    # 5. Lock file not stale (older than 5 minutes = likely stale)
    # Only report stale if the lock is actually held by another process
    lock_file = STATE_DIR / ".lock"
    if lock_file.exists():
        import fcntl
        try:
            test_fd = open(lock_file, "w")
            try:
                fcntl.flock(test_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Lock acquired — no one else holds it, so it's not stale
                fcntl.flock(test_fd, fcntl.LOCK_UN)
                checks["lock"] = {"ok": True}
            except (OSError, IOError):
                # Lock is held by another process — check age
                age = time.time() - lock_file.stat().st_mtime
                checks["lock"] = {"ok": age < 300, "age_seconds": round(age)}
            finally:
                test_fd.close()
        except OSError:
            checks["lock"] = {"ok": True}
    else:
        checks["lock"] = {"ok": True}

    healthy = all(c["ok"] for c in checks.values())
    return {"healthy": healthy, "checks": checks}


# ============================================================================
# TASK SCHEDULING
# ============================================================================

def _is_due(task: dict, current_time: float) -> bool:
    """Check if a scheduled task is due to run."""
    cadence = task.get("cadence", "daily")
    interval = CADENCES.get(cadence, 86400)
    if interval == 0:
        return True  # every_tick
    last_run = task.get("last_run_epoch", 0)
    return (current_time - last_run) >= interval


def get_due_tasks(state: dict) -> list:
    """Return list of scheduled tasks that are due now."""
    current = time.time()
    due = []
    for task in state.get("scheduled_tasks", []):
        if _is_due(task, current):
            due.append(task)
    # Also include all queued (one-shot) tasks
    due.extend(state.get("task_queue", []))
    return due


# ============================================================================
# COMMANDS
# ============================================================================

def cmd_tick():
    """Run one heartbeat tick: health check + process due tasks."""
    state = load_heartbeat()
    current = time.time()

    # Health check
    health = check_health()

    if health["healthy"]:
        state["consecutive_healthy"] += 1
        state["consecutive_unhealthy"] = 0
    else:
        state["consecutive_unhealthy"] += 1
        state["consecutive_healthy"] = 0

    # Find due tasks
    due = get_due_tasks(state)
    due_names = [t["name"] for t in due]

    # Build set of only scheduled task names that are due (exclude queued one-shots)
    due_scheduled_names = {t["name"] for t in state.get("scheduled_tasks", []) if _is_due(t, current)}

    # Mark only scheduled tasks that are actually due (not queued one-shots with same name)
    for task in state.get("scheduled_tasks", []):
        if task["name"] in due_scheduled_names:
            task["last_run_epoch"] = current
            task["run_count"] = task.get("run_count", 0) + 1

    # Clear the one-shot queue
    queued_count = len(state.get("task_queue", []))
    state["task_queue"] = []

    # Log tick
    state["tick_count"] += 1
    state["last_tick"] = now()
    tick_record = {
        "tick": state["tick_count"],
        "timestamp": state["last_tick"],
        "healthy": health["healthy"],
        "due_tasks": due_names,
        "queued_processed": queued_count,
    }
    state["tick_history"].append(tick_record)

    save_heartbeat(state)

    # Output: the agent reads this and executes the due tasks
    result = {
        "tick": state["tick_count"],
        "healthy": health["healthy"],
        "health_details": health["checks"],
        "consecutive_healthy": state["consecutive_healthy"],
        "consecutive_unhealthy": state["consecutive_unhealthy"],
        "due_tasks": due,
        "timestamp": state["last_tick"],
    }

    # Alert conditions
    alerts = []
    if state["consecutive_unhealthy"] >= 3:
        alerts.append("CRITICAL: 3+ consecutive unhealthy ticks")
    if not health["checks"].get("disk", {}).get("ok", True):
        alerts.append("LOW_DISK: less than 100MB free")
    if not health["checks"].get("lock", {}).get("ok", True):
        alerts.append("STALE_LOCK: lock file older than 5 minutes")

    if alerts:
        result["alerts"] = alerts

    print(json.dumps(result, indent=2))


def cmd_schedule(name: str, cadence: str, data: str = "{}"):
    """Add a recurring scheduled task."""
    if cadence not in CADENCES:
        print(json.dumps({"error": f"Invalid cadence '{cadence}'. Must be one of: {', '.join(CADENCES.keys())}"}))
        sys.exit(1)
    try:
        task_data = json.loads(data)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON data: {e}"}))
        sys.exit(1)

    state = load_heartbeat()

    # Deduplicate by name
    state["scheduled_tasks"] = [t for t in state["scheduled_tasks"] if t["name"] != name]

    task = {
        "name": name,
        "cadence": cadence,
        "data": task_data,
        "created": now(),
        "last_run_epoch": 0,
        "run_count": 0,
    }
    state["scheduled_tasks"].append(task)
    save_heartbeat(state)
    print(json.dumps({"status": "scheduled", "task": task}))


def cmd_queue(name: str, data: str = "{}"):
    """Add a one-shot task to the queue (runs on next tick)."""
    try:
        task_data = json.loads(data)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON data: {e}"}))
        sys.exit(1)

    state = load_heartbeat()
    task = {
        "name": name,
        "data": task_data,
        "queued_at": now(),
    }
    state["task_queue"].append(task)
    save_heartbeat(state)
    print(json.dumps({"status": "queued", "task": task, "queue_depth": len(state["task_queue"])}))


def cmd_status():
    """Show heartbeat state."""
    state = load_heartbeat()
    health = check_health()
    due = get_due_tasks(state)
    print(json.dumps({
        "tick_count": state["tick_count"],
        "last_tick": state["last_tick"],
        "healthy": health["healthy"],
        "consecutive_healthy": state["consecutive_healthy"],
        "consecutive_unhealthy": state["consecutive_unhealthy"],
        "scheduled_tasks": len(state["scheduled_tasks"]),
        "queued_tasks": len(state["task_queue"]),
        "due_now": len(due),
        "health_checks": health["checks"],
    }, indent=2))


def cmd_due():
    """List tasks that are due now."""
    state = load_heartbeat()
    due = get_due_tasks(state)
    print(json.dumps({"due_tasks": due, "count": len(due)}, indent=2))


def cmd_history(n: int = 20):
    """Show last N heartbeat ticks."""
    state = load_heartbeat()
    history = state.get("tick_history", [])[-n:]
    print(json.dumps({"ticks": history, "total": state["tick_count"]}, indent=2))


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "tick":
            cmd_tick()
        elif cmd == "schedule":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: schedule <name> <cadence> [data_json]"}))
                sys.exit(1)
            cmd_schedule(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "{}")
        elif cmd == "queue":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: queue <name> [data_json]"}))
                sys.exit(1)
            cmd_queue(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "{}")
        elif cmd == "status":
            cmd_status()
        elif cmd == "due":
            cmd_due()
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
