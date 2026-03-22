#!/usr/bin/env python3
"""Tests for sports_edge and politics_edge modules."""

import json
import math
import os
import sys
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"


# ============================================================================
# SPORTS EDGE TESTS
# ============================================================================

class TestEloWinProbability:
    def test_equal_elo(self):
        from engine.sports_edge import elo_win_probability
        result = elo_win_probability(1500, 1500)
        assert abs(result["team_a_prob"] - 0.5) < 0.001
        assert abs(result["team_b_prob"] - 0.5) < 0.001

    def test_higher_elo_favored(self):
        from engine.sports_edge import elo_win_probability
        result = elo_win_probability(1700, 1500)
        assert result["team_a_prob"] > 0.7

    def test_home_advantage(self):
        from engine.sports_edge import elo_win_probability
        away = elo_win_probability(1500, 1500, home_advantage=0)
        home = elo_win_probability(1500, 1500, home_advantage=100)
        assert home["team_a_prob"] > away["team_a_prob"]

    def test_probabilities_sum_to_one(self):
        from engine.sports_edge import elo_win_probability
        result = elo_win_probability(1600, 1450, home_advantage=50)
        assert abs(result["team_a_prob"] + result["team_b_prob"] - 1.0) < 0.001


class TestOddsConversion:
    def test_american_negative(self):
        from engine.sports_edge import american_odds_to_prob
        # -150 → bet $150 to win $100 → 60%
        p = american_odds_to_prob(-150)
        assert abs(p - 0.60) < 0.01

    def test_american_positive(self):
        from engine.sports_edge import american_odds_to_prob
        # +200 → bet $100 to win $200 → 33.3%
        p = american_odds_to_prob(200)
        assert abs(p - 0.333) < 0.01

    def test_decimal_odds(self):
        from engine.sports_edge import decimal_odds_to_prob
        assert abs(decimal_odds_to_prob(2.0) - 0.50) < 0.01
        assert abs(decimal_odds_to_prob(4.0) - 0.25) < 0.01


class TestVigRemoval:
    def test_remove_vig_proportional(self):
        from engine.sports_edge import remove_vig
        # Typical -110/-110 line: implied = [0.5238, 0.5238], sum = 1.0476
        implied = [0.5238, 0.5238]
        fair = remove_vig(implied)
        assert abs(sum(fair) - 1.0) < 0.001
        assert abs(fair[0] - 0.5) < 0.01

    def test_devig_american_odds(self):
        from engine.sports_edge import devig_odds
        result = devig_odds([-150, +130], odds_format="american")
        assert abs(sum(result["fair_probs"]) - 1.0) < 0.001
        assert result["vig"] > 0
        # Favorite should have higher fair prob
        assert result["fair_probs"][0] > result["fair_probs"][1]

    def test_devig_three_way(self):
        from engine.sports_edge import devig_odds
        # Soccer: home/draw/away
        result = devig_odds([2.10, 3.40, 3.60], odds_format="decimal")
        assert len(result["fair_probs"]) == 3
        assert abs(sum(result["fair_probs"]) - 1.0) < 0.001


class TestSourceAggregation:
    def test_single_source(self):
        from engine.sports_edge import aggregate_sources
        result = aggregate_sources([
            {"name": "espn", "probs": [0.65, 0.35], "weight": 1.0},
        ])
        assert result["consensus_probs"] == [0.65, 0.35]
        assert result["num_sources"] == 1

    def test_multi_source_agreement(self):
        from engine.sports_edge import aggregate_sources, CONFIDENCE_SPORTS_MULTI
        result = aggregate_sources([
            {"name": "espn", "probs": [0.60, 0.40], "weight": 1.0},
            {"name": "538", "probs": [0.62, 0.38], "weight": 1.0},
        ])
        # Consensus should be ~0.61
        assert abs(result["consensus_probs"][0] - 0.61) < 0.01
        assert result["confidence"] >= CONFIDENCE_SPORTS_MULTI

    def test_strong_agreement_boosts_confidence(self):
        from engine.sports_edge import aggregate_sources, CONFIDENCE_SPORTS_STRONG
        result = aggregate_sources([
            {"name": "espn", "probs": [0.70, 0.30], "weight": 1.0},
            {"name": "538", "probs": [0.71, 0.29], "weight": 1.0},
            {"name": "vegas", "probs": [0.69, 0.31], "weight": 1.0},
        ])
        assert result["confidence"] == CONFIDENCE_SPORTS_STRONG

    def test_weighted_sources(self):
        from engine.sports_edge import aggregate_sources
        result = aggregate_sources([
            {"name": "good", "probs": [0.80, 0.20], "weight": 3.0},
            {"name": "bad", "probs": [0.50, 0.50], "weight": 1.0},
        ])
        # Should be closer to 0.80 than 0.50
        assert result["consensus_probs"][0] > 0.70


