#!/usr/bin/env python3
"""
Tests for the self-evolving agent framework modules:
- language_gradients.py — Backward attribution
- prompt_breeding.py — EvoPrompt evolutionary prompt population
- meta_optimizer.py — Three-optimizer design + meta-prompt loop
- workflow_evolution.py — DAG pipeline + AFlow + SEW
- multi_grader.py — N-dimensional grading
- error_signatures.py — Error pattern database
- closed_loop.py — Per-stage validation + adversarial critique
- mutate_dna.py integration — gradient-mutate + breed-express
"""

import json
import os
import subprocess
import sys

import pytest

ENGINE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
GRADIENTS_PY = os.path.join(ENGINE_DIR, "language_gradients.py")
BREEDING_PY = os.path.join(ENGINE_DIR, "prompt_breeding.py")
META_OPT_PY = os.path.join(ENGINE_DIR, "meta_optimizer.py")
WORKFLOW_PY = os.path.join(ENGINE_DIR, "workflow_evolution.py")
GRADER_PY = os.path.join(ENGINE_DIR, "multi_grader.py")
ERROR_SIG_PY = os.path.join(ENGINE_DIR, "error_signatures.py")
CLOSED_LOOP_PY = os.path.join(ENGINE_DIR, "closed_loop.py")
MUTATE_DNA_PY = os.path.join(ENGINE_DIR, "mutate_dna.py")
STATE_PY = os.path.join(ENGINE_DIR, "state.py")


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Run every test with an isolated state directory."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("EVOLUTION_STATE_DIR", str(state_dir))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "evolution" / ".state").mkdir(parents=True, exist_ok=True)
    (tmp_path / "evolution" / "genome").mkdir(parents=True, exist_ok=True)
    (tmp_path / "evolution" / "nucleus").mkdir(parents=True, exist_ok=True)
    yield tmp_path


def run_cmd(script, *args):
    """Run a Python engine command and return parsed JSON output."""
    result = subprocess.run(
        [sys.executable, script] + list(args),
        capture_output=True, text=True,
        env={**os.environ},
    )
    output = result.stdout.strip()
    if output:
        try:
            return json.loads(output), result.returncode
        except json.JSONDecodeError:
            return {"raw": output}, result.returncode
    return {"raw": result.stderr.strip()}, result.returncode


# ============================================================================
# LANGUAGE GRADIENTS
# ============================================================================

class TestLanguageGradients:
    def test_record_node(self):
        data, rc = run_cmd(GRADIENTS_PY, "record", "node1", "input data", "output data", "do the thing")
        assert rc == 0
        assert data["status"] == "recorded"
        assert data["node_id"] == "node1"
        assert data["step"] == 0

    def test_record_multiple_nodes(self):
        run_cmd(GRADIENTS_PY, "record", "n1", "in1", "out1", "prompt1")
        data, rc = run_cmd(GRADIENTS_PY, "record", "n2", "in2", "out2", "prompt2")
        assert data["trajectory_length"] == 2

    def test_loss_supervised(self):
        data, rc = run_cmd(GRADIENTS_PY, "loss", "hello world", "hello world", "say hello")
        assert rc == 0
        assert data["aggregate_score"] == 1.0
        assert data["mode"] == "supervised"

    def test_loss_unsupervised(self):
        data, rc = run_cmd(GRADIENTS_PY, "loss", "the quick brown fox", "", "test fox jumping")
        assert rc == 0
        assert data["mode"] == "unsupervised"

    def test_backward_pass(self):
        run_cmd(GRADIENTS_PY, "record", "n1", "task", "error in output", "do stuff")
        run_cmd(GRADIENTS_PY, "record", "n2", "prev output", "final result", "finish")
        run_cmd(GRADIENTS_PY, "loss", "error in final", "expected good", "test task")
        data, rc = run_cmd(GRADIENTS_PY, "backward")
        assert rc == 0
        assert data["status"] == "backward_complete"
        assert data["gradients_computed"] == 2

    def test_backward_no_trajectory(self):
        _, rc = run_cmd(GRADIENTS_PY, "backward")
        assert rc == 1

    def test_apply_gradients(self):
        run_cmd(GRADIENTS_PY, "record", "n1", "in", "error failed", "short")
        run_cmd(GRADIENTS_PY, "loss", "error failed", "good output", "task")
        run_cmd(GRADIENTS_PY, "backward")
        data, rc = run_cmd(GRADIENTS_PY, "apply")
        assert rc == 0
        assert data["status"] == "update_plan_ready"
        assert data["nodes_to_update"] >= 1

    def test_clear(self):
        run_cmd(GRADIENTS_PY, "record", "n1", "in", "out", "p")
        data, rc = run_cmd(GRADIENTS_PY, "clear")
        assert rc == 0
        assert data["status"] == "cleared"

    def test_history(self):
        data, rc = run_cmd(GRADIENTS_PY, "history")
        assert rc == 0
        assert "total_passes" in data


