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
#
# Usage: ./engine/fitness.sh [project_dir]
# Output: JSON to stdout with fitness scores
# ============================================================================

set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

# --- Configuration ---
TIMEOUT_SEC="${EVOLUTION_TIMEOUT:-120}"  # 2 minute default, configurable

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
    local name="$1" passed="$2" weight="$3" detail="$4"
    local score=0
    [[ "$passed" == "true" ]] && score=1
    RESULTS+=("{\"name\":\"$name\",\"passed\":$passed,\"score\":$score,\"weight\":$weight,\"detail\":\"$detail\"}")
    TOTAL_SCORE=$(echo "$TOTAL_SCORE + $score * $weight" | bc -l 2>/dev/null || echo "$TOTAL_SCORE")
    TOTAL_WEIGHT=$(echo "$TOTAL_WEIGHT + $weight" | bc -l 2>/dev/null || echo "$TOTAL_WEIGHT")
}

add_error() {
    ERRORS+=("\"$1\"")
}

# Run a command with timeout protection
run_with_timeout() {
    local cmd="$1"
    if command -v timeout &>/dev/null; then
        timeout "$TIMEOUT_SEC" bash -c "$cmd" 2>&1
    else
        # Fallback: run without timeout but warn
        bash -c "$cmd" 2>&1
    fi
}

# Parse test counts from framework output.
# Each framework has a different output format — we match the most common patterns.
parse_test_counts() {
    local output="$1" framework="$2"
    case "$framework" in
        jest|vitest)
            # Jest: "Tests:  5 passed, 2 failed, 7 total"
            # Vitest: similar format
            TESTS_PASSING=$(echo "$output" | grep -oP 'Tests:\s+\K\d+(?= passed)' 2>/dev/null || echo "0")
            local failed=$(echo "$output" | grep -oP '\d+(?= failed)' 2>/dev/null | tail -1 || echo "0")
            TESTS_TOTAL=$((TESTS_PASSING + failed))
            # Fallback: try "X passing" format (mocha)
            if [[ "$TESTS_TOTAL" -eq 0 ]]; then
                TESTS_PASSING=$(echo "$output" | grep -oP '\K\d+(?= passing)' 2>/dev/null || echo "0")
                failed=$(echo "$output" | grep -oP '\K\d+(?= failing)' 2>/dev/null || echo "0")
                TESTS_TOTAL=$((TESTS_PASSING + failed))
            fi
            ;;
        pytest)
            # Pytest: "5 passed, 2 failed" or "5 passed"
            TESTS_PASSING=$(echo "$output" | grep -oP '\K\d+(?= passed)' 2>/dev/null | tail -1 || echo "0")
            local failed=$(echo "$output" | grep -oP '\K\d+(?= failed)' 2>/dev/null | tail -1 || echo "0")
            local errors=$(echo "$output" | grep -oP '\K\d+(?= error)' 2>/dev/null | tail -1 || echo "0")
            TESTS_TOTAL=$((TESTS_PASSING + failed + errors))
            ;;
        cargo)
            # Cargo: "test result: ok. 5 passed; 0 failed; 0 ignored"
            TESTS_PASSING=$(echo "$output" | grep -oP 'test result:.*\K\d+(?= passed)' 2>/dev/null || echo "0")
            local failed=$(echo "$output" | grep -oP 'test result:.*\K\d+(?= failed)' 2>/dev/null || echo "0")
            TESTS_TOTAL=$((TESTS_PASSING + failed))
            ;;
        go)
            # Go: "ok  package  0.005s" per passing package, "FAIL" per failing
            TESTS_PASSING=$(echo "$output" | grep -c '^ok' 2>/dev/null || echo "0")
            local failed=$(echo "$output" | grep -c '^FAIL' 2>/dev/null || echo "0")
            TESTS_TOTAL=$((TESTS_PASSING + failed))
            ;;
        *)
            # Generic: just use exit code, count as 1 test
            TESTS_TOTAL=1
            ;;
    esac

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
            add_result "tests" "false" "0.40" "TIMEOUT after ${TIMEOUT_SEC}s"
        else
            local_framework="jest"
            grep -q "vitest" package.json 2>/dev/null && local_framework="vitest"
            parse_test_counts "$TEST_OUTPUT" "$local_framework"
            add_result "tests" "$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)" "0.40" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL"
        fi
    else
        add_error "No 'test' script found in package.json"
    fi

    # Build
    if grep -q '"build"' package.json 2>/dev/null; then
        run_with_timeout "npm run build" >/dev/null 2>&1 && BUILD_OK=true || BUILD_OK=false
        add_result "build" "$BUILD_OK" "0.20" ""
    fi

    # Lint
    if grep -q '"lint"' package.json 2>/dev/null; then
        run_with_timeout "npm run lint" >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "0.15" ""
    elif command -v eslint &>/dev/null; then
        run_with_timeout "eslint . --max-warnings 0" >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "0.15" ""
    fi

    # TypeScript type checking
    if [[ -f "tsconfig.json" ]] && command -v tsc &>/dev/null; then
        run_with_timeout "tsc --noEmit" >/dev/null 2>&1 && TYPES_OK=true || TYPES_OK=false
        add_result "types" "$TYPES_OK" "0.15" ""
    fi

