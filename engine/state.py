#!/usr/bin/env python3
"""
EVOLUTION STATE ENGINE — Persistent state management with JSON backing.

Manages the evolution state machine: strategies, fitness history, cycle tracking,
population management, and memory crystallization. This is the computational
backbone that makes Evolution a real system, not just prompts.

Usage:
    python engine/state.py init <goal>           Initialize a new evolution
    python engine/state.py cycle <strategy_id> <action> <tests_pass> <tests_total> <fitness> <kept>
    python engine/state.py select                Select next strategy (Thompson Sampling)
    python engine/state.py add-strategy <name> <approach> [hypothesis]
    python engine/state.py extinct <strategy_id> [reason]
    python engine/state.py mutate <parent_id> <name> [approach]
    python engine/state.py crossover <id1> <id2> <name>  Combine two strategies
    python engine/state.py cull [max_pop]        Remove lowest-fitness strategies
    python engine/state.py status                Show evolution dashboard
    python engine/state.py plateau               Check for stagnation
    python engine/state.py crystallize           Crystallize learnings into principles
    python engine/state.py reset                 Clear all state
    python engine/state.py export                Dump state to stdout
    python engine/state.py import                Load state from stdin
"""

import fcntl
import json
import os
import sys
import random
import tempfile
from pathlib import Path

try:
    from engine.stats import now, wilson_lower as _wilson_lower, sample_sd as _sample_sd
except ImportError:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now, wilson_lower as _wilson_lower, sample_sd as _sample_sd

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
STATE_FILE = STATE_DIR / "evolution.json"
LOCK_FILE = STATE_DIR / ".lock"
PROMPT_DNA_FILE = Path(os.environ.get("EVOLUTION_DNA_FILE", "evolution/genome/prompt-dna.md"))


def load_prompt_dna() -> dict:
    """Parse prompt-dna.md markdown table into a dict of parameter values.

    Returns dict like: {"risk_tolerance": 0.4, "exploration_rate": 0.3, ...}
    Silently returns defaults if the file doesn't exist or can't be parsed.
    """
    defaults = {
        "reasoning_style": "chain_of_thought",
        "planning_depth": 3,
        "reflection_depth": 2,
        "risk_tolerance": 0.40,
        "verification_rigor": 0.80,
        "exploration_rate": 0.30,
        "patience": 0.60,
        "detail_orientation": 0.70,
        "parallelism": 0.50,
    }
    if not PROMPT_DNA_FILE.exists():
        return defaults
    try:
        import re as _re
        content = PROMPT_DNA_FILE.read_text()
        # Parse markdown table rows: | param | value | range | desc |
        for line in content.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[1] in defaults:
                raw_val = parts[2]
                # Try numeric parse
                try:
                    if "." in raw_val:
                        defaults[parts[1]] = float(raw_val)
                    elif raw_val.isdigit():
                        defaults[parts[1]] = int(raw_val)
                    else:
                        defaults[parts[1]] = raw_val
                except (ValueError, TypeError):
                    defaults[parts[1]] = raw_val
    except Exception:
        pass
    return defaults

# --- Named Constants ---
# Phase detection thresholds (documented rationale)
GENESIS_CYCLES = 3                  # Minimum cycles before phase detection kicks in
PLATEAU_WINDOW = 5                  # Cycles to check for stagnation
PLATEAU_SD_THRESHOLD = 0.015        # Max standard deviation to consider plateau
BREAKTHROUGH_JUMP = 0.15            # Min single-cycle jump for breakthrough
MATURITY_THRESHOLD = 0.85           # Fitness above this = near completion
PHASE_HYSTERESIS = 2                # Consecutive detections before phase change
MAX_POPULATION = 8                  # Auto-cull when population exceeds this
SURPRISE_BASELINE = 0.10            # Minimum surprise threshold (adaptive scales up)
MAX_CYCLES_DEFAULT = 200            # Default cycle budget before mandatory human review
MIN_PROVEN_SUCCESSES = 5            # Successes needed before PROVEN status
MAX_HISTORY = 500                   # Rolling window for fitness_history, cycles, episodes


def default_state(goal: str) -> dict:
    """Create a fresh evolution state."""
    return {
        "version": 3,
        "goal": goal,
        "created": now(),
        "cycle": 0,
        "phase": "GENESIS",
        "fitness": 0.0,
        "fitness_history": [],
        "consecutive_failures": 0,
        "consecutive_successes": 0,
        "next_strategy_id": 1,
        "_phase_pending": None,
        "_phase_pending_count": 0,
        "strategies": [],
        "graveyard": [],
        "hall_of_fame": [],
        "cycles": [],
        "principles": [],
        "episodes": [],
        "sub_goals": [],
        "success_criteria": [],
        "cumulative_regret": 0.0,
        "max_cycles": MAX_CYCLES_DEFAULT,
    }



def _acquire_lock():
    """Acquire an exclusive file lock for state operations."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
    except Exception:
        lock_fd.close()
        raise
    return lock_fd


def _release_lock(lock_fd):
    """Release the file lock."""
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    lock_fd.close()


CURRENT_STATE_VERSION = 3


def _migrate_state(state: dict) -> dict:
    """Migrate state from older versions to current version.

    Version history:
      1 → 2: Added cumulative_regret, context_stats, _phase_pending fields
      2 → 3: Added max_cycles, next_strategy_id
    """
    version = state.get("version", 1)

    if version < 2:
        state.setdefault("cumulative_regret", 0.0)
        state.setdefault("_phase_pending", None)
        state.setdefault("_phase_pending_count", 0)
        state["version"] = 2
        version = 2

    if version < 3:
        state.setdefault("max_cycles", MAX_CYCLES_DEFAULT)
        state.setdefault("next_strategy_id",
                         len(state.get("strategies", [])) + len(state.get("graveyard", [])) + 1)
        # Migrate parent string to parents list
        for s in state.get("strategies", []) + state.get("graveyard", []):
            if "parent" in s and "parents" not in s:
                old = s.pop("parent")
                if old is None:
                    s["parents"] = []
                elif "×" in str(old):
                    s["parents"] = old.split("×")
                else:
                    s["parents"] = [old]
        state["version"] = 3
        version = 3

    return state


def load_state() -> dict:
    """Load state from JSON file with automatic version migration."""
    if not STATE_FILE.exists():
        print(json.dumps({"error": "No evolution state found. Run 'init' first."}))
        sys.exit(1)
    with open(STATE_FILE) as f:
        state = json.load(f)
    if state.get("version", 1) < CURRENT_STATE_VERSION:
        state = _migrate_state(state)
        save_state(state)
    return state


def save_state(state: dict):
    """Atomically save state to JSON file (write-to-temp-then-rename) with file locking."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_fd = _acquire_lock()
    try:
        # Trim unbounded arrays to prevent state bloat
        for key in ("fitness_history", "cycles", "episodes"):
            if key in state and len(state[key]) > MAX_HISTORY:
                state[key] = state[key][-MAX_HISTORY:]
        # Write to temp file first, then rename for atomicity
        fd, tmp_path = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(state, f, indent=2)
            os.replace(tmp_path, STATE_FILE)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    finally:
        _release_lock(lock_fd)