# ============================================================================
# PROMPT BREEDING
# ============================================================================

class TestPromptBreeding:
    def test_init_role(self):
        data, rc = run_cmd(BREEDING_PY, "init", "soul", "You are an autonomous agent.")
        assert rc == 0
        assert data["status"] == "initialized"
        assert data["role"] == "soul"

    def test_score_prompt(self):
        run_cmd(BREEDING_PY, "init", "soul", "Be autonomous.")
        data, rc = run_cmd(BREEDING_PY, "score", "soul", "P001", "0.75")
        assert rc == 0
        assert data["avg_fitness"] == 0.75

    def test_best_prompt(self):
        run_cmd(BREEDING_PY, "init", "soul", "Be autonomous.")
        run_cmd(BREEDING_PY, "score", "soul", "P001", "0.8")
        data, rc = run_cmd(BREEDING_PY, "best", "soul")
        assert rc == 0
        assert data["best_prompt_id"] == "P001"

    def test_mutate_prompt(self):
        run_cmd(BREEDING_PY, "init", "soul", "You are an autonomous agent. Follow instructions.")
        data, rc = run_cmd(BREEDING_PY, "mutate", "soul", "P001")
        assert rc == 0
        assert data["status"] == "mutated"
        assert data["parent_id"] == "P001"

    def test_crossover(self):
        run_cmd(BREEDING_PY, "init", "soul", "Be fast. Execute immediately.")
        run_cmd(BREEDING_PY, "mutate", "soul", "P001")
        data, rc = run_cmd(BREEDING_PY, "crossover", "soul", "P001", "P002")
        assert rc == 0
        assert data["status"] == "crossover"

    def test_breed_cycle(self):
        run_cmd(BREEDING_PY, "init", "soul", "Be autonomous. Follow instructions.")
        run_cmd(BREEDING_PY, "mutate", "soul", "P001")
        run_cmd(BREEDING_PY, "score", "soul", "P001", "0.7")
        run_cmd(BREEDING_PY, "score", "soul", "P002", "0.5")
        data, rc = run_cmd(BREEDING_PY, "breed", "soul")
        assert rc == 0
        assert data["status"] == "bred"

    def test_evolve_mutator(self):
        data, rc = run_cmd(BREEDING_PY, "evolve-mutator")
        assert rc == 0
        assert data["status"] == "mutator_evolved"

    def test_status(self):
        run_cmd(BREEDING_PY, "init", "soul", "Be autonomous.")
        data, rc = run_cmd(BREEDING_PY, "status")
        assert rc == 0
        assert "soul" in data["roles"]


# ============================================================================
# META OPTIMIZER
# ============================================================================

