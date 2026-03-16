#!/usr/bin/env bash
# ============================================================================
# EVOLUTION FITNESS ENGINE — Mechanical fitness computation
# ============================================================================
# Detects project type, runs verification commands, and outputs a JSON
# fitness report with ZERO subjectivity. Only exit codes and test counts.
#
# Usage: ./engine/fitness.sh [project_dir]
# Output: JSON to stdout with fitness scores
# ============================================================================

set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

# --- Output accumulator ---
RESULTS=()
TOTAL_SCORE=0
TOTAL_WEIGHT=0
TESTS_PASSING=0
TESTS_TOTAL=0
BUILD_OK=false
LINT_OK=false
TYPES_OK=false

# --- Helpers ---
add_result() {
    local name="$1" passed="$2" weight="$3" detail="$4"
    local score=0
    [[ "$passed" == "true" ]] && score=1
    RESULTS+=("{\"name\":\"$name\",\"passed\":$passed,\"score\":$score,\"weight\":$weight,\"detail\":\"$detail\"}")
    TOTAL_SCORE=$(echo "$TOTAL_SCORE + $score * $weight" | bc -l 2>/dev/null || echo "$TOTAL_SCORE")
    TOTAL_WEIGHT=$(echo "$TOTAL_WEIGHT + $weight" | bc -l 2>/dev/null || echo "$TOTAL_WEIGHT")
}

parse_test_counts() {
    local output="$1" framework="$2"
    case "$framework" in
        jest|vitest)
            TESTS_PASSING=$(echo "$output" | grep -oP 'Tests:\s+\K\d+(?= passed)' 2>/dev/null || echo "0")
            local failed=$(echo "$output" | grep -oP 'Tests:\s+\d+ passed,\s+\K\d+(?= failed)' 2>/dev/null || echo "0")
            TESTS_TOTAL=$((TESTS_PASSING + failed))
            ;;
        pytest)
            TESTS_PASSING=$(echo "$output" | grep -oP '\K\d+(?= passed)' 2>/dev/null || echo "0")
            local failed=$(echo "$output" | grep -oP '\K\d+(?= failed)' 2>/dev/null || echo "0")
            TESTS_TOTAL=$((TESTS_PASSING + failed))
            ;;
        cargo)
            TESTS_PASSING=$(echo "$output" | grep -oP 'test result:.*\K\d+(?= passed)' 2>/dev/null || echo "0")
            local failed=$(echo "$output" | grep -oP 'test result:.*\K\d+(?= failed)' 2>/dev/null || echo "0")
            TESTS_TOTAL=$((TESTS_PASSING + failed))
            ;;
        go)
            TESTS_PASSING=$(echo "$output" | grep -c '^ok' 2>/dev/null || echo "0")
            local failed=$(echo "$output" | grep -c '^FAIL' 2>/dev/null || echo "0")
            TESTS_TOTAL=$((TESTS_PASSING + failed))
            ;;
        *)
            # Generic: just use exit code
            TESTS_TOTAL=1
            ;;
    esac
    [[ "$TESTS_TOTAL" -eq 0 ]] && TESTS_TOTAL=1
}

# --- Detect and run ---

