#!/usr/bin/env python3
"""
ERROR SIGNATURES — Error Pattern Database and Matching.

Tracks error patterns across evolution cycles to enable faster diagnosis.
When an error occurs, the system checks if it matches a known signature
and immediately suggests the fix that worked last time.

This is the agent's "immune system" — once it encounters and solves an
error, it remembers the antibody and can respond faster next time.

Features:
1. EXTRACTION: Parse error output to extract a normalized signature
2. MATCHING: Compare new errors against the signature database
3. RESOLUTION: Track which fixes resolved each signature
4. LEARNING: Update confidence in resolutions based on success rate

Usage:
    python3 engine/error_signatures.py extract <error_output>
    python3 engine/error_signatures.py match <error_output>
    python3 engine/error_signatures.py resolve <signature_id> <resolution> <success:true|false>
    python3 engine/error_signatures.py list [--unresolved]
    python3 engine/error_signatures.py stats
    python3 engine/error_signatures.py prune [max_age_days]
"""

import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from engine.stats import now
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now

ENGINE_DIR = Path(__file__).parent
PROJECT_DIR = ENGINE_DIR.parent
STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
SIGNATURES_FILE = STATE_DIR / "error_signatures.json"
MAX_SIGNATURES = 200


# ---------------------------------------------------------------------------
# Error Signature Patterns
# ---------------------------------------------------------------------------

# Common error patterns with extraction regexes
ERROR_PATTERNS = [
    {
        "type": "python_exception",
        "regex": r"(\w+Error): (.+)",
        "extract": lambda m: {"error_class": m.group(1), "message": m.group(2)},
    },
    {
        "type": "python_traceback",
        "regex": r'File "([^"]+)", line (\d+)',
        "extract": lambda m: {"file": m.group(1), "line": int(m.group(2))},
    },
    {
        "type": "node_error",
        "regex": r"(TypeError|ReferenceError|SyntaxError|RangeError): (.+)",
        "extract": lambda m: {"error_class": m.group(1), "message": m.group(2)},
    },
    {
        "type": "test_failure",
        "regex": r"(FAIL|FAILED|ERROR)\s+(.+)",
        "extract": lambda m: {"status": m.group(1), "test": m.group(2)},
    },
    {
        "type": "build_error",
        "regex": r"error\[E(\d+)\]: (.+)",
        "extract": lambda m: {"code": m.group(1), "message": m.group(2)},
    },
    {
        "type": "lint_error",
        "regex": r"(\d+):(\d+)\s+(error|warning)\s+(.+)",
        "extract": lambda m: {"line": m.group(1), "col": m.group(2), "level": m.group(3), "message": m.group(4)},
    },
    {
        "type": "import_error",
        "regex": r"(ModuleNotFoundError|ImportError): (.+)",
        "extract": lambda m: {"error_class": m.group(1), "module": m.group(2)},
    },
    {
        "type": "permission_error",
        "regex": r"(PermissionError|EACCES): (.+)",
        "extract": lambda m: {"error_class": "PermissionError", "detail": m.group(2)},
    },
    {
        "type": "timeout_error",
        "regex": r"(TimeoutError|timed? ?out|deadline exceeded)",
        "extract": lambda m: {"error_class": "TimeoutError", "detail": m.group(1)},
    },
    {
        "type": "connection_error",
        "regex": r"(ConnectionError|ECONNREFUSED|ECONNRESET|ETIMEDOUT)",
        "extract": lambda m: {"error_class": "ConnectionError", "detail": m.group(1)},
    },
]


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def load_signatures() -> dict:
    """Load error signature database."""
    if SIGNATURES_FILE.exists():
        with open(SIGNATURES_FILE) as f:
            return json.load(f)
    return {
        "signatures": {},
        "total_extractions": 0,
        "total_matches": 0,
        "total_resolutions": 0,
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


def save_signatures(state: dict):
    """Save error signature database (atomic write)."""
    # Prune if over limit (keep most recently seen)
    sigs = state["signatures"]
    if len(sigs) > MAX_SIGNATURES:
        sorted_sigs = sorted(sigs.items(), key=lambda x: x[1].get("last_seen", ""), reverse=True)
        state["signatures"] = dict(sorted_sigs[:MAX_SIGNATURES])
    _atomic_write(SIGNATURES_FILE, state)


# ---------------------------------------------------------------------------
# Signature Extraction
# ---------------------------------------------------------------------------

def _normalize_error(error_output: str) -> str:
    """Normalize error output by removing variable parts (paths, line numbers, hashes)."""
    normalized = error_output

    # Remove absolute paths, keep relative
    normalized = re.sub(r'/[^\s:]+/', '<PATH>/', normalized)

    # Remove hex addresses
    normalized = re.sub(r'0x[0-9a-fA-F]+', '<ADDR>', normalized)

    # Remove specific line numbers (keep the pattern)
    normalized = re.sub(r'line \d+', 'line <N>', normalized)

    # Remove timestamps
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '<TIMESTAMP>', normalized)

    # Remove UUIDs
    normalized = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<UUID>', normalized)

    return normalized.strip()


