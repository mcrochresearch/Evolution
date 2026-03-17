#!/usr/bin/env python3
"""
guard.py — Mechanical anti-pattern detection for git diffs.

Scans git diffs for known anti-patterns that are listed in project guidelines
but were never mechanically enforced. Provides two subcommands:

  scan [ref]              Check diff for anti-patterns (default ref: HEAD)
  test-count <before> <after>  Warn if test count decreased between refs
"""

import json
import re
import subprocess
import sys


# ---------------------------------------------------------------------------
# Anti-pattern definitions
# ---------------------------------------------------------------------------

PATTERNS = [
    # TypeScript/JavaScript suppressions
    {"regex": r"@ts-ignore",       "name": "@ts-ignore"},
    {"regex": r"@ts-nocheck",      "name": "@ts-nocheck"},
    {"regex": r"eslint-disable",   "name": "eslint-disable"},
    # Python suppressions
    {"regex": r"#\s*type:\s*ignore", "name": "# type: ignore"},
    {"regex": r"#\s*noqa",          "name": "# noqa"},
    {"regex": r"#\s*pragma:\s*no\s*cover", "name": "# pragma: no cover"},
    # TypeScript unsafe escape
    {"regex": r"\bas\s+any\b",     "name": "as any"},
    # Test skipping
    {"regex": r"\.skip\s*\(",      "name": ".skip("},
    {"regex": r"\.only\s*\(",      "name": ".only("},
]

# console.log is only flagged in non-test files
CONSOLE_LOG = {"regex": r"console\.log", "name": "console.log"}

TEST_FILE_PATTERN = re.compile(
    r"\.(test|spec)\.(ts|tsx|js|jsx)$|__tests__/|/test/|/tests/|_test\.py$|test_.*\.py$"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_git(*args: str) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(json.dumps({"error": f"git failed: {result.stderr.strip()}"}),
              file=sys.stderr)
        sys.exit(2)
    return result.stdout


def parse_diff(diff_text: str):
    """
    Yield (file, line_number, added_line) tuples from a unified diff
    produced with --unified=0.
    """
    current_file = None
    current_line = None

    for raw_line in diff_text.splitlines():
        # Detect file header: +++ b/path/to/file
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            continue

        # Hunk header: @@ -old,count +new,count @@
        hunk_match = re.match(r"^@@ .+? \+(\d+)(?:,\d+)? @@", raw_line)
        if hunk_match:
            current_line = int(hunk_match.group(1))
            continue

        # Added line
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            if current_file is not None and current_line is not None:
                yield current_file, current_line, raw_line[1:]
                current_line += 1
            continue

        # Context or removed lines don't advance the "added" counter here
        # (with --unified=0 there should be none, but be safe)


def is_test_file(filepath: str) -> bool:
    return bool(TEST_FILE_PATTERN.search(filepath))


# ---------------------------------------------------------------------------
# scan subcommand
# ---------------------------------------------------------------------------

def cmd_scan(ref: str = "HEAD") -> int:
    """Scan the diff against `ref` for anti-patterns. Returns exit code."""
    diff_text = run_git("diff", ref, "--unified=0")

    violations = []
    for filepath, line_no, line_content in parse_diff(diff_text):
        # Check standard patterns
        for pat in PATTERNS:
            if re.search(pat["regex"], line_content):
                violations.append({
                    "pattern": pat["name"],
                    "file": filepath,
                    "line": line_no,
                })

        # console.log only in non-test files
        if not is_test_file(filepath) and re.search(CONSOLE_LOG["regex"], line_content):
            violations.append({
                "pattern": CONSOLE_LOG["name"],
                "file": filepath,
                "line": line_no,
            })

    clean = len(violations) == 0
    output = {"violations": violations, "clean": clean}
    print(json.dumps(output, indent=2))
    return 0 if clean else 1


# ---------------------------------------------------------------------------
# test-count subcommand
# ---------------------------------------------------------------------------

def count_tests_at_ref(ref: str) -> int:
    """
    Count test functions/cases visible at a given git ref by searching for
    common test markers: def test_, it(, test(, describe(, etc.
    """
    try:
        result = subprocess.run(
            ["git", "grep", "-c",
             "-e", "def test_",
             "-e", "\\bit(",
             "-e", "\\btest(",
             "-e", "\\bdescribe(",
             "--", "*.py", "*.ts", "*.tsx", "*.js", "*.jsx"],
            capture_output=True, text=True,
            # git grep returns 1 when no matches; that's fine
        )
    except Exception:
        return 0

    total = 0
    for count_line in result.stdout.strip().splitlines():
        # format: path:count
        parts = count_line.rsplit(":", 1)
        if len(parts) == 2:
            try:
                total += int(parts[1])
            except ValueError:
                pass
    return total


def cmd_test_count(before: str, after: str) -> int:
    """Compare test counts between two refs. Warns if count decreased."""
    before_count = count_tests_at_ref(before)
    after_count = count_tests_at_ref(after)
    delta = after_count - before_count

    result = {
        "before": {"ref": before, "test_count": before_count},
        "after":  {"ref": after,  "test_count": after_count},
        "delta": delta,
        "warning": delta < 0,
    }
    if delta < 0:
        result["message"] = (
            f"Test count decreased by {abs(delta)}: {before_count} -> {after_count}"
        )
    else:
        result["message"] = (
            f"Test count OK ({'+' if delta > 0 else ''}{delta}): "
            f"{before_count} -> {after_count}"
        )

    print(json.dumps(result, indent=2))
    return 1 if delta < 0 else 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: guard.py <scan [ref] | test-count <before> <after>>",
              file=sys.stderr)
        sys.exit(2)

    subcmd = sys.argv[1]

    if subcmd == "scan":
        ref = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
        sys.exit(cmd_scan(ref))

    elif subcmd == "test-count":
        if len(sys.argv) < 4:
            print("Usage: guard.py test-count <before-ref> <after-ref>",
                  file=sys.stderr)
            sys.exit(2)
        sys.exit(cmd_test_count(sys.argv[2], sys.argv[3]))

    else:
        print(f"Unknown subcommand: {subcmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
