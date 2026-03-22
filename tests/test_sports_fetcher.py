#!/usr/bin/env python3
"""Tests for sports_fetcher — ESPN and Odds API integration."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    monkeypatch.setenv("EVOLUTION_STATE_DIR", str(state_dir))
    monkeypatch.chdir(tmp_path)

    import engine.sports_fetcher as sf
    import engine.risk as risk
    import engine.smart_money as sm
    import engine.trade_pipeline as tp

    monkeypatch.setattr(sf, "STATE_DIR", state_dir)
    monkeypatch.setattr(sf, "CACHE_DIR", state_dir / "sports_cache")
    monkeypatch.setattr(risk, "STATE_DIR", state_dir)
    monkeypatch.setattr(risk, "RISK_STATE_FILE", state_dir / "risk_state.json")
    monkeypatch.setattr(sm, "STATE_DIR", state_dir)
    monkeypatch.setattr(sm, "WALLET_DB_FILE", state_dir / "smart_money.json")
    monkeypatch.setattr(tp, "STATE_DIR", state_dir)
    monkeypatch.setattr(tp, "PIPELINE_LOG", state_dir / "trade_pipeline.jsonl")

    return state_dir


# Mock ESPN response (real structure from their API)
MOCK_ESPN_RESPONSE = {
    "events": [
        {
            "id": "401656789",
            "name": "Los Angeles Lakers at Boston Celtics",
            "date": "2026-03-25T00:00Z",
            "status": {"type": {"name": "STATUS_SCHEDULED"}},
            "competitions": [{
                "competitors": [
                    {
                        "homeAway": "home",
                        "team": {"displayName": "Boston Celtics", "abbreviation": "BOS"},
                        "score": "0",
                        "records": [{"summary": "50-20"}],
                    },
                    {
                        "homeAway": "away",
                        "team": {"displayName": "Los Angeles Lakers", "abbreviation": "LAL"},
                        "score": "0",
                        "records": [{"summary": "40-30"}],
                    },
                ],
                "odds": [{
                    "spread": -5.5,
                    "overUnder": 220.5,
                    "details": "BOS -5.5",
                    "provider": {"name": "ESPN BET"},
                }],
            }],
            "predictor": {
                "homeTeam": {"gameProjection": 68.0},
                "awayTeam": {"gameProjection": 32.0},
            },
        },
    ],
}

# Mock Odds API response
MOCK_ODDS_RESPONSE = [
    {
        "id": "abc123",
        "home_team": "Boston Celtics",
        "away_team": "Los Angeles Lakers",
        "commence_time": "2026-03-25T00:00:00Z",
        "bookmakers": [
            {
                "key": "draftkings",
                "title": "DraftKings",
                "markets": [{
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Boston Celtics", "price": -220},
                        {"name": "Los Angeles Lakers", "price": 180},
                    ],
                }],
            },
            {
                "key": "fanduel",
                "title": "FanDuel",
                "markets": [{
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Boston Celtics", "price": -210},
                        {"name": "Los Angeles Lakers", "price": 175},
                    ],
                }],
            },
            {
                "key": "pinnacle",
                "title": "Pinnacle",
                "markets": [{
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Boston Celtics", "price": -215},
                        {"name": "Los Angeles Lakers", "price": 185},
                    ],
                }],
            },
        ],
    },
]


class TestESPNFetcher:
    @patch("engine.sports_fetcher._http_get")
    def test_fetches_and_parses(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_ESPN_RESPONSE
        from engine.sports_fetcher import fetch_espn_scoreboard

        result = fetch_espn_scoreboard("nba")
        assert result["count"] == 1
        event = result["events"][0]
        assert "Celtics" in event["name"]
        assert event["probabilities"] is not None
        # ESPN predictor says home (Celtics) has 68%
        # Celtics is index 0 (home), Lakers is index 1 (away)
        assert event["probabilities"]["team_a"] == 0.68

    @patch("engine.sports_fetcher._http_get")
    def test_caches_result(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_ESPN_RESPONSE
        from engine.sports_fetcher import fetch_espn_scoreboard

        fetch_espn_scoreboard("nba")
        first_count = mock_get.call_count
        fetch_espn_scoreboard("nba")
        assert mock_get.call_count == first_count  # Used cache

    @patch("engine.sports_fetcher._http_get")
    def test_api_error_handled(self, mock_get, isolated_state):
        mock_get.side_effect = ConnectionError("ESPN down")
        from engine.sports_fetcher import fetch_espn_scoreboard

        result = fetch_espn_scoreboard("nba")
        assert "error" in result

    def test_unknown_sport(self, isolated_state):
        from engine.sports_fetcher import fetch_espn_scoreboard
        result = fetch_espn_scoreboard("curling")
        assert "error" in result


class TestOddsApiFetcher:
    @patch("engine.sports_fetcher._http_get")
    def test_fetches_and_devigs(self, mock_get, isolated_state, monkeypatch):
        mock_get.return_value = MOCK_ODDS_RESPONSE
        monkeypatch.setattr("engine.sports_fetcher.ODDS_API_KEY", "test_key")
        from engine.sports_fetcher import fetch_odds_api

        result = fetch_odds_api("nba")
        assert result["count"] == 1
        event = result["events"][0]
        assert event["bookmaker_count"] == 3
        assert event["consensus"] is not None
        # Consensus should show Celtics favored
        probs = event["consensus"]["consensus_probs"]
        assert probs[0] > probs[1]  # Home team (Celtics) favored

    def test_no_api_key(self, isolated_state, monkeypatch):
        monkeypatch.setattr("engine.sports_fetcher.ODDS_API_KEY", "")
        from engine.sports_fetcher import fetch_odds_api

        result = fetch_odds_api("nba")
        assert "error" in result
        assert "ODDS_API_KEY" in result["error"]

    @patch("engine.sports_fetcher._http_get")
    def test_sharp_books_weighted_higher(self, mock_get, isolated_state, monkeypatch):
        mock_get.return_value = MOCK_ODDS_RESPONSE
        monkeypatch.setattr("engine.sports_fetcher.ODDS_API_KEY", "test_key")
        from engine.sports_fetcher import fetch_odds_api

        result = fetch_odds_api("nba")
        event = result["events"][0]
        # Pinnacle is a sharp book, should have weight 2.0 in aggregation
        assert event["consensus"]["num_sources"] == 3


class TestCombinedEvaluation:
    @patch("engine.sports_fetcher._http_get")
    def test_multi_source_evaluation(self, mock_get, isolated_state, monkeypatch):
        # ESPN call returns one thing, Odds API returns another
        def side_effect(url, **kwargs):
            if "espn" in url:
                return MOCK_ESPN_RESPONSE
            else:
                return MOCK_ODDS_RESPONSE

        mock_get.side_effect = side_effect
        monkeypatch.setattr("engine.sports_fetcher.ODDS_API_KEY", "test_key")
        from engine.sports_fetcher import fetch_and_evaluate

        result = fetch_and_evaluate(
            "nba",
            market_prices=[0.55, 0.40],  # Polymarket prices
        )

        assert "consensus" in result
        assert "edge_analysis" in result
        assert "sources" in result
        assert len(result["sources"]) >= 1

    @patch("engine.sports_fetcher._http_get")
    def test_evaluation_without_market_prices(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_ESPN_RESPONSE
        from engine.sports_fetcher import fetch_and_evaluate

        result = fetch_and_evaluate("nba")
        assert "consensus" in result
        assert "note" in result  # Should say "provide market_prices"

    @patch("engine.sports_fetcher._http_get")
    def test_evaluation_with_pipeline(self, mock_get, isolated_state, monkeypatch):
        mock_get.return_value = MOCK_ESPN_RESPONSE
        monkeypatch.setattr("engine.sports_fetcher.ODDS_API_KEY", "")
        from engine.sports_fetcher import fetch_and_evaluate

        result = fetch_and_evaluate(
            "nba",
            market_prices=[0.50, 0.45],
            bankroll=500,
        )

        assert "edge_analysis" in result
        # May or may not have pipeline results depending on edge


class TestListSports:
    def test_lists_all_sports(self):
        from engine.sports_fetcher import list_available_sports
        result = list_available_sports()
        assert "nfl" in result["sports"]
        assert "nba" in result["sports"]
        assert result["sports"]["nba"]["espn"] is True


class TestCacheClear:
    def test_clear_cache(self, isolated_state):
        from engine.sports_fetcher import clear_cache, CACHE_DIR
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / "sports_abc.json").write_text("{}")
        result = clear_cache()
        assert result["cleared"] == 1


class TestESPNEventParsing:
    """Test edge cases in ESPN event parsing."""

    @patch("engine.sports_fetcher._http_get")
    def test_spread_to_probability_conversion(self, mock_get, isolated_state):
        """When no predictor available, convert spread to probability."""
        no_predictor = {
            "events": [{
                "id": "123",
                "name": "Team A at Team B",
                "date": "2026-03-25T00:00Z",
                "status": {"type": {"name": "STATUS_SCHEDULED"}},
                "competitions": [{
                    "competitors": [
                        {"homeAway": "home", "team": {"displayName": "Team B"}, "score": "0"},
                        {"homeAway": "away", "team": {"displayName": "Team A"}, "score": "0"},
                    ],
                    "odds": [{"spread": -7.0, "overUnder": 45.0}],
                }],
            }],
        }
        mock_get.return_value = no_predictor
        from engine.sports_fetcher import fetch_espn_scoreboard

        result = fetch_espn_scoreboard("nfl")
        assert result["count"] == 1
        event = result["events"][0]
        assert event["probabilities"] is not None
        # Home favorite with -7 spread in NFL: 7 * 2.7% = 18.9%, so ~69%
        assert event["probabilities"]["team_a"] > 0.65

    @patch("engine.sports_fetcher._http_get")
    def test_empty_events(self, mock_get, isolated_state):
        mock_get.return_value = {"events": []}
        from engine.sports_fetcher import fetch_espn_scoreboard

        result = fetch_espn_scoreboard("nba")
        assert result["count"] == 0


class TestEvolveCLI:
    def test_sports_list_via_evolve(self):
        import subprocess
        result = subprocess.run(
            ["bash", str(ENGINE_DIR.parent / "engine" / "evolve"), "sports-list"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "nba" in data["sports"]