class TestMetaOptimizer:
    def test_optimize_prompt(self):
        gradient = json.dumps({"blame_score": 0.8, "attribution": "Node produced errors",
                               "suggested_fix": "Add error handling instructions"})
        data, rc = run_cmd(META_OPT_PY, "optimize-prompt", "node1", "Do the thing", gradient)
        assert rc == 0
        assert data["status"] == "prompt_optimized"
        assert "error" in data["optimized_prompt"].lower()

    def test_optimize_tools(self):
        gradient = json.dumps({"blame_score": 0.6, "attribution": "error in output"})
        data, rc = run_cmd(META_OPT_PY, "optimize-tools", "node1", '["tool1"]', gradient)
        assert rc == 0
        assert data["status"] == "tools_optimized"

    def test_optimize_topology(self):
        pipeline = json.dumps({"nodes": ["n1", "n2", "n3"]})
        gradients = json.dumps([
            {"node_id": "n1", "blame_score": 0.8},
            {"node_id": "n2", "blame_score": 0.1},
        ])
        data, rc = run_cmd(META_OPT_PY, "optimize-topology", pipeline, gradients)
        assert rc == 0
        assert data["status"] == "topology_optimized"

    def test_meta_loop(self):
        feedback = json.dumps([
            {"dimension": "correctness", "score": 0.9, "feedback": "Good"},
            {"dimension": "completeness", "score": 0.5, "feedback": "Missing edge cases"},
        ])
        data, rc = run_cmd(META_OPT_PY, "meta-loop", "Do X", '{"results": "ok"}', feedback)
        assert rc == 0
        assert data["avg_score"] == 0.7
        assert data["status"] == "continue"  # Below 0.8 threshold

    def test_threshold_check_pass(self):
        data, rc = run_cmd(META_OPT_PY, "threshold-check", "0.85")
        assert rc == 0
        assert data["passed"] is True

    def test_threshold_check_fail(self):
        data, rc = run_cmd(META_OPT_PY, "threshold-check", "0.60")
        assert rc == 0
        assert data["passed"] is False

    def test_status(self):
        data, rc = run_cmd(META_OPT_PY, "status")
        assert rc == 0
        assert "total_optimizations" in data


# ============================================================================
# WORKFLOW EVOLUTION
# ============================================================================