def _compute_signature_id(error_type: str, key_fields: dict) -> str:
    """Compute a stable signature ID from error type and key fields."""
    content = f"{error_type}:{json.dumps(key_fields, sort_keys=True)}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def cmd_extract(error_output: str):
    """Extract an error signature from error output.

    Parses the error, normalizes it, and stores it in the database.
    Returns the signature for matching.
    """
    state = load_signatures()

    # Try each pattern
    matched = False
    error_type = "unknown"
    key_fields = {}

    for pattern in ERROR_PATTERNS:
        match = re.search(pattern["regex"], error_output, re.MULTILINE)
        if match:
            error_type = pattern["type"]
            key_fields = pattern["extract"](match)
            # Convert all values to strings for JSON safety
            key_fields = {k: str(v) for k, v in key_fields.items()}
            matched = True
            break

    if not matched:
        # Fallback: use first non-empty line as signature
        first_line = error_output.strip().split("\n")[0][:200]
        error_type = "generic"
        key_fields = {"first_line": _normalize_error(first_line)}

    sig_id = _compute_signature_id(error_type, key_fields)
    normalized = _normalize_error(error_output[:500])

    if sig_id in state["signatures"]:
        # Update existing signature
        sig = state["signatures"][sig_id]
        sig["occurrences"] += 1
        sig["last_seen"] = now()
    else:
        # New signature
        state["signatures"][sig_id] = {
            "id": sig_id,
            "type": error_type,
            "key_fields": key_fields,
            "normalized_preview": normalized[:300],
            "occurrences": 1,
            "first_seen": now(),
            "last_seen": now(),
            "resolutions": [],
            "resolved": False,
        }

    state["total_extractions"] += 1
    save_signatures(state)

    print(json.dumps({
        "status": "extracted",
        "signature_id": sig_id,
        "error_type": error_type,
        "key_fields": key_fields,
        "is_new": sig_id not in state["signatures"] or state["signatures"][sig_id]["occurrences"] == 1,
        "occurrences": state["signatures"][sig_id]["occurrences"],
    }))


# ---------------------------------------------------------------------------
# Signature Matching
# ---------------------------------------------------------------------------

def cmd_match(error_output: str):
    """Match an error against the signature database.

    Returns matching signatures with their known resolutions,
    sorted by relevance (exact match first, then similarity).
    """
    state = load_signatures()

    # Try exact signature match first
    for pattern in ERROR_PATTERNS:
        match = re.search(pattern["regex"], error_output, re.MULTILINE)
        if match:
            error_type = pattern["type"]
            key_fields = {k: str(v) for k, v in pattern["extract"](match).items()}
            sig_id = _compute_signature_id(error_type, key_fields)

            if sig_id in state["signatures"]:
                sig = state["signatures"][sig_id]
                state["total_matches"] += 1
                save_signatures(state)

                # Get best resolution
                best_resolution = None
                if sig["resolutions"]:
                    resolved = [r for r in sig["resolutions"] if r.get("success")]
                    if resolved:
                        best_resolution = max(resolved,
                                              key=lambda r: r.get("success_count", 0))

                print(json.dumps({
                    "status": "matched",
                    "match_type": "exact",
                    "signature_id": sig_id,
                    "error_type": sig["type"],
                    "occurrences": sig["occurrences"],
                    "resolved": sig["resolved"],
                    "best_resolution": best_resolution,
                    "all_resolutions": sig["resolutions"],
                }))
                return

    # Fuzzy match: find similar signatures
    normalized = _normalize_error(error_output[:500])
    matches = []

    for sig_id, sig in state["signatures"].items():
        # Simple similarity: compare normalized previews
        sim = _similarity(normalized, sig.get("normalized_preview", ""))
        if sim > 0.3:
            matches.append({
                "signature_id": sig_id,
                "error_type": sig["type"],
                "similarity": round(sim, 2),
                "occurrences": sig["occurrences"],
                "resolved": sig["resolved"],
                "resolutions": sig["resolutions"][:3],
            })

    matches.sort(key=lambda m: m["similarity"], reverse=True)

    state["total_matches"] += 1
    save_signatures(state)

    print(json.dumps({
        "status": "fuzzy_matched" if matches else "no_match",
        "matches": matches[:5],
        "total_checked": len(state["signatures"]),
    }))


def _similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity between two strings (word-level)."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = len(words_a & words_b)
    union = len(words_a | words_b)
    return intersection / union if union > 0 else 0.0