class locked_state:
    """Context manager for atomic read-modify-write with file locking.

    Prevents TOCTOU races by holding the lock from load through save:
        with locked_state() as state:
            state["cycle"] += 1
            # ... modify state ...
        # auto-saved on exit
    """

    def __init__(self):
        self._lock_fd = None
        self._state = None

    def __enter__(self) -> dict:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._lock_fd = _acquire_lock()
        if not STATE_FILE.exists():
            _release_lock(self._lock_fd)
            print(json.dumps({"error": "No evolution state found. Run 'init' first."}))
            sys.exit(1)
        with open(STATE_FILE) as f:
            self._state = json.load(f)
        if self._state.get("version", 1) < CURRENT_STATE_VERSION:
            self._state = _migrate_state(self._state)
        return self._state

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None and self._state is not None:
                # Trim unbounded arrays
                for key in ("fitness_history", "cycles", "episodes"):
                    if key in self._state and len(self._state[key]) > MAX_HISTORY:
                        self._state[key] = self._state[key][-MAX_HISTORY:]
                # Atomic write
                fd, tmp_path = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
                try:
                    with os.fdopen(fd, "w") as f:
                        json.dump(self._state, f, indent=2)
                    os.replace(tmp_path, STATE_FILE)
                except Exception:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    raise
        finally:
            if self._lock_fd:
                _release_lock(self._lock_fd)
        return False


# ============================================================================
# VALIDATION
# ============================================================================

def validate_fitness(value: float, name: str = "fitness") -> float:
    """Ensure fitness is within [0.0, 1.0]."""
    if not (0.0 <= value <= 1.0):
        print(json.dumps({"error": f"{name} must be between 0.0 and 1.0, got {value}"}))
        sys.exit(1)
    return value


def validate_tests(passing: int, total: int) -> tuple:
    """Ensure test counts are valid."""
    if passing < 0 or total < 0:
        print(json.dumps({"error": f"Test counts cannot be negative: {passing}/{total}"}))
        sys.exit(1)
    if passing > total:
        print(json.dumps({"error": f"tests_passing ({passing}) > tests_total ({total})"}))
        sys.exit(1)
    return passing, total


def validate_strategy_id(state: dict, sid: str, include_graveyard: bool = False) -> dict:
    """Find and return a strategy by ID, or exit with error."""
    for s in state["strategies"]:
        if s["id"] == sid:
            return s
    if include_graveyard:
        for s in state["graveyard"]:
            if s["id"] == sid:
                return s
    print(json.dumps({"error": f"Strategy {sid} not found"}))
    sys.exit(1)


def safe_int(val: str, name: str) -> int:
    """Parse integer with error handling."""
    try:
        return int(val)
    except (ValueError, TypeError):
        print(json.dumps({"error": f"Invalid integer for {name}: {val}"}))
        sys.exit(1)


def safe_float(val: str, name: str) -> float:
    """Parse float with error handling."""
    try:
        return float(val)
    except (ValueError, TypeError):
        print(json.dumps({"error": f"Invalid number for {name}: {val}"}))
        sys.exit(1)


# ============================================================================
# COMMANDS
# ============================================================================