class TestWorkflowEvolution:
    def test_init(self):
        data, rc = run_cmd(WORKFLOW_PY, "init", "test-pipeline", "A test pipeline")
        assert rc == 0
        assert data["status"] == "initialized"

    def test_add_node(self):
        run_cmd(WORKFLOW_PY, "init", "pipe", "desc")
        data, rc = run_cmd(WORKFLOW_PY, "add-node", "analyze", "analyzer", "Analyze the task")
        assert rc == 0
        assert data["status"] == "node_added"

    def test_add_edge(self):
        run_cmd(WORKFLOW_PY, "init", "pipe", "desc")
        run_cmd(WORKFLOW_PY, "add-node", "n1", "role1", "prompt1")
        run_cmd(WORKFLOW_PY, "add-node", "n2", "role2", "prompt2")
        data, rc = run_cmd(WORKFLOW_PY, "add-edge", "n1", "n2")
        assert rc == 0
        assert data["status"] == "edge_added"

    def test_cycle_detection(self):
        run_cmd(WORKFLOW_PY, "init", "pipe", "desc")
        run_cmd(WORKFLOW_PY, "add-node", "a", "r", "p")
        run_cmd(WORKFLOW_PY, "add-node", "b", "r", "p")
        run_cmd(WORKFLOW_PY, "add-edge", "a", "b")
        _, rc = run_cmd(WORKFLOW_PY, "add-edge", "b", "a")
        assert rc == 1  # Cycle should be rejected

    def test_topology(self):
        run_cmd(WORKFLOW_PY, "init", "pipe", "desc")
        run_cmd(WORKFLOW_PY, "add-node", "n1", "r1", "p1")
        run_cmd(WORKFLOW_PY, "add-node", "n2", "r2", "p2")
        run_cmd(WORKFLOW_PY, "add-edge", "n1", "n2")
        data, rc = run_cmd(WORKFLOW_PY, "topology")
        assert rc == 0
        assert data["total_nodes"] == 2
        assert data["execution_order"] == ["n1", "n2"]

    def test_parallel_groups(self):
        run_cmd(WORKFLOW_PY, "init", "pipe", "desc")
        run_cmd(WORKFLOW_PY, "add-node", "root", "r", "p")
        run_cmd(WORKFLOW_PY, "add-node", "a", "r", "p")
        run_cmd(WORKFLOW_PY, "add-node", "b", "r", "p")
        run_cmd(WORKFLOW_PY, "add-edge", "root", "a")
        run_cmd(WORKFLOW_PY, "add-edge", "root", "b")
        data, rc = run_cmd(WORKFLOW_PY, "parallel-groups")
        assert rc == 0
        assert data["max_parallelism"] == 2  # a and b can run in parallel

    def test_validate(self):
        run_cmd(WORKFLOW_PY, "init", "pipe", "desc")
        run_cmd(WORKFLOW_PY, "add-node", "n1", "r", "p")
        data, rc = run_cmd(WORKFLOW_PY, "validate")
        assert rc == 0
        assert data["valid"] is True

    def test_score_node(self):
        run_cmd(WORKFLOW_PY, "init", "pipe", "desc")
        run_cmd(WORKFLOW_PY, "add-node", "n1", "r", "p")
        data, rc = run_cmd(WORKFLOW_PY, "score-node", "n1", "0.8")
        assert rc == 0
        assert data["avg_fitness"] == 0.8

    def test_optimize(self):
        run_cmd(WORKFLOW_PY, "init", "pipe", "desc")
        run_cmd(WORKFLOW_PY, "add-node", "n1", "r", "p")
        data, rc = run_cmd(WORKFLOW_PY, "optimize")
        assert rc == 0
        assert data["status"] == "optimized"

    def test_aflow(self):
        run_cmd(WORKFLOW_PY, "init", "pipe", "desc")
        data, rc = run_cmd(WORKFLOW_PY, "aflow", "Build a REST API")
        assert rc == 0
        assert data["status"] == "decompositions_generated"
        assert len(data["decompositions"]) == 3

    def test_remove_node(self):
        run_cmd(WORKFLOW_PY, "init", "pipe", "desc")
        run_cmd(WORKFLOW_PY, "add-node", "n1", "r", "p")
        data, rc = run_cmd(WORKFLOW_PY, "remove-node", "n1")
        assert rc == 0
        assert data["total_nodes"] == 0


# ============================================================================
# MULTI GRADER
# ============================================================================

class TestMultiGrader:
    def test_grade_output(self):
        data, rc = run_cmd(GRADER_PY, "grade",
                          "def add(a, b): return a + b",
                          "Write an add function")
        assert rc == 0
        assert "aggregate_score" in data
        assert data["grader_count"] == 4  # 4 default graders

    def test_grade_with_errors(self):
        data, rc = run_cmd(GRADER_PY, "grade",
                          "Traceback: TypeError: undefined is not a function",
                          "Build a working function")
        assert rc == 0
        # Correctness should be low due to error keywords
        correctness = next(g for g in data["grades"] if g["dimension"] == "correctness")
        assert correctness["score"] < 0.5

    def test_grade_empty_output(self):
        data, rc = run_cmd(GRADER_PY, "grade", "", "Write something")
        assert rc == 0
        correctness = next(g for g in data["grades"] if g["dimension"] == "correctness")
        assert correctness["score"] == 0.0

    def test_add_custom_grader(self):
        data, rc = run_cmd(GRADER_PY, "add-grader", "testability",
                          "testability", "Is the code easy to test?")
        assert rc == 0
        assert data["total_graders"] == 5

    def test_remove_grader(self):
        data, rc = run_cmd(GRADER_PY, "remove-grader", "robustness")
        assert rc == 0
        assert data["remaining"] == 3

    def test_list_graders(self):
        data, rc = run_cmd(GRADER_PY, "list-graders")
        assert rc == 0
        assert data["total"] == 4

    def test_aggregate(self):
        grades = json.dumps([
            {"dimension": "a", "score": 0.8, "weight": 0.5},
            {"dimension": "b", "score": 0.6, "weight": 0.5},
        ])
        data, rc = run_cmd(GRADER_PY, "aggregate", grades)
        assert rc == 0
        assert data["aggregate_score"] == 0.7

    def test_calibrate(self):
        # Grade something first to create history
        run_cmd(GRADER_PY, "grade", "hello world", "say hello")
        data, rc = run_cmd(GRADER_PY, "calibrate", "correctness", "0.9")
        assert rc == 0
        assert data["status"] == "calibrated"