# ---------------------------------------------------------------------------
# Resolution Tracking
# ---------------------------------------------------------------------------

def cmd_resolve(signature_id: str, resolution: str, success: bool):
    """Record a resolution attempt for a signature.

    Tracks which fixes work and which don't, building up confidence
    over time in the best resolution for each error pattern.
    """
    state = load_signatures()

    if signature_id not in state["signatures"]:
        print(json.dumps({"error": f"Signature '{signature_id}' not found"}))
        sys.exit(1)

    sig = state["signatures"][signature_id]

    # Check if this resolution already exists
    existing = None
    for r in sig["resolutions"]:
        if r["resolution"] == resolution:
            existing = r
            break

    if existing:
        existing["attempts"] += 1
        if success:
            existing["success_count"] += 1
        existing["success_rate"] = round(
            existing["success_count"] / existing["attempts"], 2
        )
        existing["last_used"] = now()
    else:
        sig["resolutions"].append({
            "resolution": resolution,
            "attempts": 1,
            "success_count": 1 if success else 0,
            "success_rate": 1.0 if success else 0.0,
            "success": success,
            "first_used": now(),
            "last_used": now(),
        })

    # Mark signature as resolved if any resolution has >50% success rate
    sig["resolved"] = any(
        r["success_rate"] >= 0.5 and r["attempts"] >= 2
        for r in sig["resolutions"]
    )

    state["total_resolutions"] += 1
    save_signatures(state)

    print(json.dumps({
        "status": "resolution_recorded",
        "signature_id": signature_id,
        "resolution": resolution[:200],
        "success": success,
        "sig_resolved": sig["resolved"],
        "total_resolutions": len(sig["resolutions"]),
    }))


# ---------------------------------------------------------------------------
# Query Commands
# ---------------------------------------------------------------------------

def cmd_list(unresolved_only: bool = False):
    """List all error signatures."""
    state = load_signatures()

    sigs = state["signatures"]
    if unresolved_only:
        sigs = {k: v for k, v in sigs.items() if not v.get("resolved")}

    # Sort by occurrence count
    sorted_sigs = sorted(sigs.values(), key=lambda s: s["occurrences"], reverse=True)

    print(json.dumps({
        "total": len(sorted_sigs),
        "signatures": [{
            "id": s["id"],
            "type": s["type"],
            "key_fields": s["key_fields"],
            "occurrences": s["occurrences"],
            "resolved": s["resolved"],
            "resolution_count": len(s["resolutions"]),
            "last_seen": s["last_seen"],
        } for s in sorted_sigs[:20]],
    }))


def cmd_stats():
    """Show error signature statistics."""
    state = load_signatures()

    sigs = state["signatures"]
    total = len(sigs)
    resolved = sum(1 for s in sigs.values() if s.get("resolved"))
    unresolved = total - resolved

    type_counts = {}
    for s in sigs.values():
        t = s["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    # Most frequent errors
    frequent = sorted(sigs.values(), key=lambda s: s["occurrences"], reverse=True)[:5]

    print(json.dumps({
        "total_signatures": total,
        "resolved": resolved,
        "unresolved": unresolved,
        "resolution_rate": round(resolved / max(total, 1), 2),
        "total_extractions": state["total_extractions"],
        "total_matches": state["total_matches"],
        "total_resolutions": state["total_resolutions"],
        "type_distribution": type_counts,
        "most_frequent": [{
            "id": s["id"],
            "type": s["type"],
            "occurrences": s["occurrences"],
            "resolved": s["resolved"],
        } for s in frequent],
    }))


def cmd_prune(max_age_days: int = 30):
    """Prune old, unreferenced signatures."""
    state = load_signatures()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    pruned = []

    for sig_id, sig in list(state["signatures"].items()):
        if sig["last_seen"] < cutoff and sig["occurrences"] <= 1 and not sig["resolved"]:
            pruned.append(sig_id)
            del state["signatures"][sig_id]

    save_signatures(state)
    print(json.dumps({
        "status": "pruned",
        "pruned_count": len(pruned),
        "remaining": len(state["signatures"]),
    }))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "extract":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: extract <error_output>"}))
            sys.exit(1)
        cmd_extract(sys.argv[2])
    elif cmd == "match":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: match <error_output>"}))
            sys.exit(1)
        cmd_match(sys.argv[2])
    elif cmd == "resolve":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: resolve <signature_id> <resolution> <success:true|false>"}))
            sys.exit(1)
        cmd_resolve(sys.argv[2], sys.argv[3], sys.argv[4].lower() == "true")
    elif cmd == "list":
        unresolved = "--unresolved" in sys.argv
        cmd_list(unresolved)
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "prune":
        max_age = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        cmd_prune(max_age)
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
