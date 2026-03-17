#!/usr/bin/env python3
"""
Independent audit log for the Evolution engine.

This module provides an append-only, hash-chained JSONL audit trail that is
separate from the agent's own reflections and logs. It gives humans a tamper-
evident record of what actually happened.

Usage:
    python engine/audit.py log <event_type> <json_data>
    python engine/audit.py verify
    python engine/audit.py tail [N]
"""

import fcntl
import hashlib
import json
import os
import sys
import time

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VALID_EVENT_TYPES = frozenset(
    ["cycle", "checkpoint", "revert", "strategy_change", "fitness"]
)

STATE_DIR = os.environ.get(
    "EVOLUTION_STATE_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "evolution", ".state"),
)
AUDIT_LOG_PATH = os.path.join(STATE_DIR, "audit.log")

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def _hash_line(line: str) -> str:
    """Return the SHA-256 hex digest of a single log line (without trailing newline)."""
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def _read_last_line(path: str) -> str | None:
    """Return the last non-empty line of *path*, or None if the file is empty / missing."""
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        last = None
        for line in f:
            stripped = line.rstrip("\n")
            if stripped:
                last = stripped
        return last


def _prev_hash(path: str) -> str:
    """Compute the hash that should go into the next log entry."""
    last = _read_last_line(path)
    if last is None:
        # Genesis entry — no previous line, use the null hash.
        return "0" * 64
    return _hash_line(last)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_log(event_type: str, json_data_str: str) -> None:
    """Append one entry to the audit log."""
    if event_type not in VALID_EVENT_TYPES:
        print(
            json.dumps(
                {
                    "error": f"Invalid event_type '{event_type}'. "
                    f"Must be one of: {', '.join(sorted(VALID_EVENT_TYPES))}"
                }
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        data = json.loads(json_data_str)
    except json.JSONDecodeError as exc:
        print(
            json.dumps({"error": f"Invalid JSON data: {exc}"}),
            file=sys.stderr,
        )
        sys.exit(1)

    os.makedirs(STATE_DIR, exist_ok=True)

    # Hold an exclusive lock to prevent concurrent processes from breaking the hash chain
    lock_path = os.path.join(STATE_DIR, ".audit.lock")
    lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "data": data,
            "prev_hash": _prev_hash(AUDIT_LOG_PATH),
        }

        line = json.dumps(entry, separators=(",", ":"))

        # Atomic append under lock: read prev_hash and write are now serialized
        fd = os.open(AUDIT_LOG_PATH, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, (line + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

    print(json.dumps({"ok": True, "event_type": event_type, "hash": _hash_line(line)}))


def cmd_verify() -> None:
    """Verify the hash chain is unbroken."""
    if not os.path.exists(AUDIT_LOG_PATH):
        print(json.dumps({"ok": True, "entries": 0, "message": "No audit log yet."}))
        return

    expected_prev = "0" * 64  # genesis
    line_num = 0
    errors: list[str] = []

    with open(AUDIT_LOG_PATH, "r") as f:
        for raw_line in f:
            raw_line = raw_line.rstrip("\n")
            if not raw_line:
                continue
            line_num += 1

            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                errors.append(f"Line {line_num}: invalid JSON")
                continue

            actual_prev = entry.get("prev_hash", "")
            if actual_prev != expected_prev:
                errors.append(
                    f"Line {line_num}: hash mismatch — "
                    f"expected {expected_prev[:16]}..., "
                    f"got {actual_prev[:16]}..."
                )

            expected_prev = _hash_line(raw_line)

    if errors:
        print(
            json.dumps({"ok": False, "entries": line_num, "errors": errors}),
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print(json.dumps({"ok": True, "entries": line_num, "message": "Hash chain intact."}))


def cmd_tail(n: int = 10) -> None:
    """Show the last *n* entries from the audit log."""
    if not os.path.exists(AUDIT_LOG_PATH):
        print(json.dumps({"entries": [], "message": "No audit log yet."}))
        return

    lines: list[str] = []
    with open(AUDIT_LOG_PATH, "r") as f:
        for raw_line in f:
            stripped = raw_line.rstrip("\n")
            if stripped:
                lines.append(stripped)

    tail_lines = lines[-n:]
    for line in tail_lines:
        # Pretty-print each entry for human readability.
        try:
            entry = json.loads(line)
            print(json.dumps(entry, indent=2))
        except json.JSONDecodeError:
            print(line)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: audit.py <log|verify|tail> [args...]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "log":
        if len(sys.argv) != 4:
            print("Usage: audit.py log <event_type> <json_data>", file=sys.stderr)
            sys.exit(1)
        cmd_log(sys.argv[2], sys.argv[3])

    elif command == "verify":
        cmd_verify()

    elif command == "tail":
        n = 10
        if len(sys.argv) >= 3:
            try:
                n = int(sys.argv[2])
            except ValueError:
                print("Usage: audit.py tail [N]", file=sys.stderr)
                sys.exit(1)
        cmd_tail(n)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
