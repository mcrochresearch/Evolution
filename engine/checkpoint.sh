#!/usr/bin/env bash
# ============================================================================
# EVOLUTION CHECKPOINT ENGINE — Git-based state snapshots and rollback
# ============================================================================
# Creates real git commits on detached refs (refs/evolution/checkpoint-N) so
# checkpoints are first-class objects in the repo, not ephemeral stashes.
#
# Atomic writes: checkpoint metadata is stored in a proper JSON file using
# write-to-temp-then-rename (matching engine/state.py's approach).
#
# Safe staging: only tracked files and evolution/ are staged — never secrets,
# build artifacts, or .tmp files.
#
# Usage:
#   ./engine/checkpoint.sh create [message]  Create a checkpoint
#   ./engine/checkpoint.sh revert [--confirm] Revert to last checkpoint
#   ./engine/checkpoint.sh list              List recent checkpoints
#   ./engine/checkpoint.sh diff              Show changes since checkpoint
# ============================================================================

set -euo pipefail

CMD="${1:-help}"
shift || true

STATE_DIR="evolution/.state"
CHECKPOINT_FILE="$STATE_DIR/checkpoints.json"
MAX_CHECKPOINTS=20

# ============================================================================
# Helpers
# ============================================================================

# Atomic JSON write: write to temp file, then rename.
# This prevents corruption on power failure or concurrent access.
atomic_write_json() {
    local target="$1"
    local content="$2"
    local dir
    dir=$(dirname "$target")
    mkdir -p "$dir"
    local tmp
    tmp=$(mktemp "${dir}/.checkpoint-XXXXXX.tmp")
    if printf '%s\n' "$content" > "$tmp" 2>/dev/null; then
        mv -f "$tmp" "$target"
    else
        rm -f "$tmp" 2>/dev/null || true
        echo '{"error":"Failed to write checkpoint metadata"}' >&2
        return 1
    fi
}

# Read the checkpoint list, or return an empty structure.
read_checkpoints() {
    if [[ -f "$CHECKPOINT_FILE" ]]; then
        cat "$CHECKPOINT_FILE"
    else
        echo '{"checkpoints":[]}'
    fi
}

# Get the next checkpoint number (monotonically increasing).
next_checkpoint_number() {
    local data
    data=$(read_checkpoints)
    python3 -c "
import json, sys
data = json.loads(sys.argv[1])
entries = data.get('checkpoints', [])
if entries:
    nums = [e.get('number', 0) for e in entries]
    print(max(nums) + 1)
else:
    print(1)
" "$data"
}

# Stage only safe files: tracked files (updated) + the evolution/ directory.
# Never uses 'git add -A' which would stage secrets, build artifacts, etc.
safe_stage() {
    # Update index for all already-tracked files (adds modifications + deletions)
    git add -u 2>/dev/null || true
    # Stage evolution state directory (new and modified files there)
    if [[ -d "evolution/" ]]; then
        git add -- evolution/ 2>/dev/null || true
    fi
}

# ============================================================================
# Commands
# ============================================================================

