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

case "$CMD" in
    create)
        MESSAGE="${1:-Cycle checkpoint}"
        # Stage current changes
        git add -A 2>/dev/null || true
        # Create a commit as checkpoint
        HASH=$(git stash create 2>/dev/null || echo "")
        if [[ -z "$HASH" ]]; then
            # No changes to stash, record current HEAD
            HASH=$(git rev-parse HEAD 2>/dev/null || echo "none")
        fi
        TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
        TAG="${CHECKPOINT_TAG_PREFIX}-${TIMESTAMP}"

        # Store checkpoint info
        mkdir -p evolution/.state
        echo "{\"tag\":\"$TAG\",\"hash\":\"$HASH\",\"head\":\"$(git rev-parse HEAD 2>/dev/null || echo none)\",\"message\":\"$MESSAGE\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >> evolution/.state/checkpoints.jsonl

        echo "{\"status\":\"created\",\"tag\":\"$TAG\",\"hash\":\"$HASH\"}"
        ;;

    revert)
        if [[ ! -f evolution/.state/checkpoints.jsonl ]]; then
            echo '{"error":"No checkpoints found"}'
            exit 1
        fi

        # Get the last checkpoint
        LAST=$(tail -1 evolution/.state/checkpoints.jsonl)
        HEAD_AT_CHECKPOINT=$(echo "$LAST" | python3 -c "import sys,json; print(json.load(sys.stdin)['head'])" 2>/dev/null || echo "")

        if [[ -z "$HEAD_AT_CHECKPOINT" || "$HEAD_AT_CHECKPOINT" == "none" ]]; then
            echo '{"error":"Cannot determine checkpoint HEAD"}'
            exit 1
        fi

        # Reset to checkpoint state
        git checkout "$HEAD_AT_CHECKPOINT" -- . 2>/dev/null || git reset --hard "$HEAD_AT_CHECKPOINT" 2>/dev/null
        echo "{\"status\":\"reverted\",\"to\":\"$HEAD_AT_CHECKPOINT\"}"
        ;;

    list)
        if [[ ! -f evolution/.state/checkpoints.jsonl ]]; then
            echo '{"checkpoints":[]}'
            exit 0
        fi
        echo '{"checkpoints":['
        tail -10 evolution/.state/checkpoints.jsonl | while IFS= read -r line; do
            echo "  $line,"
        done
        echo ']}'
        ;;

    diff)
        if [[ ! -f evolution/.state/checkpoints.jsonl ]]; then
            echo '{"error":"No checkpoints"}'
            exit 1
        fi
        LAST=$(tail -1 evolution/.state/checkpoints.jsonl)
        HEAD_AT=$(echo "$LAST" | python3 -c "import sys,json; print(json.load(sys.stdin)['head'])" 2>/dev/null || echo "HEAD~1")
        git diff "$HEAD_AT" --stat 2>/dev/null || echo "No diff available"
        ;;

    help|*)
        echo "Usage: ./engine/checkpoint.sh {create|revert|list|diff} [args]"
        ;;
esac