# ============================================================================
# ERROR SIGNATURES
# ============================================================================

class TestErrorSignatures:
    def test_extract_python_error(self):
        data, rc = run_cmd(ERROR_SIG_PY, "extract", "ValueError: invalid literal for int()")
        assert rc == 0
        assert data["error_type"] == "python_exception"
        assert data["key_fields"]["error_class"] == "ValueError"

    def test_extract_node_error(self):
        data, rc = run_cmd(ERROR_SIG_PY, "extract", "ReferenceError: x is not defined")
        assert rc == 0
        # ReferenceError matches node_error pattern (not python_exception)
        assert data["error_type"] in ("node_error", "python_exception")
        assert data["key_fields"]["error_class"] == "ReferenceError"

    def test_extract_generic(self):
        data, rc = run_cmd(ERROR_SIG_PY, "extract", "something went wrong")
        assert rc == 0
        assert data["error_type"] == "generic"

    def test_match_exact(self):
        # Extract first, then match
        run_cmd(ERROR_SIG_PY, "extract", "ValueError: bad value")
        data, rc = run_cmd(ERROR_SIG_PY, "match", "ValueError: bad value")
        assert rc == 0
        assert data["status"] == "matched"
        assert data["match_type"] == "exact"

    def test_match_no_match(self):
        data, rc = run_cmd(ERROR_SIG_PY, "match", "completely unique error xyz123")
        assert rc == 0
        assert data["status"] in ("no_match", "fuzzy_matched")

    def test_resolve(self):
        run_cmd(ERROR_SIG_PY, "extract", "ImportError: No module named foo")
        # Get the signature ID
        data, _ = run_cmd(ERROR_SIG_PY, "match", "ImportError: No module named foo")
        sig_id = data["signature_id"]
        resolve_data, rc = run_cmd(ERROR_SIG_PY, "resolve", sig_id, "pip install foo", "true")
        assert rc == 0
        assert resolve_data["success"] is True

    def test_stats(self):
        run_cmd(ERROR_SIG_PY, "extract", "SyntaxError: unexpected token")
        data, rc = run_cmd(ERROR_SIG_PY, "stats")
        assert rc == 0
        assert data["total_signatures"] >= 1

    def test_list(self):
        run_cmd(ERROR_SIG_PY, "extract", "NameError: name 'x' is not defined")
        data, rc = run_cmd(ERROR_SIG_PY, "list")
        assert rc == 0
        assert data["total"] >= 1

    def test_occurrence_counting(self):
        run_cmd(ERROR_SIG_PY, "extract", "ValueError: test")
        run_cmd(ERROR_SIG_PY, "extract", "ValueError: test")
        data, rc = run_cmd(ERROR_SIG_PY, "extract", "ValueError: test")
        assert data["occurrences"] == 3


# ============================================================================
# CLOSED LOOP
# ============================================================================