cmd_create() {
    local message="${1:-Cycle checkpoint}"

    # Stage safely
    safe_stage

    # Create a tree object from the current index (includes staged changes)
    local tree_hash
    tree_hash=$(git write-tree 2>/dev/null)
    if [[ -z "$tree_hash" ]]; then
        echo '{"error":"Failed to create tree object. Is this a git repository?"}'
        exit 1
    fi

    # Create a commit object pointing at this tree
    local head_hash
    head_hash=$(git rev-parse HEAD 2>/dev/null || echo "none")
    local commit_hash
    commit_hash=$(git commit-tree "$tree_hash" -p "$head_hash" -m "evolution checkpoint: $message" 2>/dev/null)
    if [[ -z "$commit_hash" ]]; then
        echo '{"error":"Failed to create checkpoint commit"}'
        exit 1
    fi

    # Assign a checkpoint number and store as a git ref
    local num
    num=$(next_checkpoint_number)
    local ref="refs/evolution/checkpoint-${num}"
    git update-ref "$ref" "$commit_hash" 2>/dev/null

    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # Build the updated checkpoint list atomically
    local data
    data=$(read_checkpoints)
    local new_data
    new_data=$(python3 -c "
import json, sys
data = json.loads(sys.argv[1])
entry = {
    'number': int(sys.argv[2]),
    'ref': sys.argv[3],
    'commit': sys.argv[4],
    'head': sys.argv[5],
    'message': sys.argv[6],
    'timestamp': sys.argv[7]
}
entries = data.get('checkpoints', [])
entries.append(entry)
# Keep only the last $MAX_CHECKPOINTS entries
entries = entries[-${MAX_CHECKPOINTS}:]
print(json.dumps({'checkpoints': entries}, indent=2))
" "$data" "$num" "$ref" "$commit_hash" "$head_hash" "$message" "$timestamp")

    atomic_write_json "$CHECKPOINT_FILE" "$new_data"

    echo "{\"status\":\"created\",\"number\":$num,\"ref\":\"$ref\",\"commit\":\"$commit_hash\",\"head\":\"$head_hash\"}"
}

cmd_revert() {
    local confirmed=false
    for arg in "$@"; do
        if [[ "$arg" == "--confirm" ]]; then
            confirmed=true
        fi
    done

    if [[ ! -f "$CHECKPOINT_FILE" ]]; then
        echo '{"error":"No checkpoints found. Create a checkpoint first."}'
        exit 1
    fi

    # Get the last checkpoint
    local data
    data=$(read_checkpoints)
    local commit_hash ref num
    commit_hash=$(python3 -c "
import json, sys
data = json.loads(sys.argv[1])
entries = data.get('checkpoints', [])
if not entries:
    print('')
else:
    print(entries[-1]['commit'])
" "$data")
    ref=$(python3 -c "
import json, sys
data = json.loads(sys.argv[1])
entries = data.get('checkpoints', [])
print(entries[-1]['ref'] if entries else '')
" "$data")
    num=$(python3 -c "
import json, sys
data = json.loads(sys.argv[1])
entries = data.get('checkpoints', [])
print(entries[-1]['number'] if entries else '')
" "$data")

    if [[ -z "$commit_hash" ]]; then
        echo '{"error":"Cannot determine checkpoint commit. Checkpoint metadata may be corrupted."}'
        exit 1
    fi

    # Verify the commit exists in the repo
    if ! git cat-file -e "$commit_hash" 2>/dev/null; then
        echo "{\"error\":\"Checkpoint commit $commit_hash no longer exists in the repository.\"}"
        exit 1
    fi

    # Safety warning
    if [[ "$confirmed" != "true" ]]; then
        echo "{\"warning\":\"This will revert the working tree to checkpoint $num ($commit_hash). Pass --confirm to proceed, or review with 'diff' first.\"}" >&2
        echo "{\"status\":\"dry_run\",\"would_revert_to\":{\"number\":$num,\"ref\":\"$ref\",\"commit\":\"$commit_hash\"}}"
        return 0
    fi

    # Step 1: Find files that exist now but did not exist at checkpoint time.
    # These are files created after the checkpoint — git checkout won't remove them.
    local new_files
    new_files=$(git diff --name-only --diff-filter=A "$commit_hash" HEAD 2>/dev/null || true)

    # Step 2: Checkout the checkpoint tree over the working directory.
    # This restores all files that existed at checkpoint time to their checkpoint state.
    if ! git checkout "$commit_hash" -- . 2>/dev/null; then
        echo "{\"error\":\"Failed to checkout checkpoint $commit_hash. Working tree may be in an inconsistent state.\"}"
        exit 1
    fi

    # Step 3: Remove files that were created after the checkpoint.
    if [[ -n "$new_files" ]]; then
        local removed=0
        while IFS= read -r file; do
            if [[ -f "$file" ]]; then
                rm -f "$file"
                removed=$((removed + 1))
            fi
        done <<< "$new_files"
        # Clean up empty directories left behind
        if [[ $removed -gt 0 ]]; then
            git clean -fd --quiet 2>/dev/null || true
        fi
    fi

    # Step 4: Reset the index to match what we just checked out
    safe_stage

    echo "{\"status\":\"reverted\",\"to\":{\"number\":$num,\"ref\":\"$ref\",\"commit\":\"$commit_hash\"},\"method\":\"checkout+clean\"}"
}

cmd_list() {
    if [[ ! -f "$CHECKPOINT_FILE" ]]; then
        echo '{"checkpoints":[]}'
        exit 0
    fi

    # Read the JSON file directly — it is already a proper JSON structure.
    # Show only the last 10 for display (file may store up to MAX_CHECKPOINTS).
    python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
entries = data.get('checkpoints', [])[-10:]
print(json.dumps({'checkpoints': entries}, indent=2))
" "$CHECKPOINT_FILE"
}

cmd_diff() {
    if [[ ! -f "$CHECKPOINT_FILE" ]]; then
        echo '{"error":"No checkpoints found"}'
        exit 1
    fi

    local data
    data=$(read_checkpoints)
    local commit_hash
    commit_hash=$(python3 -c "
import json, sys
data = json.loads(sys.argv[1])
entries = data.get('checkpoints', [])
if not entries:
    print('')
else:
    print(entries[-1]['commit'])
" "$data")

    if [[ -z "$commit_hash" ]]; then
        echo '{"error":"Cannot determine checkpoint commit"}'
        exit 1
    fi

    if ! git cat-file -e "$commit_hash" 2>/dev/null; then
        echo "{\"error\":\"Checkpoint commit $commit_hash no longer exists\"}"
        exit 1
    fi

    # Compare current working tree against the checkpoint commit
    git diff "$commit_hash" --stat 2>/dev/null || echo '{"error":"No diff available"}'
}

# ============================================================================
# Dispatch
# ============================================================================

case "$CMD" in
    create)
        cmd_create "$@"
        ;;
    revert)
        cmd_revert "$@"
        ;;
    list)
        cmd_list
        ;;
    diff)
        cmd_diff
        ;;
    help|*)
        echo "Usage: ./engine/checkpoint.sh {create|revert|list|diff} [args]"
        echo ""
        echo "Commands:"
        echo "  create [message]   Create a checkpoint (git commit on detached ref)"
        echo "  revert [--confirm] Revert working tree to last checkpoint"
        echo "  list               List recent checkpoints"
        echo "  diff               Show changes since last checkpoint"
        ;;
esac