# Python
elif [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "requirements.txt" ]]; then
    DETECTED_TYPE="python"

    # Tests
    if command -v pytest &>/dev/null; then
        TEST_OUTPUT=$(run_with_timeout "pytest --tb=short" 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
        if [[ $TEST_EXIT -eq 124 ]]; then
            add_error "Tests timed out after ${TIMEOUT_SEC}s"
            add_result "tests" "false" "0.40" "TIMEOUT"
        else
            parse_test_counts "$TEST_OUTPUT" "pytest"
            add_result "tests" "$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)" "0.40" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL"
        fi
    elif [[ -d "tests" ]] || [[ -d "test" ]]; then
        add_error "Test directory found but pytest not installed"
    fi

    # Lint
    if command -v ruff &>/dev/null; then
        run_with_timeout "ruff check ." >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "0.15" ""
    fi

    # Types
    if command -v mypy &>/dev/null; then
        run_with_timeout "mypy ." >/dev/null 2>&1 && TYPES_OK=true || TYPES_OK=false
        add_result "types" "$TYPES_OK" "0.15" ""
    fi

# Rust
elif [[ -f "Cargo.toml" ]]; then
    DETECTED_TYPE="rust"

    TEST_OUTPUT=$(run_with_timeout "cargo test" 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
    if [[ $TEST_EXIT -eq 124 ]]; then
        add_error "Tests timed out after ${TIMEOUT_SEC}s"
        add_result "tests" "false" "0.40" "TIMEOUT"
    else
        parse_test_counts "$TEST_OUTPUT" "cargo"
        add_result "tests" "$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)" "0.40" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL"
    fi

    run_with_timeout "cargo build" >/dev/null 2>&1 && BUILD_OK=true || BUILD_OK=false
    add_result "build" "$BUILD_OK" "0.20" ""

    if command -v cargo-clippy &>/dev/null || cargo clippy --version &>/dev/null; then
        run_with_timeout "cargo clippy -- -D warnings" >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "0.15" ""
    fi

# Go
elif [[ -f "go.mod" ]]; then
    DETECTED_TYPE="go"

    TEST_OUTPUT=$(run_with_timeout "go test ./..." 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
    if [[ $TEST_EXIT -eq 124 ]]; then
        add_error "Tests timed out after ${TIMEOUT_SEC}s"
        add_result "tests" "false" "0.40" "TIMEOUT"
    else
        parse_test_counts "$TEST_OUTPUT" "go"
        add_result "tests" "$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)" "0.40" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL"
    fi

    run_with_timeout "go build ./..." >/dev/null 2>&1 && BUILD_OK=true || BUILD_OK=false
    add_result "build" "$BUILD_OK" "0.20" ""

    run_with_timeout "go vet ./..." >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
    add_result "lint" "$LINT_OK" "0.15" ""

# Makefile fallback
elif [[ -f "Makefile" ]]; then
    DETECTED_TYPE="make"

    if grep -q '^test:' Makefile 2>/dev/null; then
        run_with_timeout "make test" >/dev/null 2>&1 && add_result "tests" "true" "0.40" "" || add_result "tests" "false" "0.40" ""
    fi
    if grep -q '^build:' Makefile 2>/dev/null; then
        run_with_timeout "make build" >/dev/null 2>&1 && add_result "build" "true" "0.20" "" || add_result "build" "false" "0.20" ""
    fi
    if grep -q '^lint:' Makefile 2>/dev/null; then
        run_with_timeout "make lint" >/dev/null 2>&1 && add_result "lint" "true" "0.15" "" || add_result "lint" "false" "0.15" ""
    fi

else
    DETECTED_TYPE="none"
    add_error "No recognized project type found (no package.json, pyproject.toml, Cargo.toml, go.mod, or Makefile)"
fi

# --- Compute overall fitness ---
if command -v bc &>/dev/null; then
    if (( $(echo "$TOTAL_WEIGHT > 0" | bc -l 2>/dev/null || echo 0) )); then
        FITNESS=$(echo "scale=4; $TOTAL_SCORE / $TOTAL_WEIGHT" | bc -l 2>/dev/null || echo "0")
    else
        FITNESS="0"
    fi
else
    # Fallback: Python for math if bc unavailable
    if [[ ${#RESULTS[@]} -gt 0 ]]; then
        FITNESS=$(python3 -c "print(round($TOTAL_SCORE / max($TOTAL_WEIGHT, 0.001), 4))" 2>/dev/null || echo "0")
    else
        FITNESS="0"
    fi
    add_error "bc not found — used Python fallback for arithmetic"
fi

# --- Output JSON ---
RESULTS_JSON=""
if [[ ${#RESULTS[@]} -gt 0 ]]; then
    RESULTS_JSON=$(IFS=,; echo "${RESULTS[*]}")
fi

ERRORS_JSON=""
if [[ ${#ERRORS[@]} -gt 0 ]]; then
    ERRORS_JSON=$(IFS=,; echo "${ERRORS[*]}")
fi

cat <<EOF
{
  "fitness": $FITNESS,
  "tests_passing": $TESTS_PASSING,
  "tests_total": $TESTS_TOTAL,
  "build": $BUILD_OK,
  "lint": $LINT_OK,
  "types": $TYPES_OK,
  "project_type": "$DETECTED_TYPE",
  "checks": [$RESULTS_JSON],
  "errors": [$ERRORS_JSON],
  "timeout_sec": $TIMEOUT_SEC,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
