#!/usr/bin/env python3
"""
EVOLUTION SKILLFORGE — Autonomous skill extraction and creation engine.

Inspired by:
- Voyager (NVIDIA, 2023) — agents that build a skill library
- Claudeception — autonomous skill extraction from Claude Code sessions
- Pattern Graduation — memory -> recurs 2-3x -> permanent skill

When Evolution discovers a reusable solution, SkillForge packages it as a
proper Claude Code / OpenClaw skill that auto-loads in future sessions.

Features:
- Atomic file writes (write-to-temp-then-rename)
- Skill deduplication (name-based)
- Skill versioning (tracks revisions)
- Auto-promotion criteria (3+ uses, >60% success rate)
- Wilson score confidence intervals for promotion decisions

Usage:
    python engine/skillforge.py extract <name> <description> <steps_json> [trigger]
    python engine/skillforge.py use <skill_id> <true|false>
    python engine/skillforge.py promote <skill_id>
    python engine/skillforge.py list
    python engine/skillforge.py stats
"""

import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import math

SKILLS_DIR = Path("evolution/skills")
REGISTRY = Path("evolution/.state/skill-registry.json")

# Promotion criteria
MIN_USES_FOR_PROMOTION = 3
MIN_SUCCESS_RATE_FOR_PROMOTION = 0.60


def now():
    return datetime.now(timezone.utc).isoformat()


def load_registry():
    if REGISTRY.exists():
        with open(REGISTRY) as f:
            return json.load(f)
    return {"skills": [], "promoted": [], "version": 2, "next_skill_id": 1}


def save_registry(registry):
    """Atomically save registry (write-to-temp-then-rename)."""
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=REGISTRY.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(registry, f, indent=2)
        os.replace(tmp_path, REGISTRY)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def wilson_lower(successes: int, total: int, z: float = 1.96) -> float:
    """Wilson score lower bound — conservative estimate of true success rate."""
    if total == 0:
        return 0.0
    phat = successes / total
    denominator = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denominator
    spread = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total) / denominator
    return max(0, round(center - spread, 4))


def find_skill_by_id(registry, skill_id):
    """Find a skill by ID in the registry."""
    for s in registry["skills"]:
        if s["id"] == skill_id:
            return s
    return None


def find_skill_by_name(registry, name):
    """Find a skill by name (for deduplication)."""
    normalized = _sanitize_name(name)
    for s in registry["skills"]:
        if _sanitize_name(s["name"]) == normalized:
            return s
    return None


def cmd_extract(name: str, description: str, steps: list, trigger: str = ""):
    """Extract a discovered solution into a reusable skill."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    registry = load_registry()

    # Check for duplicate by name
    existing = find_skill_by_name(registry, name)
    if existing:
        # Update existing skill (versioning)
        existing["version"] = existing.get("version", 1) + 1
        existing["description"] = description
        existing["updated_at"] = now()
        # Rewrite the skill file
        _write_skill_file(name, description, steps, trigger, existing["id"], existing["version"])
        save_registry(registry)
        print(json.dumps({
            "status": "updated",
            "skill": existing,
            "message": f"Updated existing skill to version {existing['version']}"
        }))
        return

    # Monotonic skill ID (survives deletions, prevents collisions)
    sid_num = registry.get("next_skill_id", len(registry["skills"]) + 1)
    skill_id = f"SK{sid_num:03d}"
    registry["next_skill_id"] = sid_num + 1

    # Create the skill file
    _write_skill_file(name, description, steps, trigger, skill_id, 1)

    # Register
    skill_entry = {
        "id": skill_id,
        "name": name,
        "description": description,
        "file": str(SKILLS_DIR / f"{_sanitize_name(name)}.md"),
        "created": now(),
        "times_used": 0,
        "successes": 0,
        "version": 1,
        "promoted": False,
    }
    registry["skills"].append(skill_entry)
    save_registry(registry)

    print(json.dumps({"status": "extracted", "skill": skill_entry}))


def _sanitize_name(name: str) -> str:
    """Sanitize skill name to prevent path traversal. Uses allowlist, not denylist."""
    safe = name.lower().replace(' ', '-')
    # Allowlist: only alphanumeric, hyphens, and underscores survive
    safe = re.sub(r'[^a-z0-9_-]', '', safe)
    if not safe:
        safe = "unnamed-skill"
    return safe


def _write_skill_file(name, description, steps, trigger, skill_id, version):
    """Write the skill markdown file atomically."""
    skill_content = f"""---
name: evolution-{_sanitize_name(name)}
description: "{description}"
---

# {name}

> Auto-extracted by Evolution SkillForge on {now()[:10]}
> Version {version}

## When to Use
{trigger if trigger else f"When you encounter a problem matching: {description}"}

## Procedure
"""
    for i, step in enumerate(steps, 1):
        skill_content += f"\n{i}. {step}"

    skill_content += f"""

