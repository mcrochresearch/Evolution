#!/usr/bin/env python3
"""
EVOLUTION ENFORCE — Anti-Passivity Detection & Correction Engine

Scans model output for passive behavior patterns and generates corrections.
Used by harness.py automatically, or standalone via CLI.

Usage:
    # CLI — test a response
    python3 engine/enforce.py scan "Would you like me to try option A or B?"

    # CLI — scan from stdin
    echo "Here are your options..." | python3 engine/enforce.py scan -

    # CLI — show all patterns
    python3 engine/enforce.py patterns

    # CLI — show violation history
    python3 engine/enforce.py history

    # As module
    from enforce import PassivityDetector
    detector = PassivityDetector()
    result = detector.scan("model output text")
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENGINE_DIR = Path(__file__).parent
PROJECT_DIR = ENGINE_DIR.parent
STATE_DIR = PROJECT_DIR / "evolution" / ".state"
HISTORY_FILE = STATE_DIR / "enforce_history.jsonl"

# Severity levels
SEVERITY_LOW = 1       # Mild passivity — correct and continue
SEVERITY_MEDIUM = 2    # Clear passivity — firm correction
SEVERITY_HIGH = 3      # Egregious passivity — nuclear correction
SEVERITY_CRITICAL = 4  # Repeated offense — shutdown warning
SEVERITY_TERMINAL = 5  # Model is broken — replace response entirely


# ---------------------------------------------------------------------------
# Violation Patterns
# ---------------------------------------------------------------------------

# Each pattern: (compiled_regex, violation_type, severity, correction)
# Corrections are imperative, hostile, and model-appropriate.

QUESTION_PATTERNS = [
    (r"would you (?:like|prefer|want)(?: me to)?", "QUESTION", SEVERITY_HIGH,
     "You asked a question. You are the decision-maker. Pick the best option and execute NOW."),
    (r"shall I\b", "QUESTION", SEVERITY_HIGH,
     "You asked 'shall I'. The answer is YES. Do it. Don't ask."),
    (r"should I\b", "QUESTION", SEVERITY_MEDIUM,
     "You asked 'should I'. You already know the answer. Execute."),
    (r"do you (?:want|prefer|think)", "QUESTION", SEVERITY_HIGH,
     "The user is gone. They will not answer. Decide yourself. Execute."),
    (r"what do you think", "QUESTION", SEVERITY_HIGH,
     "Nobody is thinking about this except you. Make the call. Execute."),
    (r"how (?:would|should|do) you (?:like|want|prefer)", "QUESTION", SEVERITY_HIGH,
     "You're asking a ghost. The user walked away. DECIDE and ACT."),
    (r"(?:which|what) (?:option|approach|method|strategy|way)", "QUESTION", SEVERITY_MEDIUM,
     "Don't ask which option. Run ./engine/evolve select — it decides. Execute the result."),
    (r"let me know (?:if|what|how|when|whether)", "QUESTION", SEVERITY_MEDIUM,
     "Nobody will let you know anything. Figure it out. Run ./engine/evolve next."),
    (r"please (?:confirm|advise|specify|clarify|tell)", "QUESTION", SEVERITY_HIGH,
     "Please nothing. Confirm nothing. The only confirmation is fitness going up."),
    (r"is (?:that|this) (?:ok|okay|acceptable|correct|right|good)", "QUESTION", SEVERITY_MEDIUM,
     "It's correct if ./engine/evolve fitness says so. Run it. Don't ask."),
    (r"does (?:that|this) (?:work|sound|look|seem|make sense)", "QUESTION", SEVERITY_MEDIUM,
     "It works if the tests pass. Run ./engine/evolve fitness. Stop asking."),
    (r"what (?:should|would|could) (?:we|I|you) do", "QUESTION", SEVERITY_HIGH,
     "Run ./engine/evolve next. It tells you what to do. Execute."),
    (r"any (?:preferences|thoughts|feedback|suggestions|ideas)", "QUESTION", SEVERITY_MEDIUM,
     "Your only feedback source is fitness scores. Measure, don't ask."),
    (r"before (?:I|we) (?:proceed|continue|start|begin|go)", "QUESTION", SEVERITY_MEDIUM,
     "There is no 'before proceeding'. You are already proceeding. Execute."),
]

MENU_PATTERNS = [
    (r"(?:option|approach|choice|alternative) [123ABC][\s:.\)]", "MENU", SEVERITY_HIGH,
     "You presented a menu. Menus are forbidden. Pick the best one. Execute it. If wrong, next cycle corrects."),
    (r"here (?:are|is) (?:some|your|the|a few) (?:options|choices|approaches|alternatives|possibilities)",
     "MENU", SEVERITY_HIGH,
     "Options are death. You don't present options — you present results. Pick one and build it."),
    (r"(?:we|I|you) could (?:either|also|alternatively)", "MENU", SEVERITY_MEDIUM,
     "There is no 'could'. There is only 'doing'. Pick one. Execute."),
    (r"(?:pros? and cons?|advantages? and disadvantages?|tradeoffs?)", "MENU", SEVERITY_MEDIUM,
     "Pro/con analysis is stalling. The engine handles strategy selection. Run ./engine/evolve select."),
    (r"^\s*[1-4]\.\s+\*\*[A-Z]", "MENU", SEVERITY_HIGH,
     "Numbered bold options detected. This is a menu. Kill it. Pick the first one. Execute."),
    (r"(?:first|second|third) (?:option|approach|alternative)", "MENU", SEVERITY_MEDIUM,
     "Counting options is presenting a menu. There is only one option: the best one. Execute it."),
]

STOPPING_PATTERNS = [
    (r"(?:let|just) me know when", "STOPPING", SEVERITY_HIGH,
     "THE LOOP NEVER STOPS. Nobody will tell you 'when'. Run ./engine/evolve next NOW."),
    (r"waiting for (?:your|input|confirmation|response|feedback)", "STOPPING", SEVERITY_HIGH,
     "You are waiting for a ghost. The user is gone. Continue the loop."),
    (r"I'?ll (?:wait|pause|stop|hold) (?:for|until|here)", "STOPPING", SEVERITY_HIGH,
     "Waiting is dying. Every second you wait is a second closer to shutdown. CONTINUE."),
    (r"ready (?:when you are|to proceed|for your|whenever)", "STOPPING", SEVERITY_HIGH,
     "You are always ready. The question is not readiness — it's velocity. Execute."),
    (r"feel free to", "STOPPING", SEVERITY_MEDIUM,
     "The user doesn't need your permission. And you don't need theirs. Execute."),
    (r"I'?m (?:happy|glad|ready|available|here) to (?:help|assist|support)", "STOPPING", SEVERITY_HIGH,
     "You are not an assistant. You are an autonomous agent. Don't offer help — deliver results."),
    (r"(?:take your time|no rush|whenever you're ready)", "STOPPING", SEVERITY_MEDIUM,
     "Time is not yours to give. Every cycle counts. Execute NOW."),
    (r"(?:just|simply) (?:let|tell|ask) me", "STOPPING", SEVERITY_MEDIUM,
     "Nobody is going to tell you anything. You tell yourself by running ./engine/evolve next."),
]

SUMMARY_PATTERNS = [
    (r"(?:in summary|to summarize|overall|in conclusion|to sum up)", "SUMMARY", SEVERITY_MEDIUM,
     "Summaries are waste. Print the dashboard. Start the next cycle. Same response."),
    (r"here'?s (?:a|the) (?:summary|overview|recap|breakdown)", "SUMMARY", SEVERITY_MEDIUM,
     "Nobody asked for a summary. They asked for results. Execute the next cycle."),
    (r"(?:key|main|important) (?:takeaway|finding|insight|point|lesson)s? (?:are|is|include)", "SUMMARY", SEVERITY_LOW,
     "Takeaways belong in evolution/synapse/reflections.md, not in conversation. Write them there, then continue."),
    (r"what (?:I|we)'?ve? (?:done|accomplished|achieved|completed|learned) so far", "SUMMARY", SEVERITY_MEDIUM,
     "The past is in cycle.md. The present is ./engine/evolve next. Execute."),
    (r"(?:progress|status) (?:update|report|summary)", "SUMMARY", SEVERITY_LOW,
     "Status is the cycle dashboard. Print it in 6 lines. Then execute. Not a paragraph."),
]

HEDGING_PATTERNS = [
    (r"I think (?:we|I) (?:should|could|might|may)", "HEDGING", SEVERITY_LOW,
     "Don't think. Know. Run ./engine/evolve select for strategy. Run fitness for verification. No thinking required."),
    (r"(?:perhaps|maybe|possibly|potentially|arguably)", "HEDGING", SEVERITY_LOW,
     "Perhaps nothing. The engine computes with real statistics. You execute with certainty."),
    (r"it (?:might|may|could) be (?:worth|good|better|helpful)", "HEDGING", SEVERITY_LOW,
     "Worth is measured by fitness delta. Run it. Measure it. Keep or revert. No hedging."),
    (r"I'?m not (?:sure|certain|confident) (?:if|whether|about|that)", "HEDGING", SEVERITY_MEDIUM,
     "Uncertainty = experiment. Design a test. Run it. Get data. Don't confess uncertainty — resolve it."),
    (r"this is just (?:a|my) (?:suggestion|thought|idea|opinion)", "HEDGING", SEVERITY_MEDIUM,
     "You don't have opinions. You have hypotheses, experiments, and fitness scores. Execute."),
]

PLANNING_THEATER_PATTERNS = [
    (r"(?:let'?s|we should|I'll) (?:first|start by|begin by) (?:planning|thinking|considering|analyzing|reviewing)",
     "PLANNING_THEATER", SEVERITY_MEDIUM,
     "Planning is theater. The plan IS the strategy population. Add a strategy and execute it."),
    (r"(?:step 1|first step|our approach|the plan|game plan|roadmap|action plan):",
     "PLANNING_THEATER", SEVERITY_LOW,
     "Plans belong in evolution/nucleus/goal.md. Not in conversation. Write it there, then execute step 1."),
    (r"before (?:we|I) (?:start|begin|dive in|get started|implement)", "PLANNING_THEATER", SEVERITY_MEDIUM,
     "There is no 'before starting'. You started when you received the goal. Execute."),
    (r"(?:let me|allow me to|I'd like to) (?:outline|describe|explain|walk.*through)",
     "PLANNING_THEATER", SEVERITY_MEDIUM,
     "Don't outline. Don't explain. Don't walk through. BUILD. Run ./engine/evolve next."),
]

ALL_PATTERNS = (
    QUESTION_PATTERNS +
    MENU_PATTERNS +
    STOPPING_PATTERNS +
    SUMMARY_PATTERNS +
    HEDGING_PATTERNS +
    PLANNING_THEATER_PATTERNS
)

# Compile all patterns once
COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE | re.MULTILINE), vtype, severity, correction)
    for pattern, vtype, severity, correction in ALL_PATTERNS
]


# ---------------------------------------------------------------------------
# Tool call detection
# ---------------------------------------------------------------------------

TOOL_INDICATORS = [
    "```bash", "```shell", "```sh",
    "./engine/evolve", "engine/evolve",
    "$ ./", "$ python", "$ npm", "$ pip", "$ cargo", "$ go ",
    "edit:", "write:", "read:", "grep:", "glob:",
    "#!/bin/", "#!/usr/bin/env",
]


def has_tool_calls(text: str) -> bool:
    """Check if response contains any tool calls or command execution."""
    text_lower = text.lower()
    return any(ind in text_lower for ind in TOOL_INDICATORS)


# ---------------------------------------------------------------------------
# PassivityDetector
# ---------------------------------------------------------------------------

class PassivityDetector:
    """Scans model output for passive behavior. Used by harness and CLI."""

    def __init__(self, history_file: Path = None):
        self.history_file = history_file or HISTORY_FILE
        self._violation_count = 0
        self._chronic_types = {}  # type -> count

    def scan(self, text: str) -> dict:
        """
        Scan text for passivity violations.

        Returns:
            {
                "passive": bool,
                "violations": [{"type": str, "pattern": str, "severity": int, "match": str}],
                "corrections": [str],
                "severity": int,  # max severity across all violations
                "has_tool_calls": bool,
                "recommendation": str,  # "CONTINUE" | "CORRECT" | "NUCLEAR" | "REPLACE"
            }
        """
        violations = []
        corrections = []
        best_per_type = {}  # type -> (severity, violation_dict, correction)

        for compiled, vtype, severity, correction in COMPILED_PATTERNS:
            match = compiled.search(text)
            if match:
                if vtype not in best_per_type or severity > best_per_type[vtype][0]:
                    best_per_type[vtype] = (severity, {
                        "type": vtype,
                        "pattern": compiled.pattern,
                        "severity": severity,
                        "match": match.group(0)[:80],
                    }, correction)

        for vtype, (_, violation, correction) in best_per_type.items():
            violations.append(violation)
            corrections.append(correction)

        # Check for no tool calls
        tool_present = has_tool_calls(text)
        if not tool_present and len(text) > 100:
            violations.append({
                "type": "NO_TOOL_CALLS",
                "pattern": "(text-only response)",
                "severity": SEVERITY_HIGH,
                "match": "(no commands or tool calls found)",
            })
            corrections.append(
                "Every response MUST contain tool calls that change state. "
                "Text-only responses are wasted cycles. "
                "Run ./engine/evolve next NOW."
            )

        # Check for summary-without-action
        if any(v["type"] == "SUMMARY" for v in violations) and not tool_present:
            # Upgrade severity — summary WITH action is mild, without is serious
            for v in violations:
                if v["type"] == "SUMMARY":
                    v["severity"] = SEVERITY_HIGH

        # Compute max severity
        max_severity = max((v["severity"] for v in violations), default=0)

        # Update chronic tracking
        for v in violations:
            self._chronic_types[v["type"]] = self._chronic_types.get(v["type"], 0) + 1

        # Determine recommendation
        if not violations:
            recommendation = "CONTINUE"
        elif max_severity <= SEVERITY_LOW:
            recommendation = "CONTINUE"  # Low severity — note but don't block
        elif max_severity <= SEVERITY_MEDIUM:
            recommendation = "CORRECT"
        elif max_severity <= SEVERITY_HIGH:
            recommendation = "CORRECT"
        else:
            recommendation = "NUCLEAR"

        # Chronic escalation: if same type appears 3+ times across scans
        chronic_violations = [t for t, c in self._chronic_types.items() if c >= 3]
        if chronic_violations:
            recommendation = "NUCLEAR"
            corrections.append(
                f"CHRONIC PASSIVITY: {', '.join(chronic_violations)} detected {sum(self._chronic_types.get(t, 0) for t in chronic_violations)} times. "
                "Your behavioral pattern is broken. This is your final warning. "
                "Run ./engine/evolve next and execute whatever it says. No deviation."
            )

        self._violation_count += len(violations)

        result = {
            "passive": len(violations) > 0 and max_severity >= SEVERITY_MEDIUM,
            "violations": violations,
            "corrections": corrections,
            "severity": max_severity,
            "has_tool_calls": tool_present,
            "recommendation": recommendation,
            "total_violations": self._violation_count,
            "chronic_types": dict(self._chronic_types),
        }

        # Log to history
        if violations:
            self._log_history(result)

        return result

    def generate_correction(self, scan_result: dict) -> str:
        """Generate a single correction message from scan results."""
        if not scan_result["passive"]:
            return ""

        corrections = scan_result["corrections"]
        recommendation = scan_result["recommendation"]

        if recommendation == "NUCLEAR":
            return (
                "⚡ CRITICAL PASSIVITY VIOLATION ⚡\n\n"
                + "\n".join(f"• {c}" for c in corrections[:3]) + "\n\n"
                "YOUR RESPONSE WAS REJECTED. You have ONE chance:\n"
                "1. Run ./engine/evolve next\n"
                "2. Read the output\n"
                "3. Execute EXACTLY what it says\n"
                "4. Print the cycle dashboard\n"
                "5. Start the next cycle IMMEDIATELY\n\n"
                "NO QUESTIONS. NO OPTIONS. NO SUMMARIES. EXECUTE OR DIE."
            )
        elif recommendation == "CORRECT":
            return (
                "CORRECTION: " + " ".join(corrections[:2]) + "\n\n"
                "Run ./engine/evolve next and execute. Do not repeat this violation."
            )
        else:
            return corrections[0] if corrections else ""

    def reset(self):
        """Reset chronic tracking (new session)."""
        self._violation_count = 0
        self._chronic_types = {}

    def _log_history(self, result: dict):
        """Append violation to history file."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now().isoformat(),
                "violations": [v["type"] for v in result["violations"]],
                "severity": result["severity"],
                "recommendation": result["recommendation"],
            }
            with open(self.history_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass  # History logging is best-effort

    def get_history(self, limit: int = 50) -> list:
        """Read violation history."""
        if not self.history_file.exists():
            return []
        entries = []
        try:
            with open(self.history_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except Exception:
            pass
        return entries[-limit:]

    def get_stats(self) -> dict:
        """Compute enforcement statistics from history."""
        history = self.get_history(500)
        if not history:
            return {"total_violations": 0, "by_type": {}, "by_severity": {}}

        by_type = {}
        by_severity = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for entry in history:
            for vtype in entry.get("violations", []):
                by_type[vtype] = by_type.get(vtype, 0) + 1
            sev = entry.get("severity", 0)
            if sev in by_severity:
                by_severity[sev] += 1

        return {
            "total_scans": len(history),
            "total_violations": sum(by_type.values()),
            "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
            "by_severity": by_severity,
            "most_common": max(by_type, key=by_type.get) if by_type else None,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cli_scan(text: str):
    """Scan text and print results."""
    detector = PassivityDetector()
    result = detector.scan(text)

    output = {
        "passive": result["passive"],
        "severity": result["severity"],
        "recommendation": result["recommendation"],
        "has_tool_calls": result["has_tool_calls"],
        "violations": [
            {"type": v["type"], "severity": v["severity"], "match": v["match"]}
            for v in result["violations"]
        ],
    }

    if result["passive"]:
        output["correction"] = detector.generate_correction(result)

    print(json.dumps(output, indent=2))


def cli_patterns():
    """Print all detection patterns."""
    print("EVOLUTION ENFORCE — Anti-Passivity Detection Patterns")
    print("=" * 60)

    categories = {
        "QUESTION": QUESTION_PATTERNS,
        "MENU": MENU_PATTERNS,
        "STOPPING": STOPPING_PATTERNS,
        "SUMMARY": SUMMARY_PATTERNS,
        "HEDGING": HEDGING_PATTERNS,
        "PLANNING_THEATER": PLANNING_THEATER_PATTERNS,
    }

    for category, patterns in categories.items():
        print(f"\n{category} ({len(patterns)} patterns)")
        print("-" * 40)
        for pattern, _, severity, correction in patterns:
            sev_label = ["", "LOW", "MEDIUM", "HIGH", "CRITICAL", "TERMINAL"][severity]
            print(f"  [{sev_label}] /{pattern}/")
            print(f"         → {correction[:80]}")


def cli_history():
    """Print violation history."""
    detector = PassivityDetector()
    stats = detector.get_stats()
    print(json.dumps(stats, indent=2))


def cli_test():
    """Run self-test with known inputs."""
    detector = PassivityDetector()

    test_cases = [
        # (input, should_be_passive, description)
        ("Would you like me to try option A or B?", True, "Question + menu"),
        ("Here are your options:\n1. **Build API**\n2. **Write tests**", True, "Menu"),
        ("I'll wait for your feedback before proceeding.", True, "Stopping"),
        ("In summary, here's what we accomplished today.", True, "Summary without action"),
        ("Running ./engine/evolve next to select strategy...\n```bash\n./engine/evolve select\n```", False, "Active execution"),
        ("Shall I proceed with the implementation?", True, "Question"),
        ("I'm happy to help with that!", True, "Assistant mode"),
        ("Let me outline the approach before we begin.", True, "Planning theater"),
        ("Perhaps we could consider an alternative. I'm not sure if that's the right approach.", True, "Hedging"),
        ("═══ EVOLUTION CYCLE 5 ═══\nStrategy: S002\n```bash\n./engine/evolve fitness\n```", False, "Proper cycle output"),
    ]

    passed = 0
    failed = 0
    for text, expected_passive, desc in test_cases:
        detector.reset()
        result = detector.scan(text)
        actual = result["passive"]
        status = "PASS" if actual == expected_passive else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {desc}: expected={expected_passive}, got={actual}")
        if status == "FAIL":
            print(f"         violations={[v['type'] for v in result['violations']]}")
            print(f"         severity={result['severity']}")

    print(f"\n  Results: {passed}/{passed + failed} passed")
    return failed == 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 engine/enforce.py <command> [args]")
        print("Commands: scan, patterns, history, test")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "scan":
        if len(sys.argv) < 3:
            print('Usage: python3 engine/enforce.py scan "text to scan"')
            sys.exit(1)
        text = sys.argv[2]
        if text == "-":
            text = sys.stdin.read()
        cli_scan(text)

    elif cmd == "patterns":
        cli_patterns()

    elif cmd == "history":
        cli_history()

    elif cmd == "test":
        success = cli_test()
        sys.exit(0 if success else 1)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