# Node.js / JavaScript / TypeScript
if [[ -f "package.json" ]]; then
    # Tests
    if grep -q '"test"' package.json 2>/dev/null; then
        TEST_OUTPUT=$(npm test 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
        local_framework="jest"
        grep -q "vitest" package.json 2>/dev/null && local_framework="vitest"
        parse_test_counts "$TEST_OUTPUT" "$local_framework"
        add_result "tests" "$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)" "0.40" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL"
    fi

    # Build
    if grep -q '"build"' package.json 2>/dev/null; then
        npm run build >/dev/null 2>&1 && BUILD_OK=true || BUILD_OK=false
        add_result "build" "$BUILD_OK" "0.20" ""
    fi

    # Lint
    if grep -q '"lint"' package.json 2>/dev/null; then
        npm run lint >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "0.15" ""
    elif command -v eslint &>/dev/null; then
        eslint . --max-warnings 0 >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "0.15" ""
    fi

    # TypeScript
    if [[ -f "tsconfig.json" ]] && command -v tsc &>/dev/null; then
        tsc --noEmit >/dev/null 2>&1 && TYPES_OK=true || TYPES_OK=false
        add_result "types" "$TYPES_OK" "0.15" ""
    fi

# Python
elif [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "requirements.txt" ]]; then
    # Tests
    if command -v pytest &>/dev/null; then
        TEST_OUTPUT=$(pytest --tb=short 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
        parse_test_counts "$TEST_OUTPUT" "pytest"
        add_result "tests" "$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)" "0.40" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL"
    fi

    # Lint
    if command -v ruff &>/dev/null; then
        ruff check . >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
        add_result "lint" "$LINT_OK" "0.15" ""
    fi

    # Types
    if command -v mypy &>/dev/null; then
        mypy . >/dev/null 2>&1 && TYPES_OK=true || TYPES_OK=false
        add_result "types" "$TYPES_OK" "0.15" ""
    fi

# Rust
elif [[ -f "Cargo.toml" ]]; then
    # Tests
    TEST_OUTPUT=$(cargo test 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
    parse_test_counts "$TEST_OUTPUT" "cargo"
    add_result "tests" "$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)" "0.40" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL"

    # Build
    cargo build >/dev/null 2>&1 && BUILD_OK=true || BUILD_OK=false
    add_result "build" "$BUILD_OK" "0.20" ""

    # Lint
    cargo clippy -- -D warnings >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
    add_result "lint" "$LINT_OK" "0.15" ""

# Go
elif [[ -f "go.mod" ]]; then
    TEST_OUTPUT=$(go test ./... 2>&1) && TEST_EXIT=0 || TEST_EXIT=$?
    parse_test_counts "$TEST_OUTPUT" "go"
    add_result "tests" "$([[ $TEST_EXIT -eq 0 ]] && echo true || echo false)" "0.40" "exit:$TEST_EXIT tests:$TESTS_PASSING/$TESTS_TOTAL"

    go build ./... >/dev/null 2>&1 && BUILD_OK=true || BUILD_OK=false
    add_result "build" "$BUILD_OK" "0.20" ""

    go vet ./... >/dev/null 2>&1 && LINT_OK=true || LINT_OK=false
    add_result "lint" "$LINT_OK" "0.15" ""

# Makefile fallback
elif [[ -f "Makefile" ]]; then
    if grep -q '^test:' Makefile 2>/dev/null; then
        make test >/dev/null 2>&1 && add_result "tests" "true" "0.40" "" || add_result "tests" "false" "0.40" ""
    fi
    if grep -q '^build:' Makefile 2>/dev/null; then
        make build >/dev/null 2>&1 && add_result "build" "true" "0.20" "" || add_result "build" "false" "0.20" ""
    fi
    if grep -q '^lint:' Makefile 2>/dev/null; then
        make lint >/dev/null 2>&1 && add_result "lint" "true" "0.15" "" || add_result "lint" "false" "0.15" ""
    fi
fi

# --- Compute overall fitness ---
if (( $(echo "$TOTAL_WEIGHT > 0" | bc -l 2>/dev/null || echo 0) )); then
    FITNESS=$(echo "scale=4; $TOTAL_SCORE / $TOTAL_WEIGHT" | bc -l 2>/dev/null || echo "0")
else
    FITNESS="0"
fi

# --- Output JSON ---
RESULTS_JSON=$(IFS=,; echo "${RESULTS[*]}")
cat <<EOF
{
  "fitness": $FITNESS,
  "tests_passing": $TESTS_PASSING,
  "tests_total": $TESTS_TOTAL,
  "build": $BUILD_OK,
  "lint": $LINT_OK,
  "types": $TYPES_OK,
  "checks": [$RESULTS_JSON],
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
