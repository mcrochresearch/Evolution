#!/usr/bin/env bash
# ============================================================================
# EVOLUTION FITNESS ENGINE — Mechanical fitness computation
# ============================================================================
# Detects project type, runs verification commands, and outputs a JSON
# fitness report with ZERO subjectivity. Only exit codes and test counts.
#
# Features:
# - Auto-detects 6 project types (Node, Python, Rust, Go, Make, generic)
# - Parses test counts from framework output (Jest, Vitest, Pytest, Cargo, Go)
# - Weighted scoring: tests (0.40), build (0.20), lint (0.15), types (0.15)
# - Timeout protection: kills long-running commands after TIMEOUT_SEC
# - Explicit error reporting: no silent failures
# - Portable: works on both GNU/Linux and macOS (no GNU-only extensions)
#
# Usage: ./engine/fitness.sh [project_dir]
# Output: JSON to stdout with fitness scores
# ============================================================================

set -euo pipefail

# --- Manual fitness mode for non-code goals ---
# Usage: ./engine/fitness.sh --manual <score> [description]
# Score: 0.0 to 1.0
# Example: ./engine/fitness.sh --manual 0.6 "Landed 3 new leads, MRR up 5%"
if [[ "${1:-}" == "--manual" ]]; then
    SCORE="${2:-}"
    DESC="${3:-manual assessment}"
    if [[ -z "$SCORE" ]]; then
        echo '{"error":"Usage: fitness.sh --manual <score> [description]. Score must be 0.0-1.0"}' >&2
        exit 1
    fi
    # Validate score range
    VALID=$(python3 -c "
s = float('$SCORE')
if 0.0 <= s <= 1.0:
    print('ok')
else:
    print('bad')
" 2>/dev/null || echo "bad")
    if [[ "$VALID" != "ok" ]]; then
        echo "{\"error\":\"Score must be between 0.0 and 1.0, got: $SCORE\"}" >&2
        exit 1
    fi
    TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    python3 -c "
import json
print(json.dumps({
    'fitness': float('$SCORE'),
    'mode': 'manual',
    'description': '$DESC',
    'tests_passing': 0,
    'tests_total': 0,
    'test_count_confidence': 0.0,
    'build': False,
    'lint': False,
    'types': False,
    'project_type': 'manual',
    'checks': [{'name': 'manual', 'passed': float('$SCORE') >= 0.5, 'score': float('$SCORE'), 'weight': 1.0, 'detail': '$DESC'}],
    'errors': [],
    'timeout_sec': 0,
    'environment': {},
    'timestamp': '$TIMESTAMP'
}, indent=2))
"
    exit 0
fi

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

# --- Configuration (all overridable via environment) ---
TIMEOUT_SEC="${EVOLUTION_TIMEOUT:-120}"    # 2 minute default
WEIGHT_TESTS="${EVOLUTION_WEIGHT_TESTS:-0.40}"
WEIGHT_BUILD="${EVOLUTION_WEIGHT_BUILD:-0.20}"
WEIGHT_LINT="${EVOLUTION_WEIGHT_LINT:-0.15}"
WEIGHT_TYPES="${EVOLUTION_WEIGHT_TYPES:-0.15}"

# --- Output accumulator ---
RESULTS=()
TOTAL_SCORE=0
TOTAL_WEIGHT=0
TESTS_PASSING=0
TESTS_TOTAL=0
BUILD_OK=false
LINT_OK=false
TYPES_OK=false
ERRORS=()
DETECTED_TYPE="unknown"

# --- Helpers ---
add_result() {
    local name="$1" passed="$2" weight="$3" detail="$4" score="${5:-}"
    # Use continuous score if provided, otherwise binary
    if [[ -z "$score" ]]; then
        score=0
        [[ "$passed" == "true" ]] && score=1
    fi
    # Store as tab-separated fields; python3 will JSON-escape them later
    RESULTS+=("${name}	${passed}	${score}	${weight}	${detail}")
    TOTAL_SCORE=$(python3 -c "print($TOTAL_SCORE + $score * $weight)" 2>/dev/null || echo "$TOTAL_SCORE")
    TOTAL_WEIGHT=$(python3 -c "print($TOTAL_WEIGHT + $weight)" 2>/dev/null || echo "$TOTAL_WEIGHT")
}

add_error() {
    ERRORS+=("$1")
}

# Run a command with timeout protection
run_with_timeout() {
    local cmd="$1"
    if command -v timeout &>/dev/null; then
        timeout "$TIMEOUT_SEC" bash -c "$cmd" 2>&1
    elif command -v gtimeout &>/dev/null; then
        # macOS with coreutils installed via Homebrew
        gtimeout "$TIMEOUT_SEC" bash -c "$cmd" 2>&1
    else
        # Fallback: run without timeout but warn
        bash -c "$cmd" 2>&1
    fi
}

# Parse test counts from framework output using python3 for portability.
# Each framework has a different output format — python3 regex handles them all
# without relying on GNU grep -oP.
parse_test_counts() {
    local output="$1" framework="$2"
    local counts
    counts=$(python3 -c "
import re, sys

output = sys.stdin.read()
framework = '$framework'
passing = 0
failed = 0
errors = 0

if framework in ('jest', 'vitest'):
    # Jest/Vitest: 'Tests:  5 passed, 2 failed, 7 total'
    m = re.search(r'Tests:\s+(\d+)\s+passed', output)
    if m:
        passing = int(m.group(1))
    m = re.search(r'(\d+)\s+failed', output)
    if m:
        failed = int(m.group(1))
    # Fallback: mocha-style 'X passing' / 'X failing'
    if passing == 0 and failed == 0:
        m = re.search(r'(\d+)\s+passing', output)
        if m:
            passing = int(m.group(1))
        m = re.search(r'(\d+)\s+failing', output)
        if m:
            failed = int(m.group(1))

elif framework == 'pytest':
    # Pytest: '5 passed, 2 failed' or '5 passed'
    m = re.search(r'(\d+)\s+passed', output)
    if m:
        passing = int(m.group(1))
    m = re.search(r'(\d+)\s+failed', output)
    if m:
        failed = int(m.group(1))
    m = re.search(r'(\d+)\s+error', output)
    if m:
        errors = int(m.group(1))

elif framework == 'cargo':
    # Cargo: 'test result: ok. 5 passed; 0 failed; 0 ignored'
    m = re.search(r'test result:.*?(\d+)\s+passed', output)
    if m:
        passing = int(m.group(1))
    m = re.search(r'test result:.*?(\d+)\s+failed', output)
    if m:
        failed = int(m.group(1))

elif framework == 'go':
    # Go: 'ok  package  0.005s' per passing, 'FAIL' per failing
    passing = len(re.findall(r'^ok\b', output, re.MULTILINE))
    failed = len(re.findall(r'^FAIL\b', output, re.MULTILINE))

total = passing + failed + errors
print(f'{passing} {total}')
" <<< "$output" 2>/dev/null) || counts="0 0"

    TESTS_PASSING=$(echo "$counts" | cut -d' ' -f1)
    TESTS_TOTAL=$(echo "$counts" | cut -d' ' -f2)

    # Safeguard: ensure non-zero total
    [[ "$TESTS_TOTAL" -eq 0 ]] && TESTS_TOTAL=1

    # Warn if parsing likely failed
    if [[ "$TESTS_PASSING" -eq 0 && "$TESTS_TOTAL" -eq 1 ]]; then
        add_error "Could not parse test counts from $framework output — using exit code only"
    fi
}

# --- Detect and run ---

# Node.js / JavaScript / TypeScript
if [[ -f "package.json" ]]; then
    DETECTED_TYPE="node"

    # Tests
    if grep -q '"test"' package.json 2>/dev/null; then
        TEST_OUTPUT=$(run_with_timeout "npm test" 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
        if [[ $TEST_EXIT -eq 124 ]]; then
            add_error "Tests timed out after ${TIMEOUT_SEC}s"
            add_result "tests" "false" "$WEIGHT_TESTS" "TIMEOUT after ${TIMEOUT_SEC}s"
        else
            local_framework="jest"
            grep -q "vitest" package.json 2>/dev/null && local_framework="vitest"
            parse_test_counts "$TEST_OUTPUT" "$local_framework"
            test_passed="$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)"
            test_score=$(python3 -c "print(round($TESTS_PASSING / max($TESTS_TOTAL, 1), 4))" 2>/dev/null || echo "$([[ $TEST_EXIT -eq 0 ]] && echo 1 || echo 0)")
            add_result "tests" "$test_passed" "$WEIGHT_TESTS" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL" "$test_score"
        fi
    else
        add_error "No 'test' script found in package.json"
    fi

    # Build
    if grep -q '"build"' package.json 2>/dev/null; then
        run_with_timeout "npm run build" >/dev/null 2>&1 && BUILD_OK=true || BUILD_OK=false
        add_result "build" "$BUILD_OK" "$WEIGHT_BUILD" ""
    fi

    # Lint
    if grep -q '"lint"' package.json 2>/dev/null; then
        run_with_timeout "npm run lint" >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "$WEIGHT_LINT" ""
    elif command -v eslint &>/dev/null; then
        run_with_timeout "eslint . --max-warnings 0" >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "$WEIGHT_LINT" ""
    fi

    # TypeScript type checking
    if [[ -f "tsconfig.json" ]] && command -v tsc &>/dev/null; then
        run_with_timeout "tsc --noEmit" >/dev/null 2>&1 && TYPES_OK=true || TYPES_OK=false
        add_result "types" "$TYPES_OK" "$WEIGHT_TYPES" ""
    fi

# Python
elif [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "requirements.txt" ]]; then
    DETECTED_TYPE="python"

    # Tests
    if command -v pytest &>/dev/null; then
        TEST_OUTPUT=$(run_with_timeout "pytest --tb=short" 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
        if [[ $TEST_EXIT -eq 124 ]]; then
            add_error "Tests timed out after ${TIMEOUT_SEC}s"
            add_result "tests" "false" "$WEIGHT_TESTS" "TIMEOUT"
        else
            parse_test_counts "$TEST_OUTPUT" "pytest"
            test_passed="$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)"
            test_score=$(python3 -c "print(round($TESTS_PASSING / max($TESTS_TOTAL, 1), 4))" 2>/dev/null || echo "$([[ $TEST_EXIT -eq 0 ]] && echo 1 || echo 0)")
            add_result "tests" "$test_passed" "$WEIGHT_TESTS" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL" "$test_score"
        fi
    elif [[ -d "tests" ]] || [[ -d "test" ]]; then
        add_error "Test directory found but pytest not installed"
    fi

    # Lint
    if command -v ruff &>/dev/null; then
        run_with_timeout "ruff check ." >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "$WEIGHT_LINT" ""
    fi

    # Types
    if command -v mypy &>/dev/null; then
        run_with_timeout "mypy ." >/dev/null 2>&1 && TYPES_OK=true || TYPES_OK=false
        add_result "types" "$TYPES_OK" "$WEIGHT_TYPES" ""
    fi

# Rust
elif [[ -f "Cargo.toml" ]]; then
    DETECTED_TYPE="rust"

    TEST_OUTPUT=$(run_with_timeout "cargo test" 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
    if [[ $TEST_EXIT -eq 124 ]]; then
        add_error "Tests timed out after ${TIMEOUT_SEC}s"
        add_result "tests" "false" "$WEIGHT_TESTS" "TIMEOUT"
    else
        parse_test_counts "$TEST_OUTPUT" "cargo"
        test_passed="$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)"
        test_score=$(python3 -c "print(round($TESTS_PASSING / max($TESTS_TOTAL, 1), 4))" 2>/dev/null || echo "$([[ $TEST_EXIT -eq 0 ]] && echo 1 || echo 0)")
        add_result "tests" "$test_passed" "$WEIGHT_TESTS" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL" "$test_score"
    fi

    run_with_timeout "cargo build" >/dev/null 2>&1 && BUILD_OK=true || BUILD_OK=false
    add_result "build" "$BUILD_OK" "$WEIGHT_BUILD" ""

    if command -v cargo-clippy &>/dev/null || cargo clippy --version &>/dev/null; then
        run_with_timeout "cargo clippy -- -D warnings" >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "$WEIGHT_LINT" ""
    fi

# Go
elif [[ -f "go.mod" ]]; then
    DETECTED_TYPE="go"

    TEST_OUTPUT=$(run_with_timeout "go test ./..." 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
    if [[ $TEST_EXIT -eq 124 ]]; then
        add_error "Tests timed out after ${TIMEOUT_SEC}s"
        add_result "tests" "false" "$WEIGHT_TESTS" "TIMEOUT"
    else
        parse_test_counts "$TEST_OUTPUT" "go"
        test_passed="$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)"
        test_score=$(python3 -c "print(round($TESTS_PASSING / max($TESTS_TOTAL, 1), 4))" 2>/dev/null || echo "$([[ $TEST_EXIT -eq 0 ]] && echo 1 || echo 0)")
        add_result "tests" "$test_passed" "$WEIGHT_TESTS" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL" "$test_score"
    fi

    run_with_timeout "go build ./..." >/dev/null 2>&1 && BUILD_OK=true || BUILD_OK=false
    add_result "build" "$BUILD_OK" "$WEIGHT_BUILD" ""

    run_with_timeout "go vet ./..." >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
    add_result "lint" "$LINT_OK" "$WEIGHT_LINT" ""

# Makefile fallback
elif [[ -f "Makefile" ]]; then
    DETECTED_TYPE="make"

    if grep -q '^test:' Makefile 2>/dev/null; then
        run_with_timeout "make test" >/dev/null 2>&1 && add_result "tests" "true" "$WEIGHT_TESTS" "" || add_result "tests" "false" "$WEIGHT_TESTS" ""
    fi
    if grep -q '^build:' Makefile 2>/dev/null; then
        run_with_timeout "make build" >/dev/null 2>&1 && add_result "build" "true" "$WEIGHT_BUILD" "" || add_result "build" "false" "$WEIGHT_BUILD" ""
    fi
    if grep -q '^lint:' Makefile 2>/dev/null; then
        run_with_timeout "make lint" >/dev/null 2>&1 && add_result "lint" "true" "$WEIGHT_LINT" "" || add_result "lint" "false" "$WEIGHT_LINT" ""
    fi

else
    DETECTED_TYPE="none"
    add_error "No recognized project type found (no package.json, pyproject.toml, Cargo.toml, go.mod, or Makefile)"
fi

# --- Compute overall fitness ---
# Test count confidence: low test counts discount the fitness score.
# 0 tests = 0 confidence (multiplier 0.0)
# 1 test  = low confidence (multiplier 0.3)
# 5 tests = moderate (multiplier 0.7)
# 10+ tests = full confidence (multiplier 1.0)
# This prevents 1/1 passing tests from scoring the same as 100/100.
TEST_COUNT_CONFIDENCE=$(python3 -c "
import math
n = $TESTS_TOTAL
if n == 0:
    print(0.0)
else:
    # Logarithmic curve: saturates around 10 tests
    confidence = min(1.0, math.log(n + 1) / math.log(11))
    print(round(confidence, 4))
" 2>/dev/null || echo "1.0")

if [[ ${#RESULTS[@]} -gt 0 ]]; then
    FITNESS=$(python3 -c "
tw = $TOTAL_WEIGHT
ts = $TOTAL_SCORE
raw = ts / max(tw, 0.001)
# Apply test count confidence as a multiplier on the test component
# Other components (build, lint, types) are unaffected
confidence = $TEST_COUNT_CONFIDENCE
# Blend: if test confidence is low, cap overall fitness proportionally
# Even perfect build+lint+types can't compensate for no tests
test_weight_fraction = $WEIGHT_TESTS / max(tw, 0.001)
adjusted = raw * (1.0 - test_weight_fraction * (1.0 - confidence))
print(round(adjusted, 4))
" 2>/dev/null || echo "0")
else
    FITNESS="0"
fi

# --- Collect environment fingerprint ---
ENV_PYTHON3_VERSION=$(python3 --version 2>/dev/null | head -1 || echo "unavailable")
ENV_NODE_VERSION=$(node --version 2>/dev/null || echo "not installed")
ENV_OS=$(uname -s 2>/dev/null || echo "unknown")
ENV_OS_VERSION=$(uname -r 2>/dev/null || echo "unknown")
ENV_HAS_BC=$( command -v bc &>/dev/null && echo "true" || echo "false" )
ENV_HAS_TIMEOUT=$( (command -v timeout &>/dev/null || command -v gtimeout &>/dev/null) && echo "true" || echo "false" )
ENV_HAS_NPM=$( command -v npm &>/dev/null && echo "true" || echo "false" )
ENV_HAS_PYTEST=$( command -v pytest &>/dev/null && echo "true" || echo "false" )
ENV_HAS_CARGO=$( command -v cargo &>/dev/null && echo "true" || echo "false" )
ENV_HAS_GO=$( command -v go &>/dev/null && echo "true" || echo "false" )
ENV_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# --- Output JSON via python3 to guarantee valid JSON ---
# Pass all data to python3 which handles escaping, formatting, and construction.
# Results are passed as tab-separated lines via a temp file to avoid argument length limits.

RESULTS_FILE=$(mktemp)
ERRORS_FILE=$(mktemp)
# Trap ensures temp files are cleaned up even on early exit (set -e)
trap 'rm -f "$RESULTS_FILE" "$ERRORS_FILE"' EXIT

for r in "${RESULTS[@]+"${RESULTS[@]}"}"; do
    echo "$r" >> "$RESULTS_FILE"
done

for e in "${ERRORS[@]+"${ERRORS[@]}"}"; do
    echo "$e" >> "$ERRORS_FILE"
done

python3 -c "
import json, sys

fitness = float('$FITNESS')
tests_passing = int('$TESTS_PASSING')
tests_total = int('$TESTS_TOTAL')
build_ok = True if '$BUILD_OK' == 'true' else False
lint_ok = True if '$LINT_OK' == 'true' else False
types_ok = True if '$TYPES_OK' == 'true' else False
project_type = '$DETECTED_TYPE'
timeout_sec = int('$TIMEOUT_SEC')

# Parse results from tab-separated file
checks = []
with open('$RESULTS_FILE') as f:
    for line in f:
        line = line.rstrip('\n')
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) == 5:
            name, passed, score, weight, detail = parts
            checks.append({
                'name': name,
                'passed': passed == 'true',
                'score': float(score),
                'weight': float(weight),
                'detail': detail
            })

# Parse errors
errors = []
with open('$ERRORS_FILE') as f:
    for line in f:
        line = line.rstrip('\n')
        if line:
            errors.append(line)

environment = {
    'python3': '$ENV_PYTHON3_VERSION',
    'node': '$ENV_NODE_VERSION',
    'os': '$ENV_OS',
    'os_version': '$ENV_OS_VERSION',
    'tools': {
        'bc': $ENV_HAS_BC,
        'timeout': $ENV_HAS_TIMEOUT,
        'npm': $ENV_HAS_NPM,
        'pytest': $ENV_HAS_PYTEST,
        'cargo': $ENV_HAS_CARGO,
        'go': $ENV_HAS_GO
    },
    'timestamp': '$ENV_TIMESTAMP'
}

test_count_confidence = float('$TEST_COUNT_CONFIDENCE')

output = {
    'fitness': fitness,
    'tests_passing': tests_passing,
    'tests_total': tests_total,
    'test_count_confidence': test_count_confidence,
    'build': build_ok,
    'lint': lint_ok,
    'types': types_ok,
    'project_type': project_type,
    'checks': checks,
    'errors': errors,
    'timeout_sec': timeout_sec,
    'environment': environment,
    'timestamp': '$ENV_TIMESTAMP'
}

print(json.dumps(output, indent=2))
"

# Clean up temp files
rm -f "$RESULTS_FILE" "$ERRORS_FILE"