class TestSportsEdge:
    def test_underpriced_outcome(self):
        from engine.sports_edge import compute_sports_edge
        result = compute_sports_edge(
            [0.70, 0.30], [0.55, 0.45],
            labels=["Team A", "Team B"],
        )
        assert result["actionable_count"] >= 1
        trades = result["actionable_trades"]
        assert any(t["label"] == "Team A" and t["action"] == "BUY_YES" for t in trades)

    def test_no_edge(self):
        from engine.sports_edge import compute_sports_edge
        result = compute_sports_edge([0.50, 0.50], [0.50, 0.50])
        assert result["actionable_count"] == 0

    def test_structural_arb(self):
        from engine.sports_edge import compute_sports_edge
        result = compute_sports_edge(
            [0.30, 0.30, 0.40],
            [0.25, 0.25, 0.30],  # Sum = 0.80
        )
        assert result["has_structural_arb"] is True
        assert result["arb_gap"] > 0.10


class TestSportsSignalEvaluation:
    def test_full_evaluation(self):
        from engine.sports_edge import evaluate_sports_signal
        result = evaluate_sports_signal({
            "market_id": "nba_lakers_celtics",
            "sport": "nba",
            "outcomes": ["Lakers", "Celtics"],
            "sources": [
                {"name": "espn", "probs": [0.55, 0.45], "weight": 1.0},
                {"name": "538", "probs": [0.57, 0.43], "weight": 1.0},
            ],
            "market_prices": [0.45, 0.50],
        })
        assert "consensus" in result
        assert "edge_analysis" in result
        assert result["actionable_count"] >= 0


# ============================================================================
# POLITICS EDGE TESTS
# ============================================================================

class TestPollAggregation:
    def test_single_poll(self):
        from engine.politics_edge import aggregate_polls
        result = aggregate_polls([{
            "pollster": "Quinnipiac",
            "rating": "A+",
            "date": "2026-03-20",
            "sample_size": 1500,
            "results": {"Candidate A": 52, "Candidate B": 48},
        }])
        assert abs(result["fair_probs"]["Candidate A"] - 0.52) < 0.02

    def test_multiple_polls_weighted(self):
        from engine.politics_edge import aggregate_polls
        result = aggregate_polls([
            {
                "pollster": "A+ Pollster", "rating": "A+",
                "date": "2026-03-21", "sample_size": 2000,
                "results": {"X": 55, "Y": 45},
            },
            {
                "pollster": "C Pollster", "rating": "C",
                "date": "2026-03-15", "sample_size": 500,
                "results": {"X": 40, "Y": 60},
            },
        ])
        # A+ pollster should dominate over C pollster
        assert result["fair_probs"]["X"] > 0.50

    def test_recency_weighting(self):
        from engine.politics_edge import aggregate_polls
        result = aggregate_polls([
            {
                "pollster": "Recent", "rating": "B",
                "date": "2026-03-21", "sample_size": 1000,
                "results": {"A": 60, "B": 40},
            },
            {
                "pollster": "Old", "rating": "B",
                "date": "2025-12-01", "sample_size": 1000,
                "results": {"A": 40, "B": 60},
            },
        ])
        # Recent poll should dominate
        assert result["fair_probs"]["A"] > 0.55

    def test_confidence_scales_with_polls(self):
        from engine.politics_edge import aggregate_polls, CONFIDENCE_POLLS_STRONG
        polls = [
            {
                "pollster": f"Pollster {i}", "rating": "A",
                "date": "2026-03-20", "sample_size": 1500,
                "results": {"Win": 55, "Lose": 45},
            }
            for i in range(6)
        ]
        result = aggregate_polls(polls)
        assert result["confidence"] == CONFIDENCE_POLLS_STRONG


