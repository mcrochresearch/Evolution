#!/usr/bin/env python3
"""
Tests for weather_fetcher and wallet_poller.

Uses mock HTTP responses since these modules call external APIs.
Tests focus on: caching, parsing, signal generation, error handling.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """Isolate state AND module-level paths for fetcher/poller modules."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    monkeypatch.setenv("EVOLUTION_STATE_DIR", str(state_dir))
    monkeypatch.chdir(tmp_path)

    # Patch module-level paths that were resolved at import time
    import engine.weather_fetcher as wf
    import engine.wallet_poller as wp
    import engine.smart_money as sm
    import engine.risk as risk

    monkeypatch.setattr(wf, "STATE_DIR", state_dir)
    monkeypatch.setattr(wf, "CACHE_DIR", state_dir / "weather_cache")
    monkeypatch.setattr(wp, "STATE_DIR", state_dir)
    monkeypatch.setattr(wp, "POLLER_STATE_FILE", state_dir / "wallet_poller.json")
    monkeypatch.setattr(wp, "CACHE_DIR", state_dir / "wallet_cache")
    monkeypatch.setattr(sm, "STATE_DIR", state_dir)
    monkeypatch.setattr(sm, "WALLET_DB_FILE", state_dir / "smart_money.json")
    monkeypatch.setattr(risk, "STATE_DIR", state_dir)
    monkeypatch.setattr(risk, "RISK_STATE_FILE", state_dir / "risk_state.json")

    return state_dir


# ============================================================================
# WEATHER FETCHER TESTS
# ============================================================================

MOCK_OPENMETEO_RESPONSE = {
    "daily": {
        "time": ["2026-03-25"],
        "temperature_2m_max": [18.5],
        "temperature_2m_min": [8.2],
        "temperature_2m_mean": [13.4],
    },
    "timezone": "Europe/Istanbul",
}


