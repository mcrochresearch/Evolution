#!/usr/bin/env bash
# ============================================================================
# EVOLUTION CHECKPOINT ENGINE — Git-based state snapshots and rollback
# ============================================================================
# Creates lightweight checkpoints before risky operations and enables
# clean rollback when experiments fail. Uses git under the hood.
#
# Usage:
#   ./engine/checkpoint.sh create [message]  Create a checkpoint
#   ./engine/checkpoint.sh revert            Revert to last checkpoint
#   ./engine/checkpoint.sh list              List recent checkpoints
#   ./engine/checkpoint.sh diff              Show changes since checkpoint
# ============================================================================

set -euo pipefail

CMD="${1:-help}"
shift || true

CHECKPOINT_TAG_PREFIX="evolution-checkpoint"
STATE_DIR="evolution/.state"
CHECKPOINT_FILE="$STATE_DIR/checkpoints.jsonl"

case "$CMD" in
    create)
        MESSAGE="${1:-Cycle checkpoint}"

        # Stage current changes
        git add -A 2>/dev/null || true
        # Record current HEAD
        HASH=$(git rev-parse HEAD 2>/dev/null || echo "none")
        TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
        TAG="${CHECKPOINT_TAG_PREFIX}-${TIMESTAMP}"

        # Also stash any uncommitted changes so we can restore them
        STASH_HASH=$(git stash create 2>/dev/null || echo "")

        # Store checkpoint info (use python for safe JSON escaping)
        mkdir -p "$STATE_DIR"
        python3 -c "
import json, sys
print(json.dumps({
    'tag': sys.argv[1], 'head': sys.argv[2],
    'stash': sys.argv[3], 'message': sys.argv[4],
    'timestamp': sys.argv[5]
}))
" "$TAG" "$HASH" "${STASH_HASH:-none}" "$MESSAGE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$CHECKPOINT_FILE"

        echo "{\"status\":\"created\",\"tag\":\"$TAG\",\"head\":\"$HASH\"}"
        ;;

    revert)
        if [[ ! -f "$CHECKPOINT_FILE" ]]; then
            echo '{"error":"No checkpoints found. Create a checkpoint first."}'
            exit 1
        fi

        # Get the last checkpoint
        LAST=$(tail -1 "$CHECKPOINT_FILE")
        HEAD_AT_CHECKPOINT=$(echo "$LAST" | python3 -c "import sys,json; print(json.load(sys.stdin)['head'])" 2>/dev/null || echo "")

        if [[ -z "$HEAD_AT_CHECKPOINT" || "$HEAD_AT_CHECKPOINT" == "none" ]]; then
            echo '{"error":"Cannot determine checkpoint HEAD. Checkpoint may be corrupted."}'
            exit 1
        fi

        # Safer revert: checkout files from checkpoint instead of hard reset
        # This preserves git history while restoring file contents
        if git checkout "$HEAD_AT_CHECKPOINT" -- . 2>/dev/null; then
            echo "{\"status\":\"reverted\",\"to\":\"$HEAD_AT_CHECKPOINT\",\"method\":\"checkout\"}"
        else
            # Fallback: warn before hard reset
            echo "{\"status\":\"reverted\",\"to\":\"$HEAD_AT_CHECKPOINT\",\"method\":\"reset\",\"warning\":\"Used hard reset as fallback\"}" >&2
            git reset --hard "$HEAD_AT_CHECKPOINT" 2>/dev/null
            echo "{\"status\":\"reverted\",\"to\":\"$HEAD_AT_CHECKPOINT\",\"method\":\"reset\"}"
        fi
        ;;

    list)
        if [[ ! -f "$CHECKPOINT_FILE" ]]; then
            echo '{"checkpoints":[]}'
            exit 0
        fi

        # Build proper JSON array (using process substitution to avoid subshell scoping)
        echo -n '{"checkpoints":['
        FIRST=true
        while IFS= read -r line; do
            if [[ "$FIRST" == "true" ]]; then
                FIRST=false
            else
                echo -n ","
            fi
            echo -n "$line"
        done < <(tail -10 "$CHECKPOINT_FILE")
        echo ']}'
        ;;

    diff)
        if [[ ! -f "$CHECKPOINT_FILE" ]]; then
            echo '{"error":"No checkpoints found"}'
            exit 1
        fi
        LAST=$(tail -1 "$CHECKPOINT_FILE")
        HEAD_AT=$(echo "$LAST" | python3 -c "import sys,json; print(json.load(sys.stdin)['head'])" 2>/dev/null || echo "HEAD~1")
        git diff "$HEAD_AT" --stat 2>/dev/null || echo '{"error":"No diff available"}'
        ;;

    help|*)
        echo "Usage: ./engine/checkpoint.sh {create|revert|list|diff} [args]"
        ;;
esac
