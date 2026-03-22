#!/usr/bin/env python3
"""
Comprehensive tests for the Evolution engine.

Tests cover:
- State initialization, loading, saving (with atomicity)
- Strategy management (add, select, extinct, mutate, crossover, cull, resurrect)
- Cycle logging with validation
- Contextual Thompson Sampling
- Phase detection with hysteresis
- Crystallization with Wilson scores
- Statistical helpers (_sample_sd, _wilson_lower)
- SkillForge (extract, use, promote, dedup)
- Analyze (effect size, correlations)
- Input validation and error handling
"""

import json
import math
import os
import subprocess
import sys
import tempfile

import pytest

# --- Paths ---
ENGINE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
STATE_PY = os.path.join(ENGINE_DIR, "state.py")
ANALYZE_PY = os.path.join(ENGINE_DIR, "analyze.py")
SKILLFORGE_PY = os.path.join(ENGINE_DIR, "skillforge.py")


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Run every test with an isolated state directory."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("EVOLUTION_STATE_DIR", str(state_dir))
    # Also change working directory so skillforge writes to tmp
    monkeypatch.chdir(tmp_path)
    # Create skills dir for skillforge
    (tmp_path / "evolution" / "skills").mkdir(parents=True, exist_ok=True)
    (tmp_path / "evolution" / ".state").mkdir(parents=True, exist_ok=True)
    yield tmp_path


def run_cmd(script, *args, stdin_data=None):
    """Run a Python engine command and return parsed JSON output."""
    result = subprocess.run(
        [sys.executable, script] + list(args),
        capture_output=True, text=True,
        input=stdin_data,
        env={**os.environ},
    )
    # Try to parse JSON from stdout
    output = result.stdout.strip()
    if output:
        try:
            return json.loads(output), result.returncode
        except json.JSONDecodeError:
            return {"raw": output}, result.returncode
    return {"raw": result.stderr.strip()}, result.returncode


# ============================================================================
# STATE ENGINE TESTS
# ============================================================================