class TestWeatherFetcherParsing:
    """Test parsing of Open-Meteo API responses."""

    @patch("engine.weather_fetcher._http_get")
    def test_fetch_parses_response(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_OPENMETEO_RESPONSE
        from engine.weather_fetcher import fetch_forecast

        result = fetch_forecast(39.93, 32.86, "2026-03-25")

        assert result["temperature_mean"] == 13.4
        assert result["temperature_min"] == 8.2
        assert result["temperature_max"] == 18.5
        assert result["forecast_sigma"] > 0
        assert result["source"] == "open-meteo"

    @patch("engine.weather_fetcher._http_get")
    def test_sigma_from_range(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_OPENMETEO_RESPONSE
        from engine.weather_fetcher import fetch_forecast

        result = fetch_forecast(39.93, 32.86, "2026-03-25")
        assert result["range_sigma"] == round((18.5 - 8.2) / 4, 2)

    @patch("engine.weather_fetcher._http_get")
    def test_mean_computed_from_min_max(self, mock_get, isolated_state):
        """When API doesn't return mean, compute from min/max."""
        mock_get.return_value = {
            "daily": {
                "time": ["2026-04-01"],
                "temperature_2m_max": [20.0],
                "temperature_2m_min": [10.0],
                "temperature_2m_mean": [None],
            },
        }
        from engine.weather_fetcher import fetch_forecast

        result = fetch_forecast(0.0, 0.0, "2026-04-01")  # Different coords to avoid cache
        assert result["temperature_mean"] == 15.0

    @patch("engine.weather_fetcher._http_get")
    def test_api_error_returns_error(self, mock_get, isolated_state):
        mock_get.side_effect = ConnectionError("Network down")
        from engine.weather_fetcher import fetch_forecast

        result = fetch_forecast(10.0, 10.0, "2026-04-02")
        assert "error" in result


class TestWeatherFetcherCaching:
    """Test forecast caching."""

    @patch("engine.weather_fetcher._http_get")
    def test_caches_result(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_OPENMETEO_RESPONSE
        from engine.weather_fetcher import fetch_forecast, _cache_path

        fetch_forecast(39.93, 32.86, "2026-03-25")
        cache_file = _cache_path(39.93, 32.86, "2026-03-25")
        assert cache_file.exists()

    @patch("engine.weather_fetcher._http_get")
    def test_uses_cache_on_second_call(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_OPENMETEO_RESPONSE
        from engine.weather_fetcher import fetch_forecast

        # First call hits API
        fetch_forecast(50.0, 50.0, "2026-03-26")
        first_count = mock_get.call_count
        assert first_count >= 1

        # Second call should use cache
        result = fetch_forecast(50.0, 50.0, "2026-03-26")
        assert mock_get.call_count == first_count  # No new API calls
        assert result["cached"] is True

    def test_clear_cache(self, isolated_state):
        from engine.weather_fetcher import clear_cache, CACHE_DIR

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / "forecast_abc123.json").write_text("{}")
        (CACHE_DIR / "forecast_def456.json").write_text("{}")

        result = clear_cache()
        assert result["cleared"] == 2


class TestWeatherEvaluateWithFetch:
    """Test the combined fetch + evaluate convenience function."""

    @patch("engine.weather_fetcher._http_get")
    def test_evaluate_with_fetch(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_OPENMETEO_RESPONSE
        from engine.weather_fetcher import evaluate_with_fetch

        result = evaluate_with_fetch(
            lat=39.93, lon=32.86, date="2026-03-25",
            bucket_edges=[10, 12, 14, 16],
            market_prices=[0.10, 0.20, 0.30, 0.25, 0.10],
        )

        assert "forecast" in result
        assert "edge_analysis" in result
        assert result["forecast"]["temperature_mean"] == 13.4
        assert "buckets" in result["edge_analysis"]

    @patch("engine.weather_fetcher._http_get")
    def test_evaluate_with_bankroll_runs_pipeline(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_OPENMETEO_RESPONSE
        # Also patch trade_pipeline's state dirs
        import engine.trade_pipeline as tp
        tp_state = isolated_state
        from engine.weather_fetcher import evaluate_with_fetch

        result = evaluate_with_fetch(
            lat=39.93, lon=32.86, date="2026-03-25",
            bucket_edges=[10, 12, 14, 16],
            market_prices=[0.10, 0.20, 0.30, 0.25, 0.10],
            bankroll=500,
        )

        assert "pipeline" in result
        assert "trades_approved" in result["pipeline"]


# ============================================================================
# WALLET POLLER TESTS
# ============================================================================

MOCK_POSITIONS_RESPONSE = [
    {
        "market": "condition_abc123",
        "title": "Will it rain in London?",
        "outcome": "Yes",
        "size": "150",
        "avgPrice": "0.55",
        "currentValue": "165",
        "realizedPnl": "0",
        "createdAt": "2026-03-20T10:00:00Z",
    },
    {
        "market": "condition_def456",
        "title": "Ankara temp > 15C?",
        "outcome": "No",
        "size": "200",
        "avgPrice": "0.40",
        "currentValue": "180",
        "realizedPnl": "-20",
        "createdAt": "2026-03-21T15:00:00Z",
    },
]

MOCK_TRADES_RESPONSE = [
    {"market": "m1", "side": "Yes", "size": "100", "price": "0.50", "timestamp": "2026-03-20T10:00:00Z"},
    {"market": "m2", "side": "No", "size": "50", "price": "0.30", "timestamp": "2026-03-20T11:00:00Z"},
]


class TestWalletPollerParsing:
    """Test parsing of Polymarket API responses."""

    @patch("engine.wallet_poller._http_get")
    def test_fetch_positions_parses(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_POSITIONS_RESPONSE
        from engine.wallet_poller import fetch_wallet_positions

        result = fetch_wallet_positions("0xabc123")

        assert result["count"] == 2
        assert result["positions"][0]["market_id"] == "condition_abc123"
        assert result["positions"][0]["direction"] == "YES"
        assert result["positions"][0]["size"] == 150.0
        assert result["positions"][1]["direction"] == "NO"

    @patch("engine.wallet_poller._http_get")
    def test_fetch_positions_api_error(self, mock_get, isolated_state):
        mock_get.side_effect = ConnectionError("API down")
        from engine.wallet_poller import fetch_wallet_positions

        result = fetch_wallet_positions("0xabc123")
        assert "error" in result

    @patch("engine.wallet_poller._http_get")
    def test_fetch_trades_parses(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_TRADES_RESPONSE
        from engine.wallet_poller import fetch_wallet_trades

        result = fetch_wallet_trades("0xabc123")
        assert result["count"] == 2


class TestWalletPollerNewEntryDetection:
    """Test detection of new/increased positions."""

    @patch("engine.wallet_poller._http_get")
    def test_detects_new_position(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_POSITIONS_RESPONSE
        from engine.wallet_poller import poll_wallet
        from engine.smart_money import add_wallet

        add_wallet("0xtest_whale", initial_data={
            "trades_total": 100, "trades_won": 70,
            "portfolio_value_usd": 200000,
        })

        result = poll_wallet("0xtest_whale")
        assert len(result["new_entries"]) == 2
        assert result["total_positions"] == 2

    @patch("engine.wallet_poller._http_get")
    def test_no_new_entries_on_second_poll(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_POSITIONS_RESPONSE
        from engine.wallet_poller import poll_wallet
        from engine.smart_money import add_wallet

        add_wallet("0xtest", initial_data={
            "trades_total": 100, "trades_won": 70,
            "portfolio_value_usd": 200000,
        })

        poll_wallet("0xtest")
        result = poll_wallet("0xtest")
        assert len(result["new_entries"]) == 0

    @patch("engine.wallet_poller._http_get")
    def test_detects_increased_position(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_POSITIONS_RESPONSE
        from engine.wallet_poller import poll_wallet
        from engine.smart_money import add_wallet

        add_wallet("0xincrease", initial_data={
            "trades_total": 80, "trades_won": 55,
            "portfolio_value_usd": 100000,
        })

        poll_wallet("0xincrease")

        mock_get.return_value = [
            {**MOCK_POSITIONS_RESPONSE[0], "size": "300"},
            MOCK_POSITIONS_RESPONSE[1],
        ]

        result = poll_wallet("0xincrease")
        assert len(result["new_entries"]) == 1
        assert result["new_entries"][0]["new_size"] == 150  # 300 - 150

    @patch("engine.wallet_poller._http_get")
    def test_market_filter(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_POSITIONS_RESPONSE
        from engine.wallet_poller import poll_wallet
        from engine.smart_money import add_wallet

        add_wallet("0xfilter", initial_data={
            "trades_total": 100, "trades_won": 70,
            "portfolio_value_usd": 200000,
        })

        result = poll_wallet("0xfilter", market_filter="condition_abc123")
        assert len(result["new_entries"]) == 1
        assert result["new_entries"][0]["market_id"] == "condition_abc123"


class TestWalletPollerSignalGeneration:
    """Test that polling generates smart money signals."""

    @patch("engine.wallet_poller._http_get")
    def test_whale_generates_signal(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_POSITIONS_RESPONSE
        from engine.wallet_poller import poll_wallet
        from engine.smart_money import add_wallet

        add_wallet("0xsignal_whale", initial_data={
            "trades_total": 100, "trades_won": 72,
            "portfolio_value_usd": 500000,
        })

        result = poll_wallet("0xsignal_whale")
        assert result["signals_generated"] > 0
        assert len(result["signals"]) > 0
        assert result["signals"][0]["type"] == "smart_money_entry"

    @patch("engine.wallet_poller._http_get")
    def test_unknown_wallet_no_signal(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_POSITIONS_RESPONSE
        from engine.wallet_poller import poll_wallet
        from engine.smart_money import add_wallet

        add_wallet("0xnoob", initial_data={
            "trades_total": 5, "trades_won": 2,
            "portfolio_value_usd": 100,
        })

        result = poll_wallet("0xnoob")
        assert result["signals_generated"] == 0


class TestWalletPollerPollAll:
    """Test polling all tracked wallets."""

    @patch("engine.wallet_poller._http_get")
    @patch("engine.wallet_poller.RATE_LIMIT_DELAY", 0)
    def test_poll_all(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_POSITIONS_RESPONSE
        from engine.wallet_poller import poll_all_tracked
        from engine.smart_money import add_wallet

        add_wallet("0xwhale1", initial_data={
            "trades_total": 100, "trades_won": 70,
            "portfolio_value_usd": 200000,
        })
        add_wallet("0xwhale2", initial_data={
            "trades_total": 80, "trades_won": 55,
            "portfolio_value_usd": 100000,
        })

        result = poll_all_tracked()
        assert result["wallets_polled"] == 2
        assert result["total_new_entries"] > 0

    def test_poll_all_no_wallets(self, isolated_state):
        from engine.wallet_poller import poll_all_tracked

        result = poll_all_tracked()
        assert result["wallets_polled"] == 0


class TestWalletPollerDiscover:
    """Test whale discovery."""

    @patch("engine.wallet_poller._http_get")
    def test_discover_finds_whales(self, mock_get, isolated_state):
        mock_get.return_value = [
            {"maker": "0xbigfish", "size": "10000", "price": "0.50"},
            {"maker": "0xbigfish", "size": "8000", "price": "0.60"},
            {"maker": "0xbigfish", "size": "15000", "price": "0.40"},
        ] * 10
        from engine.wallet_poller import discover_whales

        result = discover_whales(min_volume=1000, min_trades=5)
        assert result["qualified"] >= 1
        assert result["candidates"][0]["address"] == "0xbigfish"


class TestWalletPollerStatus:
    """Test poller status reporting."""

    def test_status_empty(self, isolated_state):
        from engine.wallet_poller import get_poller_status

        result = get_poller_status()
        assert result["tracked_wallets"] == 0
        assert result["total_polls"] == 0


class TestWalletPollerState:
    """Test poller state persistence."""

    @patch("engine.wallet_poller._http_get")
    def test_state_persists(self, mock_get, isolated_state):
        mock_get.return_value = MOCK_POSITIONS_RESPONSE
        from engine.wallet_poller import poll_wallet, _load_poller_state
        from engine.smart_money import add_wallet

        add_wallet("0xpersist", initial_data={
            "trades_total": 60, "trades_won": 40,
            "portfolio_value_usd": 50000,
        })

        poll_wallet("0xpersist")

        state = _load_poller_state()
        assert "0xpersist" in state["wallets"]
        assert state["total_polls"] == 1