class TestStructuralArb:
    def test_detects_arb(self):
        from engine.politics_edge import detect_structural_arb
        result = detect_structural_arb(
            ["A", "B", "C", "D", "E"],
            [0.30, 0.25, 0.15, 0.10, 0.05],  # Sum = 0.85
        )
        assert result["has_arb"] is True
        assert result["arb_gap_pct"] == 15.0
        assert result["guaranteed_profit"] > 0

    def test_no_arb_when_overpriced(self):
        from engine.politics_edge import detect_structural_arb
        result = detect_structural_arb(
            ["A", "B"],
            [0.55, 0.50],  # Sum = 1.05
        )
        assert result["has_arb"] is False
        assert result.get("overpriced") is True

    def test_balanced_market(self):
        from engine.politics_edge import detect_structural_arb
        result = detect_structural_arb(
            ["A", "B"],
            [0.50, 0.50],
        )
        assert result["has_arb"] is False


class TestStaleMarketDetection:
    def test_detects_stale(self):
        from engine.politics_edge import detect_stale_market
        result = detect_stale_market(
            known_result="Biden",
            outcomes=["Biden", "Trump", "Other"],
            market_prices=[0.60, 0.30, 0.10],
        )
        assert result["stale"] is True
        assert result["edge"] > 0.30
        assert result["action"] == "BUY_YES"

    def test_not_stale_when_updated(self):
        from engine.politics_edge import detect_stale_market
        result = detect_stale_market(
            known_result="Biden",
            outcomes=["Biden", "Trump"],
            market_prices=[0.98, 0.02],
        )
        assert result["stale"] is False

    def test_invalid_result(self):
        from engine.politics_edge import detect_stale_market
        result = detect_stale_market("Nobody", ["A", "B"], [0.5, 0.5])
        assert "error" in result


class TestPoliticsSignalEvaluation:
    def test_poll_aggregate_signal(self):
        from engine.politics_edge import evaluate_politics_signal
        result = evaluate_politics_signal({
            "type": "poll_aggregate",
            "market_id": "2026_election",
            "outcomes": ["A", "B"],
            "market_prices": [0.40, 0.55],
            "polls": [
                {"pollster": "Good", "rating": "A", "date": "2026-03-20",
                 "sample_size": 1500, "results": {"A": 55, "B": 45}},
                {"pollster": "Ok", "rating": "B", "date": "2026-03-19",
                 "sample_size": 1000, "results": {"A": 53, "B": 47}},
            ],
        })
        assert result["type"] == "poll_aggregate"
        assert "consensus" in result
        assert result["actionable_count"] >= 0

    def test_structural_arb_signal(self):
        from engine.politics_edge import evaluate_politics_signal
        result = evaluate_politics_signal({
            "type": "structural_arb",
            "market_id": "primary",
            "outcomes": ["A", "B", "C", "D"],
            "market_prices": [0.30, 0.20, 0.15, 0.10],
        })
        assert result["type"] == "structural_arb"
        assert result["arb_analysis"]["has_arb"] is True

    def test_stale_market_signal(self):
        from engine.politics_edge import evaluate_politics_signal
        result = evaluate_politics_signal({
            "type": "stale_market",
            "market_id": "decided_vote",
            "outcomes": ["Yes", "No"],
            "market_prices": [0.65, 0.35],
            "known_result": "Yes",
        })
        assert result["type"] == "stale_market"
        assert result["actionable_count"] == 1


# ============================================================================
# CLI TESTS
# ============================================================================

import subprocess

class TestSportsCLI:
    def test_elo_command(self):
        result = subprocess.run(
            [sys.executable, str(ENGINE_DIR / "sports_edge.py"), "elo", "1600", "1500"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["team_a_prob"] > 0.5

    def test_devig_command(self):
        result = subprocess.run(
            [sys.executable, str(ENGINE_DIR / "sports_edge.py"), "devig", "[-150, 130]"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert abs(sum(data["fair_probs"]) - 1.0) < 0.01


class TestPoliticsCLI:
    def test_structural_arb_command(self):
        result = subprocess.run(
            [sys.executable, str(ENGINE_DIR / "politics_edge.py"),
             "structural-arb", '["A","B","C"]', '[0.30,0.25,0.20]'],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["has_arb"] is True


class TestEvolveCLIWiring:
    def test_sports_elo_via_evolve(self):
        result = subprocess.run(
            ["bash", str(ENGINE_DIR.parent / "engine" / "evolve"), "sports-elo", "1600", "1500"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["team_a_prob"] > 0.5

    def test_politics_arb_via_evolve(self):
        result = subprocess.run(
            ["bash", str(ENGINE_DIR.parent / "engine" / "evolve"),
             "politics-arb", '["A","B","C"]', '[0.30,0.25,0.20]'],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["has_arb"] is True