class TestInit:
    def test_init_creates_state(self, isolated_state):
        out, rc = run_cmd(STATE_PY, "init", "Build a REST API")
        assert rc == 0
        assert out["status"] == "initialized"
        assert out["goal"] == "Build a REST API"

    def test_init_requires_goal(self):
        out, rc = run_cmd(STATE_PY, "init", "")
        assert rc == 1
        assert "error" in out

    def test_init_state_file_created(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test goal")
        state_file = isolated_state / "state" / "evolution.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["version"] == 4
        assert data["goal"] == "Test goal"
        assert data["cycle"] == 0
        assert data["phase"] == "GENESIS"


class TestAddStrategy:
    def test_add_strategy(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        out, rc = run_cmd(STATE_PY, "add-strategy", "TDD", "Write tests first", "Tests drive design")
        assert rc == 0
        assert out["status"] == "added"
        assert out["strategy"]["id"] == "S001"
        assert out["strategy"]["name"] == "TDD"
        assert out["strategy"]["status"] == "CANDIDATE"

    def test_monotonic_ids(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        out1, _ = run_cmd(STATE_PY, "add-strategy", "A", "approach A")
        out2, _ = run_cmd(STATE_PY, "add-strategy", "B", "approach B")
        out3, _ = run_cmd(STATE_PY, "add-strategy", "C", "approach C")
        assert out1["strategy"]["id"] == "S001"
        assert out2["strategy"]["id"] == "S002"
        assert out3["strategy"]["id"] == "S003"

    def test_ids_survive_extinction(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        run_cmd(STATE_PY, "add-strategy", "B", "b")
        run_cmd(STATE_PY, "extinct", "S001", "testing")
        out, _ = run_cmd(STATE_PY, "add-strategy", "C", "c")
        assert out["strategy"]["id"] == "S003"


class TestSelect:
    def test_select_requires_strategies(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        out, rc = run_cmd(STATE_PY, "select")
        assert rc == 1
        assert "error" in out

    def test_select_returns_strategy(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "TDD", "write tests")
        out, rc = run_cmd(STATE_PY, "select")
        assert rc == 0
        assert out["selected"] == "S001"
        assert out["method"] == "contextual_thompson_sampling"
        assert "seed" in out
        assert "context" in out

    def test_select_skips_extinct(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        run_cmd(STATE_PY, "add-strategy", "B", "b")
        run_cmd(STATE_PY, "extinct", "S001", "bad")
        for _ in range(5):
            out, _ = run_cmd(STATE_PY, "select")
            assert out["selected"] == "S002"

    def test_select_reports_context(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        out, _ = run_cmd(STATE_PY, "select")
        assert out["context"] == "low"  # fitness starts at 0.0


class TestCycle:
    def test_cycle_logs_correctly(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "TDD", "test first")
        out, rc = run_cmd(STATE_PY, "cycle", "S001", "added tests", "5", "6", "0.83", "true")
        assert rc == 0
        assert out["cycle"] == 1
        assert out["fitness"] == 0.83
        assert out["kept"] is True

    def test_cycle_validates_fitness_range(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        out, rc = run_cmd(STATE_PY, "cycle", "S001", "x", "1", "1", "1.5", "true")
        assert rc == 1
        assert "error" in out

    def test_cycle_validates_tests(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        out, rc = run_cmd(STATE_PY, "cycle", "S001", "x", "10", "5", "0.5", "true")
        assert rc == 1

    def test_cycle_validates_strategy_exists(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        out, rc = run_cmd(STATE_PY, "cycle", "S999", "x", "1", "1", "0.5", "true")
        assert rc == 1

    def test_cycle_updates_strategy_stats(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        run_cmd(STATE_PY, "cycle", "S001", "try1", "3", "5", "0.6", "true")
        run_cmd(STATE_PY, "cycle", "S001", "try2", "4", "5", "0.8", "true")
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        s = state["strategies"][0]
        assert s["attempts"] == 2
        assert s["successes"] == 2
        assert s["fitness"] > 0

    def test_cycle_tracks_context_stats(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        run_cmd(STATE_PY, "cycle", "S001", "try1", "3", "5", "0.6", "true")
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        s = state["strategies"][0]
        assert "context_stats" in s
        assert "low" in s["context_stats"]
        assert s["context_stats"]["low"]["attempts"] == 1
        assert s["context_stats"]["low"]["successes"] == 1

    def test_running_average_not_ratchet(self, isolated_state):
        """Fitness should be running average, not max ratchet."""
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        run_cmd(STATE_PY, "cycle", "S001", "high", "9", "10", "0.9", "true")
        run_cmd(STATE_PY, "cycle", "S001", "low", "1", "10", "0.1", "false")
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        s = state["strategies"][0]
        # Running average of 0.9 and 0.1 should be ~0.5, NOT 0.9 (ratchet)
        assert s["fitness"] < 0.9


class TestPhaseDetection:
    def _build_state(self, isolated_state, history, phase="GROWTH"):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        state["fitness_history"] = history
        state["cycle"] = len(history)
        state["fitness"] = history[-1] if history else 0.0
        state["phase"] = phase
        state_file.write_text(json.dumps(state))
        return state_file

    def test_genesis_phase(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        run_cmd(STATE_PY, "cycle", "S001", "try", "1", "2", "0.5", "true")
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        assert state["phase"] == "GENESIS"

    def test_breakthrough_immediate(self, isolated_state):
        """BREAKTHROUGH skips hysteresis."""
        state_file = self._build_state(
            isolated_state, [0.1, 0.1, 0.1, 0.1, 0.5]
        )
        run_cmd(STATE_PY, "cycle", "S001", "jump", "9", "10", "0.9", "true")
        state = json.loads(state_file.read_text())
        assert state["phase"] == "BREAKTHROUGH"

    def test_plateau_requires_hysteresis(self, isolated_state):
        """PLATEAU needs consecutive detections."""
        state_file = self._build_state(
            isolated_state, [0.5, 0.5, 0.5, 0.5], "GROWTH"
        )
        run_cmd(STATE_PY, "cycle", "S001", "flat1", "5", "10", "0.5", "true")
        run_cmd(STATE_PY, "cycle", "S001", "flat2", "5", "10", "0.5", "true")
        run_cmd(STATE_PY, "cycle", "S001", "flat3", "5", "10", "0.5", "true")
        state = json.loads(state_file.read_text())
        assert state["phase"] == "PLATEAU"


class TestExtinct:
    def test_extinct_moves_to_graveyard(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        out, rc = run_cmd(STATE_PY, "extinct", "S001", "too slow")
        assert rc == 0
        assert out["status"] == "extinct"
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        assert len(state["strategies"]) == 0
        assert len(state["graveyard"]) == 1

    def test_extinct_nonexistent(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        out, rc = run_cmd(STATE_PY, "extinct", "S999")
        assert rc == 1


class TestMutate:
    def test_mutate_creates_child(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "Parent", "approach")
        out, rc = run_cmd(STATE_PY, "mutate", "S001", "Child", "modified approach")
        assert rc == 0
        assert out["child"]["parents"] == ["S001"]
        assert out["child"]["generation"] == 2
        assert out["child"]["id"] == "S002"


class TestCrossover:
    def test_crossover_creates_child(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        run_cmd(STATE_PY, "add-strategy", "B", "b")
        out, rc = run_cmd(STATE_PY, "crossover", "S001", "S002", "AB")
        assert rc == 0
        assert out["child"]["parents"] == ["S001", "S002"]


class TestCull:
    def test_cull_removes_weakest(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        for i in range(5):
            run_cmd(STATE_PY, "add-strategy", f"S{i}", f"approach {i}")
        for i in range(1, 6):
            sid = f"S{i:03d}"
            fitness = round(i * 0.15, 2)
            run_cmd(STATE_PY, "cycle", sid, "try1", "3", "10", str(fitness), "true")
            run_cmd(STATE_PY, "cycle", sid, "try2", "3", "10", str(fitness), "true")
        out, rc = run_cmd(STATE_PY, "cull", "3")
        assert rc == 0
        assert out["status"] == "culled"
        assert len(out["removed"]) > 0

    def test_no_cull_when_under_max(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        out, rc = run_cmd(STATE_PY, "cull")
        assert out["status"] == "no_cull_needed"


class TestResurrect:
    def test_resurrect_from_graveyard(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        run_cmd(STATE_PY, "extinct", "S001", "testing")
        out, rc = run_cmd(STATE_PY, "resurrect", "S001")
        assert rc == 0
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        assert len(state["strategies"]) == 1
        assert state["strategies"][0]["attempts"] == 0  # reset


class TestExportImport:
    def test_export_import_roundtrip(self, isolated_state):
        run_cmd(STATE_PY, "init", "Roundtrip test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        run_cmd(STATE_PY, "cycle", "S001", "try", "3", "5", "0.6", "true")
        out, _ = run_cmd(STATE_PY, "export")
        exported = json.dumps(out)
        run_cmd(STATE_PY, "reset", "--force")
        out2, rc2 = run_cmd(STATE_PY, "import", stdin_data=exported)
        assert rc2 == 0
        assert out2["status"] == "imported"

    def test_import_validates_schema(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        out, rc = run_cmd(STATE_PY, "import", stdin_data='{"foo": 1}')
        assert rc == 1
        assert "missing required fields" in out.get("error", "")


class TestWilsonScore:
    def test_wilson_properties(self):
        sys.path.insert(0, ENGINE_DIR)
        from stats import wilson_lower as _wilson_lower
        assert _wilson_lower(0, 0) == 0.0
        # Perfect record with small sample is conservative
        assert _wilson_lower(3, 3) < 1.0
        # More data -> higher lower bound
        assert _wilson_lower(90, 100) > _wilson_lower(9, 10)
        # 50/50 is between 0.2 and 0.5
        w = _wilson_lower(5, 10)
        assert 0.2 < w < 0.5


class TestSampleSD:
    def test_sd_properties(self):
        sys.path.insert(0, ENGINE_DIR)
        from stats import sample_sd as _sample_sd
        assert _sample_sd([]) == 0.0
        assert _sample_sd([5.0]) == 0.0
        assert _sample_sd([1, 1, 1, 1]) == 0.0
        # Known value: SD of [2,4,4,4,5,5,7,9] = 2.138
        sd = _sample_sd([2, 4, 4, 4, 5, 5, 7, 9])
        assert abs(sd - 2.138) < 0.01


class TestProvenStatus:
    def test_proven_requires_min_successes(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        for i in range(4):
            run_cmd(STATE_PY, "cycle", "S001", f"try{i}", "5", "10", "0.5", "true")
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        assert state["strategies"][0]["status"] == "CANDIDATE"
        run_cmd(STATE_PY, "cycle", "S001", "try5", "5", "10", "0.5", "true")
        state = json.loads(state_file.read_text())
        assert state["strategies"][0]["status"] == "PROVEN"


class TestStateIntegrity:
    def test_state_trimming(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        state["fitness_history"] = [0.5] * 600
        state["cycles"] = [{"cycle": i, "strategy": "S001", "action": "x",
                            "tests_passing": 1, "tests_total": 2, "fitness": 0.5,
                            "delta": 0.0, "kept": True, "timestamp": "t"} for i in range(600)]
        state["episodes"] = [{"cycle": i, "action": "x", "outcome": "KEPT",
                              "fitness": 0.5, "surprise": False, "timestamp": "t"} for i in range(600)]
        state_file.write_text(json.dumps(state))
        run_cmd(STATE_PY, "cycle", "S001", "trim", "1", "2", "0.5", "true")
        state = json.loads(state_file.read_text())
        assert len(state["fitness_history"]) <= 501
        assert len(state["cycles"]) <= 501


# ============================================================================
# SKILLFORGE TESTS
# ============================================================================

class TestSkillForge:
    def test_extract_skill(self, isolated_state):
        out, rc = run_cmd(SKILLFORGE_PY, "extract", "test-skill", "A test skill",
                          '["Step 1", "Step 2"]')
        assert rc == 0
        assert out["status"] == "extracted"
        assert out["skill"]["id"] == "SK001"

    def test_extract_deduplicates(self, isolated_state):
        run_cmd(SKILLFORGE_PY, "extract", "my-skill", "v1", '["step"]')
        out, rc = run_cmd(SKILLFORGE_PY, "extract", "my-skill", "v2", '["step"]')
        assert rc == 0
        assert out["status"] == "updated"
        assert out["skill"]["version"] == 2

    def test_use_records_outcome(self, isolated_state):
        run_cmd(SKILLFORGE_PY, "extract", "sk", "desc", '["s"]')
        out, rc = run_cmd(SKILLFORGE_PY, "use", "SK001", "true")
        assert rc == 0
        assert out["status"] == "recorded"
        assert out["success_rate"] == 1.0

    def test_sanitize_prevents_traversal(self, isolated_state):
        out, rc = run_cmd(SKILLFORGE_PY, "extract", "../../../etc/passwd", "evil", '["s"]')
        assert rc == 0
        assert ".." not in out["skill"]["file"]


# ============================================================================
# ANALYZE TESTS
# ============================================================================

class TestAnalyze:
    def test_effect_size(self):
        sys.path.insert(0, ENGINE_DIR)
        from analyze import effect_size
        assert effect_size([1, 2, 3], [1, 2, 3]) == 0.0
        d = effect_size([10, 11, 12], [1, 2, 3])
        assert d > 2.0  # Very large effect
        d = effect_size([5, 6, 7], [1, 2, 3])
        assert d > 0


# ============================================================================
# EDGE CASES
# ============================================================================

class TestImportTypeValidation:
    def test_import_rejects_wrong_types(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        bad_state = json.dumps({
            "goal": 123,  # should be str
            "cycle": "not_int",  # should be int
            "strategies": [],
            "graveyard": [],
            "fitness_history": [],
            "cycles": [],
            "episodes": [],
            "fitness": 0.5,
            "phase": "GENESIS",
        })
        out, rc = run_cmd(STATE_PY, "import", stdin_data=bad_state)
        assert rc == 1
        assert "Type validation failed" in out.get("error", "")

    def test_import_rejects_bad_fitness(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        bad_state = json.dumps({
            "goal": "test",
            "cycle": 0,
            "strategies": [],
            "graveyard": [],
            "fitness_history": [],
            "cycles": [],
            "episodes": [],
            "fitness": 5.0,
            "phase": "GENESIS",
        })
        out, rc = run_cmd(STATE_PY, "import", stdin_data=bad_state)
        assert rc == 1
        assert "fitness" in out.get("error", "").lower()


class TestStateMigration:
    def test_v1_to_v3_migration(self, isolated_state):
        """Old v1 state should auto-migrate to v3."""
        run_cmd(STATE_PY, "init", "Test")
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        # Simulate v1 state
        del state["version"]
        del state["cumulative_regret"]
        del state["max_cycles"]
        del state["next_strategy_id"]
        del state["_phase_pending"]
        del state["_phase_pending_count"]
        state_file.write_text(json.dumps(state))
        # Loading should trigger migration
        out, rc = run_cmd(STATE_PY, "status")
        assert rc == 0
        state = json.loads(state_file.read_text())
        assert state["version"] == 4
        assert "cumulative_regret" in state
        assert "max_cycles" in state

    def test_parent_to_parents_migration(self, isolated_state):
        """parent string field should migrate to parents list."""
        run_cmd(STATE_PY, "init", "Test")
        state_file = isolated_state / "state" / "evolution.json"
        state = json.loads(state_file.read_text())
        state["version"] = 2
        state["strategies"] = [{
            "id": "S001", "name": "A", "approach": "a", "hypothesis": "",
            "fitness": 0.5, "attempts": 1, "successes": 1, "generation": 1,
            "created": "2024-01-01", "parent": "S000", "status": "CANDIDATE",
        }]
        state_file.write_text(json.dumps(state))
        out, rc = run_cmd(STATE_PY, "status")
        assert rc == 0
        state = json.loads(state_file.read_text())
        assert state["strategies"][0]["parents"] == ["S000"]
        assert "parent" not in state["strategies"][0]


class TestEdgeCases:
    def test_negative_tests(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        out, rc = run_cmd(STATE_PY, "cycle", "S001", "x", "-1", "5", "0.5", "true")
        assert rc == 1

    def test_fitness_boundary_zero(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        out, rc = run_cmd(STATE_PY, "cycle", "S001", "x", "0", "5", "0.0", "false")
        assert rc == 0

    def test_fitness_boundary_one(self, isolated_state):
        run_cmd(STATE_PY, "init", "Test")
        run_cmd(STATE_PY, "add-strategy", "A", "a")
        out, rc = run_cmd(STATE_PY, "cycle", "S001", "x", "5", "5", "1.0", "true")
        assert rc == 0

    def test_unknown_command(self, isolated_state):
        out, rc = run_cmd(STATE_PY, "nonexistent")
        assert rc == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