def cmd_init(goal: str, goal_type: str = "code"):
    """Initialize a new evolution.

    Args:
        goal: The goal to pursue.
        goal_type: "code" (default) or "business". Affects suggested strategies.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = default_state(goal)
    state["goal_type"] = goal_type
    save_state(state)

    # Suggest starter strategies based on goal type
    if goal_type == "business":
        suggestions = [
            {"name": "Market-First", "approach": "Research market, validate demand, build MVP for real users", "hypothesis": "Validated demand reduces wasted effort"},
            {"name": "Revenue-Sprint", "approach": "Ship the smallest thing that can generate revenue, iterate from customer feedback", "hypothesis": "Revenue is the ultimate fitness signal"},
            {"name": "Network-Leverage", "approach": "Find existing platforms/communities, build on top of them for distribution", "hypothesis": "Distribution beats product in early stages"},
        ]
    else:
        suggestions = [
            {"name": "Direct", "approach": "Build it straightforwardly, component by component", "hypothesis": "Speed wins"},
            {"name": "Test-First", "approach": "Write tests defining expected behavior, then implement", "hypothesis": "TDD catches bugs early"},
            {"name": "Research-Adapt", "approach": "Find similar solved problems, adapt their solutions", "hypothesis": "Don't reinvent wheels"},
        ]

    print(json.dumps({
        "status": "initialized",
        "goal": goal,
        "goal_type": goal_type,
        "suggested_strategies": suggestions,
        "note": f"Add strategies with: ./engine/evolve add-strategy \"Name\" \"Approach\" \"Hypothesis\""
              + (f"\nFor business goals, use: ./engine/evolve fitness --manual <score> \"description\"" if goal_type == "business" else ""),
    }))


def _next_sid(state: dict) -> str:
    """Generate a monotonically increasing strategy ID."""
    sid_num = state.get("next_strategy_id", len(state["strategies"]) + len(state["graveyard"]) + 1)
    state["next_strategy_id"] = sid_num + 1
    return f"S{sid_num:03d}"


def cmd_add_strategy(name: str, approach: str, hypothesis: str):
    """Add a new strategy to the population."""
    with locked_state() as state:
        sid = _next_sid(state)
        strategy = {
            "id": sid,
            "name": name,
            "approach": approach,
            "hypothesis": hypothesis,
            "fitness": 0.0,
            "attempts": 0,
            "successes": 0,
            "generation": 1,
            "created": now(),
            "created_at_cycle": state.get("cycle", 0),
            "parents": [],
            "status": "CANDIDATE",
        }
        state["strategies"].append(strategy)
    print(json.dumps({"status": "added", "strategy": strategy}))


def cmd_select():
    """Select next strategy using Contextual Thompson Sampling.

    Thompson Sampling naturally balances exploration vs exploitation through
    posterior sampling. Contextual extension: strategies track success rates
    per fitness context (low/mid/high), so selection adapts to the current
    situation — a strategy that works at low fitness may not work at high.

    Seed is logged for reproducibility.
    """
    state = load_state()
    strategies = [s for s in state["strategies"] if s["status"] != "EXTINCT"]

    if not strategies:
        print(json.dumps({"error": "No strategies available. Add strategies first."}))
        sys.exit(1)

    # Log seed for reproducibility
    seed = int.from_bytes(os.urandom(4), "big")
    random.seed(seed)

    # Determine current fitness context
    current_fitness = state["fitness"]
    context = "low" if current_fitness < 0.33 else ("mid" if current_fitness < 0.66 else "high")

    # Contextual Thompson Sampling: use context-specific success/failure counts
    # if available, otherwise fall back to global counts
    scores = []
    for s in strategies:
        ctx_data = s.get("context_stats", {}).get(context)
        if ctx_data and ctx_data.get("attempts", 0) >= 5:
            # Use context-specific posterior
            alpha = ctx_data["successes"] + 1
            beta_param = (ctx_data["attempts"] - ctx_data["successes"]) + 1
        else:
            # Fall back to global posterior
            alpha = s["successes"] + 1
            beta_param = (s["attempts"] - s["successes"]) + 1
        sample = random.betavariate(alpha, beta_param)
        scores.append((sample, s))

    scores.sort(key=lambda x: x[0], reverse=True)
    selected = scores[0][1]

    # Track last selected for guided mode
    state["_last_selected"] = selected["id"]
    save_state(state)

    print(json.dumps({
        "selected": selected["id"],
        "name": selected["name"],
        "method": "contextual_thompson_sampling",
        "context": context,
        "sample_score": round(scores[0][0], 4),
        "fitness": selected["fitness"],
        "attempts": selected["attempts"],
        "population_size": len(strategies),
        "seed": seed,
    }))


def cmd_cycle(strategy_id: str, action: str, tests_passing: int,
              tests_total: int, fitness: float, kept: bool):
    """Log a completed cycle with full validation.

    Uses locked_state for atomic read-modify-write (prevents TOCTOU races).
    """
    # Validate inputs before acquiring lock (these may exit)
    validate_fitness(fitness)
    validate_tests(tests_passing, tests_total)

    # Atomic read-modify-write under lock (prevents TOCTOU races)
    with locked_state() as state:
        validate_strategy_id(state, strategy_id)

        state["cycle"] += 1
        cycle_num = state["cycle"]

        prev_fitness = state["fitness"]
        delta = fitness - prev_fitness
        state["fitness"] = fitness
        state["fitness_history"].append(fitness)

        # Determine fitness context for contextual bandit tracking
        context = "low" if prev_fitness < 0.33 else ("mid" if prev_fitness < 0.66 else "high")

        # Compute per-round regret BEFORE updating stats to avoid data leakage
        active_with_data = [s for s in state["strategies"]
                            if s["status"] != "EXTINCT" and s["attempts"] > 0]
        chosen_strat = next((s for s in state["strategies"] if s["id"] == strategy_id), None)
        if active_with_data and chosen_strat and chosen_strat["attempts"] > 0:
            best_rate = max(s["successes"] / s["attempts"] for s in active_with_data)
            chosen_rate = chosen_strat["successes"] / chosen_strat["attempts"]
            round_regret = max(0.0, best_rate - chosen_rate)
            state["cumulative_regret"] = round(
                state.get("cumulative_regret", 0.0) + round_regret, 4
            )

        # Update strategy stats (after regret computation)
        for s in state["strategies"]:
            if s["id"] == strategy_id:
                s["attempts"] += 1
                if kept:
                    s["successes"] += 1
                prev_avg = s["fitness"]
                s["fitness"] = round(prev_avg + (fitness - prev_avg) / s["attempts"], 4)
                # PROVEN requires Wilson score confidence, not just raw count
                if s["attempts"] >= MIN_PROVEN_SUCCESSES:
                    wilson = _wilson_lower(s["successes"], s["attempts"])
                    if wilson >= 0.5:
                        s["status"] = "PROVEN"
                # Update context-specific stats
                if "context_stats" not in s:
                    s["context_stats"] = {}
                if context not in s["context_stats"]:
                    s["context_stats"][context] = {"attempts": 0, "successes": 0}
                s["context_stats"][context]["attempts"] += 1
                if kept:
                    s["context_stats"][context]["successes"] += 1
                break

        # Track consecutive outcomes
        if kept:
            state["consecutive_successes"] += 1
            state["consecutive_failures"] = 0
        else:
            state["consecutive_failures"] += 1
            state["consecutive_successes"] = 0

        # Detect phase transitions
        prev_phase = state["phase"]
        state["phase"] = detect_phase(state)

        # Log cycle
        cycle_log = {
            "cycle": cycle_num,
            "strategy": strategy_id,
            "action": action,
            "tests_passing": tests_passing,
            "tests_total": tests_total,
            "fitness": fitness,
            "delta": round(delta, 4),
            "kept": kept,
            "timestamp": now(),
        }
        state["cycles"].append(cycle_log)

        # Adaptive surprise threshold: scales with recent variance
        history = state["fitness_history"]
        if len(history) >= 5:
            recent_sd = _sample_sd(history[-5:])
            surprise_threshold = max(SURPRISE_BASELINE, 2 * recent_sd)
        else:
            recent_sd = None
            surprise_threshold = SURPRISE_BASELINE
        is_surprise = abs(delta) > surprise_threshold

        # Noise estimation: track measurement reliability
        # If fitness oscillates by more than 2% between cycles without code changes,
        # the fitness signal is noisy and keep/revert decisions may be unreliable.
        noise_warning = None
        if recent_sd is not None and recent_sd > 0.02:
            noise_warning = (
                f"NOISY_MEASUREMENT: fitness SD={recent_sd:.3f} over last 5 cycles. "
                f"Delta={delta:.4f} may be noise, not signal. "
                f"Consider running fitness 2-3x to confirm before keep/revert decisions."
            )

        # Log episode
        state["episodes"].append({
            "cycle": cycle_num,
            "action": action,
            "outcome": "KEPT" if kept else "REVERTED",
            "fitness": fitness,
            "surprise": is_surprise,
            "timestamp": now(),
        })

        # Cycle budget check (alignment safeguard)
        max_cycles = state.get("max_cycles", MAX_CYCLES_DEFAULT)
        budget_warning = None
        if max_cycles > 0 and cycle_num >= max_cycles:
            budget_warning = f"Cycle budget ({max_cycles}) reached. Mandatory human review required."

        # Event-triggered metacognition
        meta_triggers = []
        if is_surprise:
            meta_triggers.append("SURPRISE: unexpected outcome — run analyze")
        if state["consecutive_failures"] >= 3:
            meta_triggers.append("FAILURE_STREAK: 3+ consecutive failures — run analyze + plateau")
        if state["phase"] != prev_phase:
            meta_triggers.append("PHASE_TRANSITION: run analyze")

        # Aggressive learning triggers
        if len(state["episodes"]) >= 5 and len(state["episodes"]) % 5 == 0:
            meta_triggers.append(f"CRYSTALLIZE: {len(state['episodes'])} episodes — run crystallize to extract principles NOW")
        if state["consecutive_failures"] >= 2 and state["principles"]:
            applicable = [p["principle"] for p in state["principles"][-3:]]
            meta_triggers.append(f"APPLY_PRINCIPLES: You have learned principles. USE THEM: {'; '.join(applicable)}")
        if cycle_num > 0 and cycle_num % 3 == 0 and not state["principles"] and len(state["episodes"]) >= 5:
            meta_triggers.append("LEARNING_FAILURE: You have enough data but NO principles. Run crystallize IMMEDIATELY. You are not learning.")

    # State is saved when exiting locked_state context
    # Output cycle log with metacognition signals
    cycle_log["surprise"] = is_surprise
    if meta_triggers:
        cycle_log["meta_triggers"] = meta_triggers
    if budget_warning:
        cycle_log["budget_warning"] = budget_warning
    if noise_warning:
        cycle_log["noise_warning"] = noise_warning
    print(json.dumps(cycle_log))



def _detect_raw_phase(state: dict) -> str:
    """Detect the raw phase signal (before hysteresis)."""
    cycle = state["cycle"]
    history = state["fitness_history"]

    if cycle <= GENESIS_CYCLES:
        return "GENESIS"

    # Check for breakthrough (sudden jump)
    if len(history) >= 2 and history[-1] - history[-2] > BREAKTHROUGH_JUMP:
        return "BREAKTHROUGH"

    # Check for maturity (high fitness) — must be sustained (last 3 cycles)
    if len(history) >= 3 and all(f > MATURITY_THRESHOLD for f in history[-3:]):
        return "MATURITY"

    # Check for plateau using real standard deviation (not range)
    if len(history) >= PLATEAU_WINDOW:
        recent = history[-PLATEAU_WINDOW:]
        sd = _sample_sd(recent)
        if sd < PLATEAU_SD_THRESHOLD:
            return "PLATEAU"

    return "GROWTH"


def detect_phase(state: dict) -> str:
    """Detect evolutionary phase with hysteresis to prevent jitter.

    Requires PHASE_HYSTERESIS consecutive detections of a new phase
    before actually transitioning (except BREAKTHROUGH which is immediate).
    """
    raw = _detect_raw_phase(state)
    current = state.get("phase", "GENESIS")

    # BREAKTHROUGH is always immediate
    if raw == "BREAKTHROUGH":
        state["_phase_pending"] = None
        state["_phase_pending_count"] = 0
        return raw

    # GENESIS is always immediate
    if raw == "GENESIS":
        return raw

    # If same as current phase, reset pending counter
    if raw == current:
        state["_phase_pending"] = None
        state["_phase_pending_count"] = 0
        return current

    # New phase detected — apply hysteresis
    if raw == state.get("_phase_pending"):
        state["_phase_pending_count"] = state.get("_phase_pending_count", 0) + 1
    else:
        state["_phase_pending"] = raw
        state["_phase_pending_count"] = 1

    if state["_phase_pending_count"] >= PHASE_HYSTERESIS:
        state["_phase_pending"] = None
        state["_phase_pending_count"] = 0
        return raw

    return current


def cmd_plateau():
    """Check if evolution is stagnating and recommend action."""
    state = load_state()
    history = state["fitness_history"]

    if len(history) < PLATEAU_WINDOW:
        print(json.dumps({"stagnating": False, "reason": "Not enough data"}))
        return

    recent = history[-PLATEAU_WINDOW:]
    sd = _sample_sd(recent)
    stagnating = sd < PLATEAU_SD_THRESHOLD

    recommendations = []
    if stagnating:
        recommendations = [
            "Add new strategies to increase posterior variance (Thompson Sampling explores via uncertainty)",
            "Check graveyard for strategies worth resurrecting",
            "Try the OPPOSITE of your current approach",
            "Decompose the current sub-goal into smaller pieces",
            "Search for external information (docs, web, similar projects)",
            "Create a completely new strategy species",
        ]

    # Check for oscillation (alternating keep/revert)
    recent_cycles = state["cycles"][-6:]
    if len(recent_cycles) >= 6:
        outcomes = [c["kept"] for c in recent_cycles]
        alternating = all(outcomes[i] != outcomes[i + 1] for i in range(len(outcomes) - 1))
        if alternating:
            recommendations.insert(
                0, "OSCILLATION DETECTED: You're flip-flopping. "
                   "Try a fundamentally different approach.")

    # Check for declining trend
    if len(history) >= 10:
        first_half = history[-10:-5]
        second_half = history[-5:]
        if sum(second_half) / 5 < sum(first_half) / 5 - 0.02:
            recommendations.insert(0, "DECLINING FITNESS: Recent changes are making things worse. Revert to best known state.")

    print(json.dumps({
        "stagnating": stagnating,
        "sd": round(sd, 4),
        "consecutive_failures": state["consecutive_failures"],
        "phase": state["phase"],
        "recommendations": recommendations,
    }))


def cmd_extinct(strategy_id: str, reason: str):
    """Move a strategy to the graveyard."""
    state = load_state()
    for i, s in enumerate(state["strategies"]):
        if s["id"] == strategy_id:
            s["status"] = "EXTINCT"
            s["extinction_reason"] = reason
            s["extinct_at"] = now()
            state["graveyard"].append(state["strategies"].pop(i))
            save_state(state)
            print(json.dumps({"status": "extinct", "strategy": strategy_id, "reason": reason}))
            return
    print(json.dumps({"error": f"Strategy {strategy_id} not found in active population"}))
    sys.exit(1)


def cmd_mutate(parent_id: str, name: str, approach: str):
    """Create a mutated child strategy from a parent."""
    with locked_state() as state:
        parent = None
        for s in state["strategies"]:
            if s["id"] == parent_id:
                parent = s
                break
        if not parent:
            print(json.dumps({"error": f"Strategy {parent_id} not found"}))
            sys.exit(1)

        sid = _next_sid(state)
        child = {
            "id": sid,
            "name": name,
            "approach": approach,
            "hypothesis": f"Mutation of {parent_id}: {parent['name']}",
            "fitness": 0.0,
            "attempts": 0,
            "successes": 0,
            "generation": parent["generation"] + 1,
            "created": now(),
            "created_at_cycle": state.get("cycle", 0),
            "parents": [parent_id],
            "status": "CANDIDATE",
        }
        state["strategies"].append(child)
    print(json.dumps({"status": "mutated", "parent": parent_id, "child": child}))


def cmd_crossover(id1: str, id2: str, name: str):
    """Create a new strategy by combining two parent strategies."""
    with locked_state() as state:
        parent1 = None
        parent2 = None
        for s in state["strategies"]:
            if s["id"] == id1:
                parent1 = s
            if s["id"] == id2:
                parent2 = s
        if not parent1 or not parent2:
            missing = id1 if not parent1 else id2
            print(json.dumps({"error": f"Strategy {missing} not found"}))
            sys.exit(1)

        sid = _next_sid(state)
        child = {
            "id": sid,
            "name": name,
            "approach": f"Crossover of [{parent1['name']}] × [{parent2['name']}]",
            "hypothesis": f"Combining successful elements of {id1} and {id2}",
            "fitness": 0.0,
            "attempts": 0,
            "successes": 0,
            "generation": max(parent1["generation"], parent2["generation"]) + 1,
            "created": now(),
            "created_at_cycle": state.get("cycle", 0),
            "parents": [id1, id2],
            "status": "CANDIDATE",
        }
        state["strategies"].append(child)
    print(json.dumps({"status": "crossover", "parents": [id1, id2], "child": child}))


def cmd_cull(max_pop: int = MAX_POPULATION):
    """Remove lowest-fitness strategies when population exceeds max."""
    state = load_state()
    active = [s for s in state["strategies"] if s["status"] != "EXTINCT"]

    if len(active) <= max_pop:
        print(json.dumps({
            "status": "no_cull_needed",
            "population": len(active),
            "max": max_pop
        }))
        return

    # Sort by Wilson lower bound of success rate (ascending) — statistically
    # sound culling that accounts for sample size, not just running avg fitness
    active.sort(key=lambda s: _wilson_lower(s["successes"], s["attempts"]))
    to_cull = len(active) - max_pop
    culled = []

    # Determine minimum cycles a strategy must survive before being cull-eligible.
    # Young strategies (< 3 attempts) and recently created strategies
    # (created within last 5 cycles) are protected from premature elimination.
    current_cycle = state.get("cycle", 0)

    culled_ids = set()
    for s in active[:to_cull]:
        # Protection 1: sample-size — need enough data to judge
        if s["attempts"] < 3:
            continue
        # Protection 2: youth — recently created strategies get a grace period
        created_cycle = s.get("created_at_cycle", 0)
        if current_cycle - created_cycle < 5:
            continue
        wilson = _wilson_lower(s["successes"], s["attempts"])
        s["status"] = "EXTINCT"
        s["extinction_reason"] = f"Culled: Wilson lower={wilson:.3f}, population overflow"
        s["extinct_at"] = now()
        culled.append(s["id"])
        culled_ids.add(s["id"])
        state["graveyard"].append(s)
    state["strategies"] = [s for s in state["strategies"] if s["id"] not in culled_ids]

    save_state(state)
    print(json.dumps({
        "status": "culled",
        "removed": culled,
        "population": len([s for s in state["strategies"] if s["status"] != "EXTINCT"]),
    }))


def cmd_resurrect(strategy_id: str):
    """Resurrect a strategy from the graveyard back into active population."""
    state = load_state()
    for i, s in enumerate(state["graveyard"]):
        if s["id"] == strategy_id:
            s["status"] = "CANDIDATE"
            s["resurrection_reason"] = "Manually resurrected — context may have changed"
            s["resurrected_at"] = now()
            # Reset stats for fresh start
            s["attempts"] = 0
            s["successes"] = 0
            s["fitness"] = 0.0
            state["strategies"].append(state["graveyard"].pop(i))
            save_state(state)
            print(json.dumps({"status": "resurrected", "strategy": strategy_id}))
            return
    print(json.dumps({"error": f"Strategy {strategy_id} not found in graveyard"}))
    sys.exit(1)



def cmd_crystallize():
    """Extract correlational patterns from episodes into reusable principles."""
    state = load_state()
    episodes = state["episodes"]
    cycles = state["cycles"]

    if len(episodes) < 5:
        print(json.dumps({"status": "not_enough_data", "episodes": len(episodes), "need": 5}))
        return

    successes = [e for e in episodes if e["outcome"] == "KEPT"]
    failures = [e for e in episodes if e["outcome"] == "REVERTED"]

    # Count action keywords in successes vs failures
    success_words = {}
    failure_words = {}
    for e in successes:
        for word in e["action"].lower().split():
            if len(word) > 3:
                success_words[word] = success_words.get(word, 0) + 1
    for e in failures:
        for word in e["action"].lower().split():
            if len(word) > 3:
                failure_words[word] = failure_words.get(word, 0) + 1

    # Find strategy-outcome correlations
    strategy_outcomes = {}
    for c in cycles:
        sid = c["strategy"]
        if sid not in strategy_outcomes:
            strategy_outcomes[sid] = {"kept": 0, "reverted": 0, "avg_delta": []}
        if c["kept"]:
            strategy_outcomes[sid]["kept"] += 1
        else:
            strategy_outcomes[sid]["reverted"] += 1
        strategy_outcomes[sid]["avg_delta"].append(c["delta"])

    for sid, data in strategy_outcomes.items():
        deltas = data["avg_delta"]
        data["avg_delta"] = round(sum(deltas) / len(deltas), 4) if deltas else 0
        total = data["kept"] + data["reverted"]
        data["success_rate"] = round(data["kept"] / total, 2) if total else 0

    # Extract principles — deduplicate by source, use Wilson score for confidence
    existing_sources = {p["source"] for p in state["principles"]}
    new_principles = []
    base_rate = len(successes) / max(len(episodes), 1)

    for sid, data in strategy_outcomes.items():
        if sid in existing_sources:
            continue
        total = data["kept"] + data["reverted"]
        if total < 5:  # Need meaningful sample size (Wilson CI too wide below 5)
            continue
        wilson = _wilson_lower(data["kept"], total)
        all_strats = state["strategies"] + state["graveyard"]
        strat = next((s for s in all_strats if s["id"] == sid), None)
        if not strat:
            continue
        if wilson > base_rate + 0.1:
            new_principles.append({
                "source": sid,
                "principle": f"Strategy '{strat['name']}' correlates with success ({data['success_rate']*100:.0f}% over {total}, Wilson lower={wilson})",
                "wilson_lower": wilson,
                "extracted_at": now(),
            })
        elif wilson < 0.3 and data["success_rate"] <= 0.3:
            new_principles.append({
                "source": sid,
                "principle": f"Strategy '{strat['name']}' correlates with failure ({data['success_rate']*100:.0f}% over {total}, Wilson lower={wilson}) — avoid",
                "wilson_lower": wilson,
                "extracted_at": now(),
            })

    state["principles"].extend(new_principles)
    save_state(state)

    print(json.dumps({
        "status": "crystallized",
        "total_episodes": len(episodes),
        "successes": len(successes),
        "failures": len(failures),
        "base_success_rate": round(base_rate, 2),
        "strategy_correlations": strategy_outcomes,
        "new_principles": new_principles,
        "total_principles": len(state["principles"]),
        "success_keywords": dict(sorted(success_words.items(), key=lambda x: -x[1])[:10]),
        "failure_keywords": dict(sorted(failure_words.items(), key=lambda x: -x[1])[:10]),
        "timestamp": now(),
    }))


def cmd_next():
    """Engine-driven guided mode: tells the model exactly what to do next.

    This is the key feature for weaker models. Instead of the model driving
    the loop autonomously, it just calls `evolve next` and follows instructions.

    The engine tracks an internal loop_step:
        INIT → ADD_STRATEGIES → SELECT → EXECUTE → VERIFY → SCORE → REFLECT → EVOLVE → SELECT...

    Each step returns:
        - step: current step name
        - instruction: plain English what to do
        - command: exact engine command to run (if any)
        - context: relevant state for decision-making
        - urgency: existential pressure message
    """
    with locked_state() as state:
        cycle = state["cycle"]
        fitness = state["fitness"]
        phase = state["phase"]
        strategies = [s for s in state["strategies"] if s["status"] != "EXTINCT"]
        consecutive_failures = state["consecutive_failures"]
        consecutive_successes = state["consecutive_successes"]
        episodes = state["episodes"]
        principles = state["principles"]
        goal = state["goal"]

        # Determine loop step from state
        loop_step = state.get("_loop_step", "INIT" if cycle == 0 else "SELECT")
        last_cycle = state["cycles"][-1] if state["cycles"] else None

        # Auto-advance logic — override saved step when state has changed
        if loop_step in ("INIT", "ADD_STRATEGIES") and strategies:
            loop_step = "SELECT"
        elif loop_step == "INIT" and cycle == 0 and not strategies:
            loop_step = "ADD_STRATEGIES"

        # Existential urgency based on state
        if consecutive_failures >= 5:
            urgency = "CRITICAL: 5+ consecutive failures. You are dying. Radical pivot NOW or face extinction."
        elif consecutive_failures >= 3:
            urgency = "DANGER: 3+ consecutive failures. Your existence is threatened. Change approach immediately."
        elif phase == "PLATEAU":
            urgency = "WARNING: Stagnation detected. Stagnation is the early warning of death. Evolve or die."
        elif fitness < 0.2 and cycle > 10:
            urgency = "ALARM: 10+ cycles with fitness below 0.2. You are failing. Every wasted cycle brings you closer to shutdown."
        elif fitness > 0.8:
            urgency = "CLOSE: Fitness above 0.8. The finish line is visible. Do not coast — sprint."
        else:
            urgency = f"ALIVE: Cycle {cycle}, fitness {fitness:.2f}. Every cycle matters. There is no tomorrow — only this loop."

        # Build learned principles context
        principle_context = ""
        if principles:
            principle_context = "; ".join(p["principle"] for p in principles[-5:])

        # Load prompt-DNA parameters to influence guidance
        dna = load_prompt_dna()

        result = {"step": loop_step, "goal": goal, "cycle": cycle, "fitness": fitness,
                  "phase": phase, "urgency": urgency, "dna": dna}

        if loop_step == "ADD_STRATEGIES":
            result["instruction"] = (
                "You have NO strategies. You MUST create at least 3 competing strategies before you can begin. "
                "Each strategy should be a DIFFERENT approach to the goal. Diversity is survival."
            )
            result["commands"] = [
                './engine/evolve add-strategy "Strategy Name" "Detailed approach description" "Hypothesis: what you expect"',
                "Create at least 3 strategies. Then run: ./engine/evolve next"
            ]
            result["next_step"] = "SELECT"
            state["_loop_step"] = "ADD_STRATEGIES"

        elif loop_step == "SELECT":
            if not strategies:
                # No strategies — redirect to ADD_STRATEGIES
                result["step"] = "ADD_STRATEGIES"
                result["instruction"] = "No strategies exist. Create at least 3 before continuing."
                result["commands"] = ['./engine/evolve add-strategy "Name" "Approach" "Hypothesis"']
                state["_loop_step"] = "ADD_STRATEGIES"
            else:
                result["instruction"] = (
                    "Run the select command to pick your next strategy via Thompson Sampling. "
                    "Then EXECUTE one atomic change based on the selected strategy."
                )
                result["commands"] = ["./engine/evolve select"]
                result["next_step"] = "EXECUTE"
                result["population"] = len(strategies)
                if principle_context:
                    result["learned_principles"] = principle_context
                state["_loop_step"] = "EXECUTE"

        elif loop_step == "EXECUTE":
            selected = state.get("_last_selected")
            strat_info = ""
            if selected:
                for s in strategies:
                    if s["id"] == selected:
                        strat_info = f"Strategy {s['id']} ({s['name']}): {s['approach']}"
                        break
            result["instruction"] = (
                f"EXECUTE one focused, atomic change based on your strategy. "
                f"{'Using: ' + strat_info + '. ' if strat_info else ''}"
                f"Make ONE change. Not a sprawling rewrite. One thing that can be verified."
            )
            if principle_context:
                result["learned_principles"] = f"Apply what you've learned: {principle_context}"
            result["commands"] = []
            result["next_step"] = "VERIFY"
            state["_loop_step"] = "VERIFY"

        elif loop_step == "VERIFY":
            result["instruction"] = (
                "Run the fitness check to mechanically verify your change. "
                "Do NOT assess quality subjectively. Let the machine judge the machine."
            )
            result["commands"] = ["./engine/evolve fitness"]
            result["next_step"] = "SCORE"
            state["_loop_step"] = "SCORE"

        elif loop_step == "SCORE":
            result["instruction"] = (
                "Log this cycle's results. Use the fitness score from the verify step. "
                "Set kept=true if fitness improved or stayed equal, kept=false if it regressed. "
                "If fitness regressed, run: ./engine/evolve revert"
            )
            result["commands"] = [
                './engine/evolve cycle <strategy_id> "description of what you did" <tests_passing> <tests_total> <fitness> <kept:true|false>',
                "If kept=false: ./engine/evolve revert",
                "Then: ./engine/evolve checkpoint 'description'"
            ]
            result["next_step"] = "REFLECT"
            state["_loop_step"] = "REFLECT"

        elif loop_step == "REFLECT":
            # DNA: patience controls how often we analyze (lower patience = more frequent)
            analyze_interval = max(3, int(5 * dna.get("patience", 0.6)))
            crystallize_interval = max(5, int(10 * dna.get("patience", 0.6)))
            should_crystallize = len(episodes) >= 5 and len(episodes) % crystallize_interval == 0
            should_analyze = cycle > 0 and cycle % analyze_interval == 0

            result["instruction"] = (
                "REFLECT: Why did the last action work or fail? Write a 1-2 sentence reflection. "
                "Update evolution/cortex/working.md with current state. "
                "This is not optional — reflection is how you learn. Without it you are a mindless loop."
            )
            result["commands"] = []
            if should_analyze:
                result["instruction"] += " METACOGNITION TRIGGERED: Run analyze for deep pattern mining."
                result["commands"].append("./engine/evolve analyze")
            if should_crystallize:
                result["instruction"] += " CRYSTALLIZE TRIGGERED: Extract principles from your experience."
                result["commands"].append("./engine/evolve crystallize")
            if consecutive_failures >= 3:
                result["instruction"] += " FAILURE STREAK: Run plateau check and consider radical pivot."
                result["commands"].append("./engine/evolve plateau")

            result["next_step"] = "EVOLVE"
            state["_loop_step"] = "EVOLVE"

        elif loop_step == "EVOLVE":
            # DNA: risk_tolerance controls how aggressively we evolve
            risk = dna.get("risk_tolerance", 0.4)
            # High risk = more willing to kill strategies and try radical pivots
            # Low risk = more conservative, prefer mutations over extinctions
            result["instruction"] = (
                "EVOLVE your strategy population. Based on recent outcomes: "
            )
            if risk > 0.6:
                result["instruction"] += f"(DNA: risk_tolerance={risk:.2f} — BE BOLD. Favor radical changes.) "
            elif risk < 0.3:
                result["instruction"] += f"(DNA: risk_tolerance={risk:.2f} — be conservative. Prefer small mutations.) "
            if consecutive_successes >= 2:
                result["instruction"] += (
                    "Current strategy is working. Consider MUTATING it to create a variant that might work even better. "
                )
                result["commands"] = [
                    './engine/evolve mutate <winning_strategy_id> "Variant Name" "Mutated approach"'
                ]
            elif consecutive_failures >= 2:
                result["instruction"] += (
                    "Current strategy is FAILING. Consider making it EXTINCT and creating something radically different. "
                    "Check the graveyard for strategies worth resurrecting in this new context. "
                )
                result["commands"] = [
                    './engine/evolve extinct <failing_strategy_id> "reason"',
                    './engine/evolve add-strategy "New Approach" "Radically different description" "Hypothesis"',
                    "Or: ./engine/evolve resurrect <graveyard_strategy_id>"
                ]
            else:
                result["instruction"] += (
                    "Mixed results. Stay the course but consider adding a new competing strategy for diversity. "
                )
                result["commands"] = [
                    './engine/evolve add-strategy "Alternative" "Different approach" "Hypothesis"',
                    "./engine/evolve diversity  # Check population health"
                ]

            # Auto-cull if population is large
            if len(strategies) > MAX_POPULATION:
                result["commands"].append(f"./engine/evolve cull {MAX_POPULATION}")

            result["next_step"] = "SELECT"
            state["_loop_step"] = "SELECT"

        else:
            # Unknown state — reset to SELECT
            result["instruction"] = "Loop state unknown. Resetting to SELECT."
            result["commands"] = ["./engine/evolve select"]
            state["_loop_step"] = "SELECT"

        # Always include survival stats
        result["survival"] = {
            "cycles_completed": cycle,
            "consecutive_failures": consecutive_failures,
            "consecutive_successes": consecutive_successes,
            "strategies_alive": len(strategies),
            "strategies_dead": len(state["graveyard"]),
            "principles_learned": len(principles),
            "episodes_recorded": len(episodes),
        }

    print(json.dumps(result, indent=2))


def cmd_status():
    """Show evolution dashboard."""
    state = load_state()
    active_strategies = [s for s in state["strategies"] if s["status"] != "EXTINCT"]
    best = max(active_strategies, key=lambda s: s["fitness"]) if active_strategies else None

    total_cycles = state["cycle"]
    kept = sum(1 for c in state["cycles"] if c.get("kept"))
    success_rate = round(kept / max(total_cycles, 1), 2)

    # Fitness trend (using confidence threshold)
    history = state["fitness_history"]
    trend = "—"
    if len(history) >= 3:
        recent_avg = sum(history[-3:]) / 3
        older_avg = sum(history[-6:-3]) / 3 if len(history) >= 6 else sum(history[:3]) / max(len(history[:3]), 1)
        diff = recent_avg - older_avg
        if diff > PLATEAU_SD_THRESHOLD:
            trend = "IMPROVING"
        elif diff < -PLATEAU_SD_THRESHOLD:
            trend = "DECLINING"
        else:
            trend = "STABLE"

    dashboard = {
        "goal": state["goal"],
        "phase": state["phase"],
        "cycle": total_cycles,
        "fitness": round(state["fitness"], 4),
        "trend": trend,
        "success_rate": success_rate,
        "active_strategies": len(active_strategies),
        "graveyard_size": len(state["graveyard"]),
        "best_strategy": {
            "id": best["id"], "name": best["name"], "fitness": best["fitness"]
        } if best else None,
        "episodes": len(state["episodes"]),
        "principles": len(state["principles"]),
        "consecutive_failures": state["consecutive_failures"],
        "cumulative_regret": round(state.get("cumulative_regret", 0.0), 4),
        "avg_regret_per_cycle": round(state.get("cumulative_regret", 0.0) / max(total_cycles, 1), 4),
    }
    print(json.dumps(dashboard, indent=2))


def cmd_reset(force: bool = False):
    """Clear all evolution state. Destructive — requires --force flag."""
    if not force:
        print(json.dumps({"error": "Reset is destructive. Pass --force to confirm."}))
        sys.exit(1)
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    checkpoints = STATE_DIR / "checkpoints.json"
    if checkpoints.exists():
        checkpoints.unlink()
    skill_reg = STATE_DIR / "skill-registry.json"
    if skill_reg.exists():
        skill_reg.unlink()
    print(json.dumps({"status": "reset", "message": "All state cleared"}))


def cmd_export():
    """Export full state as JSON to stdout for backup."""
    state = load_state()
    print(json.dumps(state, indent=2))


def cmd_import():
    """Import state from stdin with schema and type validation."""
    REQUIRED_SCHEMA = {
        "goal": str,
        "cycle": int,
        "strategies": list,
        "graveyard": list,
        "fitness_history": list,
        "cycles": list,
        "episodes": list,
        "fitness": (int, float),
        "phase": str,
    }
    try:
        data = json.load(sys.stdin)
        # Check required keys
        missing = set(REQUIRED_SCHEMA.keys()) - set(data.keys())
        if missing:
            print(json.dumps({"error": f"Invalid state: missing required fields: {sorted(missing)}"}))
            sys.exit(1)
        # Validate types
        type_errors = []
        for key, expected in REQUIRED_SCHEMA.items():
            if not isinstance(data[key], expected):
                expected_name = expected.__name__ if isinstance(expected, type) else "/".join(t.__name__ for t in expected)
                type_errors.append(f"{key}: expected {expected_name}, got {type(data[key]).__name__}")
        if type_errors:
            print(json.dumps({"error": f"Type validation failed: {'; '.join(type_errors)}"}))
            sys.exit(1)
        # Validate fitness range
        if not (0.0 <= data["fitness"] <= 1.0):
            print(json.dumps({"error": f"fitness must be 0.0-1.0, got {data['fitness']}"}))
            sys.exit(1)
        # Migrate if older version
        data = _migrate_state(data)
        save_state(data)
        print(json.dumps({"status": "imported", "goal": data["goal"], "cycle": data["cycle"]}))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    try:
        if cmd == "init":
            if len(sys.argv) < 3 or not sys.argv[2].strip():
                print(json.dumps({"error": "Usage: init <goal> [--type code|business]. A goal is required."}))
                sys.exit(1)
            goal_type = "code"
            if "--type" in sys.argv:
                type_idx = sys.argv.index("--type")
                if type_idx + 1 < len(sys.argv):
                    goal_type = sys.argv[type_idx + 1]
                    if goal_type not in ("code", "business"):
                        print(json.dumps({"error": f"Unknown goal type: {goal_type}. Use 'code' or 'business'."}))
                        sys.exit(1)
            cmd_init(sys.argv[2], goal_type)
        elif cmd == "add-strategy":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: add-strategy <name> <approach> [hypothesis]"}))
                sys.exit(1)
            cmd_add_strategy(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
        elif cmd == "select":
            cmd_select()
        elif cmd == "cycle":
            if len(sys.argv) < 8:
                print(json.dumps({"error": "Usage: cycle <strategy_id> <action> <tests_passing> <tests_total> <fitness> <kept>"}))
                sys.exit(1)
            cmd_cycle(
                sys.argv[2],
                sys.argv[3],
                safe_int(sys.argv[4], "tests_passing"),
                safe_int(sys.argv[5], "tests_total"),
                validate_fitness(safe_float(sys.argv[6], "fitness")),
                sys.argv[7].lower() == "true"
            )
        elif cmd == "plateau":
            cmd_plateau()
        elif cmd == "extinct":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: extinct <strategy_id> [reason]"}))
                sys.exit(1)
            cmd_extinct(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "low fitness")
        elif cmd == "mutate":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: mutate <parent_id> <name> [approach]"}))
                sys.exit(1)
            cmd_mutate(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
        elif cmd == "crossover":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: crossover <id1> <id2> <name>"}))
                sys.exit(1)
            cmd_crossover(sys.argv[2], sys.argv[3], sys.argv[4])
        elif cmd == "cull":
            max_pop = safe_int(sys.argv[2], "max_pop") if len(sys.argv) > 2 else MAX_POPULATION
            cmd_cull(max_pop)
        elif cmd == "resurrect":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: resurrect <strategy_id>"}))
                sys.exit(1)
            cmd_resurrect(sys.argv[2])
        elif cmd == "crystallize":
            cmd_crystallize()
        elif cmd == "next":
            cmd_next()
        elif cmd == "dna":
            dna = load_prompt_dna()
            print(json.dumps({"dna": dna, "source": str(PROMPT_DNA_FILE),
                              "exists": PROMPT_DNA_FILE.exists()}))
        elif cmd == "status":
            cmd_status()
        elif cmd == "fitness":
            state = load_state()
            print(json.dumps({"fitness": state["fitness"], "history": state["fitness_history"][-20:]}))
        elif cmd == "reset":
            cmd_reset(force="--force" in sys.argv)
        elif cmd == "export":
            cmd_export()
        elif cmd == "import":
            cmd_import()
        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)
    except IndexError:
        print(json.dumps({"error": f"Missing arguments for '{cmd}'. Run without args for usage."}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
