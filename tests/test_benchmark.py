#!/usr/bin/env python3
"""Tests for the Evolution benchmark engine."""

import json
import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

import benchmark


class BenchmarkTestBase(unittest.TestCase):
    """Base class with temp directory setup."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_state_dir = benchmark.STATE_DIR
        self.orig_benchmark_dir = benchmark.BENCHMARK_DIR
        self.orig_tasks_file = benchmark.TASKS_FILE
        self.orig_results_file = benchmark.RESULTS_FILE
        self.orig_evidence_file = benchmark.EVIDENCE_FILE

        benchmark.STATE_DIR = Path(self.tmpdir)
        benchmark.BENCHMARK_DIR = Path(self.tmpdir) / "benchmarks"
        benchmark.TASKS_FILE = benchmark.BENCHMARK_DIR / "tasks.json"
        benchmark.RESULTS_FILE = benchmark.BENCHMARK_DIR / "results.jsonl"
        benchmark.EVIDENCE_FILE = benchmark.BENCHMARK_DIR / "evidence.json"

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        benchmark.STATE_DIR = self.orig_state_dir
        benchmark.BENCHMARK_DIR = self.orig_benchmark_dir
        benchmark.TASKS_FILE = self.orig_tasks_file
        benchmark.RESULTS_FILE = self.orig_results_file
        benchmark.EVIDENCE_FILE = self.orig_evidence_file


class TestTaskManagement(BenchmarkTestBase):

    def test_list_builtin_tasks(self):
        tasks = benchmark.list_tasks()
        self.assertGreaterEqual(len(tasks), 5)
        names = [t["name"] for t in tasks]
        self.assertIn("rest-api-crud", names)
        self.assertIn("auth-middleware", names)
        self.assertIn("rate-limiter", names)

    def test_define_custom_task(self):
        result = benchmark.define_task(
            "custom-task",
            "A custom test task",
            {"min_fitness": 0.75, "required_tests": 5},
        )
        self.assertEqual(result["status"], "created")
        self.assertEqual(result["task"]["name"], "custom-task")

        # Should persist
        tasks = benchmark.list_tasks()
        names = [t["name"] for t in tasks]
        self.assertIn("custom-task", names)

    def test_define_duplicate_task_fails(self):
        benchmark.define_task("dup", "first", {"min_fitness": 0.5})
        result = benchmark.define_task("dup", "second", {"min_fitness": 0.5})
        self.assertIn("error", result)


class TestRecordAndCompare(BenchmarkTestBase):

    def test_record_evolution_run(self):
        result = benchmark.record_run("rest-api-crud", "evolution", 25, 0.85)
        self.assertEqual(result["status"], "recorded")
        self.assertIn("completed", result["note"].lower())

    def test_record_baseline_run(self):
        result = benchmark.record_run(
            "rest-api-crud", "baseline", 35, 0.65,
            {"human_interventions": 8},
        )
        self.assertEqual(result["status"], "recorded")
        self.assertIn("incomplete", result["note"].lower())

    def test_compare_with_no_data(self):
        result = benchmark.compare_task("nonexistent")
        self.assertIn("error", result)

    def test_compare_evolution_vs_baseline(self):
        # Record multiple runs
        for fitness in [0.82, 0.88, 0.91, 0.85, 0.87]:
            benchmark.record_run("rest-api-crud", "evolution", 25, fitness,
                                 {"human_interventions": 1})

        for fitness in [0.65, 0.70, 0.62, 0.68, 0.71]:
            benchmark.record_run("rest-api-crud", "baseline", 35, fitness,
                                 {"human_interventions": 8})

        result = benchmark.compare_task("rest-api-crud")

        # Evolution should have data
        self.assertEqual(result["evolution"]["runs"], 5)
        self.assertEqual(result["baseline"]["runs"], 5)

        # Should have statistical comparison
        self.assertIn("statistical_comparison", result)
        stat = result["statistical_comparison"]
        self.assertIn("fitness_effect_size", stat)
        self.assertEqual(stat["fitness_favors"], "evolution")

        # Should show autonomy improvement
        self.assertIn("autonomy_improvement", result)
        auto = result["autonomy_improvement"]
        self.assertGreater(auto["intervention_reduction_pct"], 50)

    def test_compare_single_mode_only(self):
        benchmark.record_run("cli-tool", "evolution", 15, 0.92)
        result = benchmark.compare_task("cli-tool")
        self.assertEqual(result["evolution"]["runs"], 1)
        self.assertEqual(result["baseline"]["note"], "No data")
        self.assertNotIn("statistical_comparison", result)


class TestAutonomyMetrics(BenchmarkTestBase):

    def test_autonomy_no_state(self):
        result = benchmark.compute_autonomy_metrics()
        self.assertIn("error", result)

    def test_autonomy_empty_cycles(self):
        state = {"cycles": [], "strategies": [], "graveyard": [],
                 "fitness_history": [], "fitness": 0}
        result = benchmark.compute_autonomy_metrics(state)
        self.assertEqual(result["autonomy_score"], 0.0)
        self.assertEqual(result["verdict"], "No data")

    def test_autonomy_healthy_state(self):
        """A well-functioning agent should score high autonomy."""
        from datetime import datetime, timezone, timedelta

        base_time = datetime(2026, 3, 22, 10, 0, 0, tzinfo=timezone.utc)
        cycles = []
        for i in range(20):
            t = base_time + timedelta(minutes=i * 3)  # 3-minute gaps = autonomous
            cycles.append({
                "cycle": i + 1,
                "strategy": f"S00{(i % 4) + 1}",
                "action": f"action {i}",
                "fitness": 0.3 + (i * 0.03),
                "delta": 0.03,
                "kept": i % 4 != 0,  # 25% revert rate
                "timestamp": t.isoformat(),
            })

        state = {
            "cycles": cycles,
            "strategies": [
                {"id": "S001", "status": "ACTIVE"},
                {"id": "S002", "status": "ACTIVE"},
                {"id": "S003", "status": "ACTIVE"},
                {"id": "S004", "status": "EXTINCT"},
            ],
            "graveyard": [
                {"id": "S005", "reason": "3 failures"},
                {"id": "S006", "reason": "superseded"},
            ],
            "fitness_history": [0.3 + i * 0.03 for i in range(20)],
            "fitness": 0.87,
        }

        result = benchmark.compute_autonomy_metrics(state)
        self.assertGreater(result["autonomy_score"], 0.6)
        self.assertIn("AUTONOMOUS", result["verdict"])

    def test_autonomy_components_present(self):
        state = {
            "cycles": [{"cycle": 1, "strategy": "S001", "kept": True,
                        "timestamp": "2026-03-22T10:00:00+00:00"}],
            "strategies": [{"id": "S001"}],
            "graveyard": [],
            "fitness_history": [0.5],
            "fitness": 0.5,
        }
        result = benchmark.compute_autonomy_metrics(state)
        self.assertIn("components", result)
        components = result["components"]
        for key in ["continuity", "strategy_diversity", "self_correction",
                     "fitness_trajectory", "extinction_decisions"]:
            self.assertIn(key, components)


class TestEvidenceCompilation(BenchmarkTestBase):

    def test_evidence_no_data(self):
        evidence = benchmark.compile_evidence()
        self.assertEqual(evidence["status"], "insufficient_data")

    def test_evidence_with_data(self):
        # Populate with enough data for a verdict
        for fitness in [0.82, 0.88, 0.91, 0.85, 0.87]:
            benchmark.record_run("rest-api-crud", "evolution", 25, fitness,
                                 {"human_interventions": 1})
        for fitness in [0.65, 0.70, 0.62, 0.68, 0.71]:
            benchmark.record_run("rest-api-crud", "baseline", 35, fitness,
                                 {"human_interventions": 8})

        evidence = benchmark.compile_evidence()
        self.assertEqual(evidence["evolution_runs"], 5)
        self.assertEqual(evidence["baseline_runs"], 5)
        self.assertIn("verdict", evidence)
        self.assertIn("effect_size", evidence["verdict"])
        # With these numbers, evolution clearly wins
        self.assertGreater(evidence["verdict"]["effect_size"], 0.8)
        self.assertIn("DEFINITIVE", evidence["verdict"]["answer"])

    def test_evidence_report_generation(self):
        benchmark.record_run("cli-tool", "evolution", 15, 0.92)
        benchmark.record_run("cli-tool", "baseline", 20, 0.75,
                             {"human_interventions": 5})
        report = benchmark.generate_report()
        self.assertIn("cli-tool", report)
        self.assertIn("VERDICT", report)


class TestStatisticalRigor(BenchmarkTestBase):

    def test_effect_size_large_difference(self):
        """When evolution clearly outperforms, effect size should be large."""
        for _ in range(10):
            benchmark.record_run("rest-api-crud", "evolution", 20, 0.90)
            benchmark.record_run("rest-api-crud", "baseline", 40, 0.60)

        result = benchmark.compare_task("rest-api-crud")
        stat = result["statistical_comparison"]
        self.assertGreater(stat["fitness_effect_size"], 0.8)
        self.assertEqual(stat["fitness_effect_interpretation"], "large")

    def test_effect_size_no_difference(self):
        """When both perform equally, effect size should be negligible."""
        for _ in range(10):
            benchmark.record_run("cli-tool", "evolution", 20, 0.75)
            benchmark.record_run("cli-tool", "baseline", 20, 0.75)

        result = benchmark.compare_task("cli-tool")
        stat = result["statistical_comparison"]
        self.assertLess(abs(stat["fitness_effect_size"]), 0.2)
        self.assertEqual(stat["fitness_effect_interpretation"], "negligible")

    def test_wilson_confidence_intervals(self):
        """Completion rates should have Wilson CIs."""
        for i in range(5):
            benchmark.record_run("auth-middleware", "evolution", 30,
                                 0.90 if i < 4 else 0.70)

        result = benchmark.compare_task("auth-middleware")
        ci = result["evolution"]["completion_ci"]
        self.assertEqual(len(ci), 2)
        self.assertLess(ci[0], ci[1])  # lower < upper


if __name__ == "__main__":
    unittest.main()
