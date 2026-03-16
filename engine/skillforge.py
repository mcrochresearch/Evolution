#!/usr/bin/env python3
"""
EVOLUTION SKILLFORGE — Autonomous skill extraction and creation engine.

Inspired by:
- Voyager (NVIDIA, 2023) — agents that build a skill library
- Claudeception — autonomous skill extraction from Claude Code sessions
- Pattern Graduation — memory → recurs 2-3x → permanent skill

When Evolution discovers a reusable solution, SkillForge packages it as a
proper Claude Code / OpenClaw skill that auto-loads in future sessions.

Usage:
    python engine/skillforge.py extract <name> <description> <steps_json>
    python engine/skillforge.py list
    python engine/skillforge.py promote <skill_id>
    python engine/skillforge.py stats
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILLS_DIR = Path("evolution/skills")
REGISTRY = Path("evolution/.state/skill-registry.json")


def now():
    return datetime.now(timezone.utc).isoformat()


def load_registry():
    if REGISTRY.exists():
        with open(REGISTRY) as f:
            return json.load(f)
    return {"skills": [], "promoted": []}


def save_registry(registry):
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY, "w") as f:
        json.dump(registry, f, indent=2)


def cmd_extract(name: str, description: str, steps: list, trigger: str = ""):
    """Extract a discovered solution into a reusable skill."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    registry = load_registry()
    skill_id = f"SK{len(registry['skills']) + 1:03d}"

    # Create the skill file
    skill_content = f"""---
name: evolution-{name.lower().replace(' ', '-')}
description: "{description}"
---

# {name}

> Auto-extracted by Evolution SkillForge on {now()[:10]}
> This skill was discovered during autonomous evolution and packaged for reuse.

## When to Use
{trigger if trigger else f"When you encounter a problem matching: {description}"}

## Procedure
"""
    for i, step in enumerate(steps, 1):
        skill_content += f"\n{i}. {step}"

    skill_content += f"""

## Metadata
- **Extracted**: {now()}
- **Skill ID**: {skill_id}
- **Times Used**: 0
- **Success Rate**: N/A
"""

    skill_path = SKILLS_DIR / f"{name.lower().replace(' ', '-')}.md"
    with open(skill_path, "w") as f:
        f.write(skill_content)

    # Register
    skill_entry = {
        "id": skill_id,
        "name": name,
        "description": description,
        "file": str(skill_path),
        "created": now(),
        "times_used": 0,
        "successes": 0,
        "promoted": False,
    }
    registry["skills"].append(skill_entry)
    save_registry(registry)

    print(json.dumps({"status": "extracted", "skill": skill_entry}))


def cmd_use(skill_id: str, success: bool):
    """Record a skill usage and outcome."""
    registry = load_registry()
    for skill in registry["skills"]:
        if skill["id"] == skill_id:
            skill["times_used"] += 1
            if success:
                skill["successes"] += 1
            save_registry(registry)
            print(json.dumps({
                "status": "recorded",
                "skill": skill_id,
                "success_rate": skill["successes"] / max(skill["times_used"], 1)
            }))
            return
    print(json.dumps({"error": f"Skill {skill_id} not found"}))


def cmd_promote(skill_id: str):
    """Promote a skill to the project's .claude/skills/ directory for auto-loading."""
    registry = load_registry()
    for skill in registry["skills"]:
        if skill["id"] == skill_id:
            src = Path(skill["file"])
            if not src.exists():
                print(json.dumps({"error": f"Skill file not found: {src}"}))
                return

            # Copy to .claude/skills/
            dest_dir = Path(".claude/skills")
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            dest.write_text(src.read_text())

            skill["promoted"] = True
            skill["promoted_at"] = now()
            registry["promoted"].append(skill_id)
            save_registry(registry)

            print(json.dumps({
                "status": "promoted",
                "skill": skill_id,
                "from": str(src),
                "to": str(dest),
            }))
            return
    print(json.dumps({"error": f"Skill {skill_id} not found"}))


def cmd_list():
    """List all extracted skills."""
    registry = load_registry()
    skills = []
    for s in registry["skills"]:
        rate = s["successes"] / max(s["times_used"], 1)
        skills.append({
            "id": s["id"],
            "name": s["name"],
            "used": s["times_used"],
            "success_rate": round(rate, 2),
            "promoted": s["promoted"],
        })
    print(json.dumps({"skills": skills, "total": len(skills)}, indent=2))


def cmd_stats():
    """Show skill library statistics."""
    registry = load_registry()
    total = len(registry["skills"])
    promoted = sum(1 for s in registry["skills"] if s["promoted"])
    total_uses = sum(s["times_used"] for s in registry["skills"])
    total_successes = sum(s["successes"] for s in registry["skills"])

    # Auto-promotion candidates: used 3+ times with >60% success
    candidates = [
        s for s in registry["skills"]
        if not s["promoted"]
        and s["times_used"] >= 3
        and s["successes"] / max(s["times_used"], 1) > 0.6
    ]

    print(json.dumps({
        "total_skills": total,
        "promoted": promoted,
        "total_uses": total_uses,
        "overall_success_rate": round(total_successes / max(total_uses, 1), 2),
        "promotion_candidates": [{"id": s["id"], "name": s["name"]} for s in candidates],
    }, indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "extract":
        steps = json.loads(sys.argv[4]) if len(sys.argv) > 4 else []
        trigger = sys.argv[5] if len(sys.argv) > 5 else ""
        cmd_extract(sys.argv[2], sys.argv[3], steps, trigger)
    elif cmd == "use":
        cmd_use(sys.argv[2], sys.argv[3].lower() == "true" if len(sys.argv) > 3 else True)
    elif cmd == "promote":
        cmd_promote(sys.argv[2])
    elif cmd == "list":
        cmd_list()
    elif cmd == "stats":
        cmd_stats()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