class TestClosedLoop:
    def test_validate_pass(self):
        criteria = json.dumps([
            {"name": "non_empty", "type": "non_empty"},
            {"name": "no_errors", "type": "no_errors"},
        ])
        data, rc = run_cmd(CLOSED_LOOP_PY, "validate", "stage1", "Hello world", criteria)
        assert rc == 0
        assert data["all_passed"] is True

    def test_validate_fail_empty(self):
        criteria = json.dumps([{"name": "non_empty", "type": "non_empty"}])
        data, rc = run_cmd(CLOSED_LOOP_PY, "validate", "stage1", "", criteria)
        assert rc == 0
        assert data["all_passed"] is False

    def test_validate_fail_errors(self):
        criteria = json.dumps([{"name": "no_errors", "type": "no_errors"}])
        data, rc = run_cmd(CLOSED_LOOP_PY, "validate", "stage1",
                          "Traceback: error occurred", criteria)
        assert rc == 0
        assert data["all_passed"] is False

    def test_validate_contains(self):
        criteria = json.dumps([{"name": "has_return", "type": "contains", "value": "return"}])
        data, rc = run_cmd(CLOSED_LOOP_PY, "validate", "stage1",
                          "def f(): return 42", criteria)
        assert rc == 0
        assert data["all_passed"] is True

    def test_validate_json_valid(self):
        criteria = json.dumps([{"name": "valid_json", "type": "json_valid"}])
        data, rc = run_cmd(CLOSED_LOOP_PY, "validate", "stage1", '{"key": "value"}', criteria)
        assert rc == 0
        assert data["all_passed"] is True

    def test_critique_all_perspectives(self):
        data, rc = run_cmd(CLOSED_LOOP_PY, "critique",
                          "eval(user_input)\nfor i in range(n):\n  for j in range(n):\n    pass",
                          "Process user data safely")
        assert rc == 0
        assert data["total_issues"] > 0
        # Should catch eval() as critical security issue
        assert any(c["perspective_id"] == "security" and c["issue_count"] > 0
                   for c in data["critiques"])

    def test_critique_single_perspective(self):
        data, rc = run_cmd(CLOSED_LOOP_PY, "critique",
                          "simple code", "do thing", "skeptic")
        assert rc == 0
        assert len(data["critiques"]) == 1

    def test_heal(self):
        validation = json.dumps({
            "correction_hints": ["Output is empty", "Missing 'return' keyword"]
        })
        data, rc = run_cmd(CLOSED_LOOP_PY, "heal", "stage1", "", validation)
        assert rc == 0
        assert data["retry_recommended"] is True
        assert len(data["corrections"]) == 2

    def test_pipeline_check(self):
        results = json.dumps([
            {"stage_id": "s1", "passed": True},
            {"stage_id": "s2", "passed": False},
            {"stage_id": "s3", "passed": True},
        ])
        data, rc = run_cmd(CLOSED_LOOP_PY, "pipeline-check", results)
        assert rc == 0
        assert data["pipeline_health"] == pytest.approx(0.67, abs=0.01)
        assert data["failed_stages"] == 1

    def test_configure(self):
        criteria = json.dumps([{"name": "check1", "type": "non_empty"}])
        data, rc = run_cmd(CLOSED_LOOP_PY, "configure", "stage1", "3", criteria)
        assert rc == 0
        assert data["status"] == "configured"

    def test_status(self):
        data, rc = run_cmd(CLOSED_LOOP_PY, "status")
        assert rc == 0
        assert "total_validations" in data


# ============================================================================
# INTEGRATION: DEPLOY THRESHOLD IN STATE
# ============================================================================

class TestDeployThreshold:
    def _init_state(self):
        run_cmd(STATE_PY, "init", "test goal")

    def test_get_default_threshold(self):
        self._init_state()
        data, rc = run_cmd(STATE_PY, "deploy-threshold")
        assert rc == 0
        assert data["deploy_threshold"] == 0.80

    def test_set_threshold(self):
        self._init_state()
        data, rc = run_cmd(STATE_PY, "deploy-threshold", "0.90")
        assert rc == 0
        assert data["deploy_threshold"] == 0.90