## Metadata
- **Skill ID**: {skill_id}
- **Version**: {version}
- **Extracted**: {now()}
"""

    skill_path = SKILLS_DIR / f"{_sanitize_name(name)}.md"
    # Atomic write
    fd, tmp_path = tempfile.mkstemp(dir=SKILLS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(skill_content)
        os.replace(tmp_path, skill_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def cmd_use(skill_id: str, success: bool):
    """Record a skill usage and outcome."""
    registry = load_registry()
    skill = find_skill_by_id(registry, skill_id)
    if not skill:
        print(json.dumps({"error": f"Skill {skill_id} not found"}))
        sys.exit(1)

    skill["times_used"] += 1
    if success:
        skill["successes"] += 1
    save_registry(registry)

    success_rate = skill["successes"] / max(skill["times_used"], 1)
    wilson = wilson_lower(skill["successes"], skill["times_used"])

    print(json.dumps({
        "status": "recorded",
        "skill": skill_id,
        "success_rate": round(success_rate, 3),
        "wilson_lower_bound": wilson,
        "promotion_eligible": (
            skill["times_used"] >= MIN_USES_FOR_PROMOTION
            and wilson >= MIN_SUCCESS_RATE_FOR_PROMOTION
            and not skill["promoted"]
        ),
    }))


def cmd_promote(skill_id: str):
    """Promote a skill to the project's .claude/skills/ directory for auto-loading."""
    registry = load_registry()
    skill = find_skill_by_id(registry, skill_id)
    if not skill:
        print(json.dumps({"error": f"Skill {skill_id} not found"}))
        return

    src = Path(skill["file"])
    if not src.exists():
        print(json.dumps({"error": f"Skill file not found: {src}"}))
        return

    # Check promotion criteria
    wilson = wilson_lower(skill["successes"], skill["times_used"])
    if skill["times_used"] < MIN_USES_FOR_PROMOTION:
        print(json.dumps({
            "warning": f"Skill only used {skill['times_used']} times (min {MIN_USES_FOR_PROMOTION}). Promoting anyway.",
        }))

    # Copy to .claude/skills/ atomically
    dest_dir = Path(".claude/skills")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    content = src.read_text()
    fd, tmp_path = tempfile.mkstemp(dir=dest_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp_path, dest)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    skill["promoted"] = True
    skill["promoted_at"] = now()
    if skill_id not in registry["promoted"]:
        registry["promoted"].append(skill_id)
    save_registry(registry)

    print(json.dumps({
        "status": "promoted",
        "skill": skill_id,
        "from": str(src),
        "to": str(dest),
        "wilson_lower_bound": wilson,
    }))


def cmd_list():
    """List all extracted skills."""
    registry = load_registry()
    skills = []
    for s in registry["skills"]:
        rate = s["successes"] / max(s["times_used"], 1)
        wilson = wilson_lower(s["successes"], s["times_used"])
        skills.append({
            "id": s["id"],
            "name": s["name"],
            "version": s.get("version", 1),
            "used": s["times_used"],
            "success_rate": round(rate, 2),
            "wilson_lower": wilson,
            "promoted": s["promoted"],
            "promotion_eligible": (
                s["times_used"] >= MIN_USES_FOR_PROMOTION
                and wilson >= MIN_SUCCESS_RATE_FOR_PROMOTION
                and not s["promoted"]
            ),
        })
    print(json.dumps({"skills": skills, "total": len(skills)}, indent=2))


def cmd_stats():
    """Show skill library statistics."""
    registry = load_registry()
    total = len(registry["skills"])
    promoted = sum(1 for s in registry["skills"] if s["promoted"])
    total_uses = sum(s["times_used"] for s in registry["skills"])
    total_successes = sum(s["successes"] for s in registry["skills"])

    # Auto-promotion candidates using Wilson score (statistically rigorous)
    candidates = [
        s for s in registry["skills"]
        if not s["promoted"]
        and s["times_used"] >= MIN_USES_FOR_PROMOTION
        and wilson_lower(s["successes"], s["times_used"]) >= MIN_SUCCESS_RATE_FOR_PROMOTION
    ]

    print(json.dumps({
        "total_skills": total,
        "promoted": promoted,
        "total_uses": total_uses,
        "overall_success_rate": round(total_successes / max(total_uses, 1), 2),
        "promotion_candidates": [{"id": s["id"], "name": s["name"],
                                   "wilson_lower": wilson_lower(s["successes"], s["times_used"])}
                                  for s in candidates],
    }, indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    try:
        if cmd == "extract":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: extract <name> <description> [steps_json] [trigger]"}))
                sys.exit(1)
            steps = json.loads(sys.argv[4]) if len(sys.argv) > 4 else []
            trigger = sys.argv[5] if len(sys.argv) > 5 else ""
            cmd_extract(sys.argv[2], sys.argv[3], steps, trigger)
        elif cmd == "use":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: use <skill_id> [true|false]"}))
                sys.exit(1)
            cmd_use(sys.argv[2], sys.argv[3].lower() == "true" if len(sys.argv) > 3 else True)
        elif cmd == "promote":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: promote <skill_id>"}))
                sys.exit(1)
            cmd_promote(sys.argv[2])
        elif cmd == "list":
            cmd_list()
        elif cmd == "stats":
            cmd_stats()
        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
