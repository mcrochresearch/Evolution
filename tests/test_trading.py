#!/usr/bin/env python3
"""
Tests for the PolyClaw v5 trading infrastructure:
- Kelly criterion position sizing
- Risk management circuit breakers
- Smart money tracker
- Weather edge calculator

These are the modules that would have prevented v1-v4 catastrophes.
"""

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """Run each test with an isolated state directory."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    monkeypatch.setenv("EVOLUTION_STATE_DIR", str(state_dir))
    monkeypatch.chdir(tmp_path)

    # Patch module-level paths resolved at import time
    import engine.risk as risk
    import engine.smart_money as sm
    import engine.trade_pipeline as tp

    monkeypatch.setattr(risk, "STATE_DIR", state_dir)
    monkeypatch.setattr(risk, "RISK_STATE_FILE", state_dir / "risk_state.json")
    monkeypatch.setattr(sm, "STATE_DIR", state_dir)
    monkeypatch.setattr(sm, "WALLET_DB_FILE", state_dir / "smart_money.json")
    monkeypatch.setattr(tp, "STATE_DIR", state_dir)
    monkeypatch.setattr(tp, "PIPELINE_LOG", state_dir / "trade_pipeline.jsonl")

    return state_dir


def run_cmd(module: str, *args):
    """Run an engine module as a subprocess and return parsed output."""
    cmd = [sys.executable, str(ENGINE_DIR / module)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    stdout = result.stdout.strip()
    try:
        return json.loads(stdout) if stdout else {}, result.returncode
    except json.JSONDecodeError:
        return {"raw": stdout, "stderr": result.stderr}, result.returncode


# ============================================================================
# KELLY CRITERION TESTS
# ============================================================================

class TestKellyFractionBinary:
    """Test the core Kelly formula for binary markets."""

    def test_no_edge_returns_zero(self):
        from engine.kelly import kelly_fraction_binary
        # Fair price = true probability → no edge
        assert kelly_fraction_binary(0.5, 0.5) == 0.0

    def test_positive_edge_yes(self):
        from engine.kelly import kelly_fraction_binary
        # True prob 60%, market price 40% → big edge on YES
        f = kelly_fraction_binary(0.60, 0.40)
        assert f > 0  # Positive = bet YES
        assert f < 1  # Never bet more than bankroll

    def test_positive_edge_no(self):
        from engine.kelly import kelly_fraction_binary
        # True prob 30%, market price 70% → edge on NO
        f = kelly_fraction_binary(0.30, 0.70)
        assert f < 0  # Negative = bet NO

    def test_edge_at_extremes(self):
        from engine.kelly import kelly_fraction_binary
        # Near-certain outcome mispriced
        f = kelly_fraction_binary(0.99, 0.50)
        assert f > 0.5  # Should recommend large bet

    def test_invalid_inputs(self):
        from engine.kelly import kelly_fraction_binary
        assert kelly_fraction_binary(0, 0.5) == 0.0
        assert kelly_fraction_binary(1, 0.5) == 0.0
        assert kelly_fraction_binary(0.5, 0) == 0.0
        assert kelly_fraction_binary(0.5, 1) == 0.0
        assert kelly_fraction_binary(-0.1, 0.5) == 0.0

    def test_symmetric_edge(self):
        from engine.kelly import kelly_fraction_binary
        # Same edge magnitude on YES vs NO should give similar absolute fractions
        f_yes = kelly_fraction_binary(0.60, 0.50)
        f_no = kelly_fraction_binary(0.40, 0.50)
        assert abs(abs(f_yes) - abs(f_no)) < 0.01


class TestKellyMulti:
    """Test Kelly for MECE multi-outcome markets (weather buckets)."""

    def test_mece_buckets(self):
        from engine.kelly import kelly_fraction_multi
        # 3 outcomes: true probs sum to 1, prices don't
        fair = [0.3, 0.5, 0.2]
        prices = [0.20, 0.40, 0.15]  # Sum = 0.75, arb gap = 0.25
        fracs = kelly_fraction_multi(fair, prices)
        assert len(fracs) == 3
        assert all(f >= 0 for f in fracs)  # All non-negative for MECE

    def test_no_edge_on_any_bucket(self):
        from engine.kelly import kelly_fraction_multi
        # Prices = fair probs → no edge
        fair = [0.3, 0.5, 0.2]
        fracs = kelly_fraction_multi(fair, fair)
        assert all(f == 0 for f in fracs)

    def test_mismatched_lengths(self):
        from engine.kelly import kelly_fraction_multi
        fracs = kelly_fraction_multi([0.5, 0.5], [0.3])
        assert fracs == [0.0, 0.0]


class TestSizePosition:
    """Test position sizing with all caps and adjustments."""

    def test_basic_sizing(self):
        from engine.kelly import size_position
        result = size_position(0.70, 0.50, 1000)
        assert result["action"] == "BET"
        assert result["direction"] == "YES"
        assert result["position_usd"] > 0
        assert result["position_usd"] <= 50  # MAX_POSITION_USD default

    def test_insufficient_edge_skips(self):
        from engine.kelly import size_position
        # 0.5% edge is below 1% minimum
        result = size_position(0.505, 0.50, 1000)
        assert result["action"] == "SKIP"

    def test_max_position_cap(self):
        from engine.kelly import size_position
        # Huge edge on large bankroll → capped at max
        result = size_position(0.90, 0.50, 100000)
        assert result["position_usd"] <= 50  # Default MAX_POSITION_USD

    def test_custom_max_position(self):
        from engine.kelly import size_position
        result = size_position(0.70, 0.50, 1000, max_position=200)
        assert result["position_usd"] <= 200

    def test_bankroll_percentage_cap(self):
        from engine.kelly import size_position
        # Even with high max, never exceed 10% of bankroll
        result = size_position(0.90, 0.50, 100, max_position=50)
        assert result["position_usd"] <= 10  # 10% of $100

    def test_confidence_reduces_size(self):
        from engine.kelly import size_position
        # Use higher max_position so we're not hitting the cap on both
        full = size_position(0.70, 0.50, 1000, confidence=1.0, max_position=500)
        half = size_position(0.70, 0.50, 1000, confidence=0.5, max_position=500)
        if full["action"] == "BET" and half["action"] == "BET":
            assert half["position_usd"] < full["position_usd"]

    def test_quarter_kelly_default(self):
        from engine.kelly import size_position, DEFAULT_KELLY_FRACTION
        assert DEFAULT_KELLY_FRACTION == 0.25
        result = size_position(0.70, 0.50, 1000)
        assert result.get("kelly_fraction_used") == 0.25

    def test_no_side_returns_skip(self):
        from engine.kelly import size_position
        result = size_position(0.50, 0.50, 1000)
        assert result["action"] == "SKIP"

    def test_expected_profit_positive_when_edge_exists(self):
        from engine.kelly import size_position
        result = size_position(0.70, 0.50, 1000)
        if result["action"] == "BET":
            assert result["expected_profit"] > 0


class TestKellyCLI:
    """Test Kelly module via CLI."""

    def test_size_command(self):
        data, rc = run_cmd("kelly.py", "size", "0.70", "0.50", "1000")
        assert rc == 0
        assert data.get("action") == "BET"
        assert data.get("direction") == "YES"

    def test_simulate_command(self):
        data, rc = run_cmd("kelly.py", "simulate", "0.60", "0.45", "500", "100",
                           "--fraction", "0.25")
        assert rc == 0
        assert "percentiles" in data
        assert "ruin_probability" in data
        assert data["n_bets"] == 100


# ============================================================================
# RISK MANAGEMENT TESTS
# ============================================================================

class TestDrawdown:
    """Test drawdown circuit breaker logic."""

    def test_no_drawdown(self):
        from engine.risk import check_drawdown
        result = check_drawdown(1000, 1000)
        assert result["level"] == "OK"
        assert result["drawdown_pct"] == 0

    def test_warning_level(self):
        from engine.risk import check_drawdown
        result = check_drawdown(1000, 880)  # 12% drawdown
        assert result["level"] == "WARNING"
        assert result["action"] == "REDUCE_SIZE"
        assert result["size_multiplier"] == 0.5

    def test_halt_level(self):
        from engine.risk import check_drawdown
        result = check_drawdown(1000, 780)  # 22% drawdown
        assert result["level"] == "HALT"
        assert result["action"] == "NO_NEW_TRADES"

    def test_emergency_level(self):
        from engine.risk import check_drawdown
        result = check_drawdown(1000, 640)  # 36% drawdown
        assert result["level"] == "EMERGENCY"
        assert result["action"] == "CLOSE_ALL"

    def test_zero_peak(self):
        from engine.risk import check_drawdown
        result = check_drawdown(0, 0)
        assert result["level"] == "OK"


class TestExposure:
    """Test portfolio exposure limit checks."""

    def test_within_limits(self):
        from engine.risk import check_exposure
        positions = [
            {"market_id": "m1", "category": "weather", "position_usd": 10},
            {"market_id": "m2", "category": "sports", "position_usd": 15},
        ]
        result = check_exposure(positions, 1000)
        assert result["can_trade"] is True
        assert len(result["violations"]) == 0

    def test_portfolio_exposure_violation(self):
        from engine.risk import check_exposure
        # 60% of bankroll at risk
        positions = [
            {"market_id": f"m{i}", "category": "weather", "position_usd": 30}
            for i in range(20)
        ]
        result = check_exposure(positions, 1000)
        assert result["can_trade"] is False
        violations = [v for v in result["violations"] if v["type"] == "PORTFOLIO_EXPOSURE"]
        assert len(violations) > 0

    def test_single_market_violation(self):
        from engine.risk import check_exposure
        positions = [
            {"market_id": "m1", "category": "weather", "position_usd": 120},
        ]
        result = check_exposure(positions, 1000)
        assert any(v["type"] == "SINGLE_MARKET" for v in result["violations"])

    def test_category_violation(self):
        from engine.risk import check_exposure
        # 30% in one category
        positions = [
            {"market_id": f"m{i}", "category": "weather", "position_usd": 50}
            for i in range(6)
        ]
        result = check_exposure(positions, 1000)
        assert any(v["type"] == "CATEGORY_EXPOSURE" for v in result["violations"])

    def test_position_count_violation(self):
        from engine.risk import check_exposure, MAX_OPEN_POSITIONS
        positions = [
            {"market_id": f"m{i}", "category": "weather", "position_usd": 1}
            for i in range(MAX_OPEN_POSITIONS + 5)
        ]
        result = check_exposure(positions, 100000)
        assert any(v["type"] == "POSITION_COUNT" for v in result["violations"])

    def test_remaining_capacity(self):
        from engine.risk import check_exposure
        positions = [
            {"market_id": "m1", "category": "weather", "position_usd": 100},
        ]
        result = check_exposure(positions, 1000)
        assert result["remaining_capacity_usd"] == 400  # 50% of 1000 - 100


class TestCanTrade:
    """Test the master trade gate."""

    def test_normal_trade_allowed(self, isolated_state):
        from engine.risk import can_trade
        result = can_trade(
            bankroll=1000,
            positions=[],
            proposed_trade={"market_id": "m1", "category": "weather", "position_usd": 10},
        )
        assert result["allowed"] is True

    def test_halted_blocks_trade(self, isolated_state):
        from engine.risk import can_trade
        state = {"halted": True, "halt_reason": "test halt"}
        result = can_trade(1000, [], {"position_usd": 10}, risk_state=state)
        assert result["allowed"] is False
        assert "halted" in result["reason"].lower()

    def test_low_bankroll_blocks(self, isolated_state):
        from engine.risk import can_trade
        result = can_trade(5, [], {"position_usd": 3})
        assert result["allowed"] is False

    def test_consecutive_losses_block(self, isolated_state):
        from engine.risk import can_trade, MAX_CONSECUTIVE_LOSSES
        state = {
            "halted": False, "halt_reason": None,
            "consecutive_losses": MAX_CONSECUTIVE_LOSSES,
            "peak_bankroll": 1000, "daily_pnl": 0, "weekly_pnl": 0,
        }
        result = can_trade(1000, [], {"position_usd": 10}, risk_state=state)
        assert result["allowed"] is False

    def test_drawdown_reduces_size(self, isolated_state):
        from engine.risk import can_trade
        state = {
            "halted": False, "halt_reason": None,
            "consecutive_losses": 0,
            "peak_bankroll": 1000,
            "daily_pnl": 0, "weekly_pnl": 0,
        }
        # 12% drawdown → WARNING → 50% size reduction
        result = can_trade(
            bankroll=880,
            positions=[],
            proposed_trade={"market_id": "m1", "category": "weather", "position_usd": 20},
            risk_state=state,
        )
        assert result["allowed"] is True
        assert result["adjusted_size"] < 20


class TestRecordTradeResult:
    """Test trade result recording and state updates."""

    def test_winning_trade(self, isolated_state):
        from engine.risk import record_trade_result, load_risk_state
        state = record_trade_result(win=True, pnl=15.0)
        assert state["winning_trades"] == 1
        assert state["consecutive_losses"] == 0
        assert state["daily_pnl"] == 15.0

    def test_losing_streak_triggers_halt(self, isolated_state):
        from engine.risk import record_trade_result, MAX_CONSECUTIVE_LOSSES
        state = None
        for i in range(MAX_CONSECUTIVE_LOSSES):
            state = record_trade_result(win=False, pnl=-5.0, risk_state=state)
        assert state["halted"] is True
        assert state["consecutive_losses"] == MAX_CONSECUTIVE_LOSSES

    def test_win_resets_consecutive_losses(self, isolated_state):
        from engine.risk import record_trade_result
        state = record_trade_result(win=False, pnl=-5.0)
        state = record_trade_result(win=False, pnl=-5.0, risk_state=state)
        assert state["consecutive_losses"] == 2
        state = record_trade_result(win=True, pnl=10.0, risk_state=state)
        assert state["consecutive_losses"] == 0

    def test_daily_reset(self, isolated_state):
        from engine.risk import record_trade_result, reset_daily
        state = record_trade_result(win=False, pnl=-20.0)
        assert state["daily_pnl"] == -20.0
        state = reset_daily(state)
        assert state["daily_pnl"] == 0.0


class TestRiskCLI:
    """Test risk module via CLI."""

    def test_drawdown_command(self):
        data, rc = run_cmd("risk.py", "drawdown", "1000", "880")
        assert rc == 0
        assert data.get("level") == "WARNING"

    def test_check_command(self):
        positions = json.dumps([
            {"market_id": "m1", "category": "weather", "position_usd": 10}
        ])
        data, rc = run_cmd("risk.py", "check", "1000", positions)
        assert rc == 0
        assert data.get("can_trade") is True


# ============================================================================
# SMART MONEY TRACKER TESTS
# ============================================================================

class TestWalletClassification:
    """Test wallet tier classification."""

    def test_whale(self):
        from engine.smart_money import classify_wallet
        w = {"trades_total": 100, "trades_won": 70, "portfolio_value_usd": 200000}
        assert classify_wallet(w) == "whale"

    def test_shark(self):
        from engine.smart_money import classify_wallet
        w = {"trades_total": 60, "trades_won": 42, "portfolio_value_usd": 50000}
        assert classify_wallet(w) == "shark"

    def test_smart(self):
        from engine.smart_money import classify_wallet
        w = {"trades_total": 50, "trades_won": 35, "portfolio_value_usd": 5000}
        assert classify_wallet(w) == "smart"

    def test_promising(self):
        from engine.smart_money import classify_wallet
        w = {"trades_total": 40, "trades_won": 25, "portfolio_value_usd": 1000}
        assert classify_wallet(w) == "promising"

    def test_unknown_insufficient_data(self):
        from engine.smart_money import classify_wallet
        w = {"trades_total": 5, "trades_won": 4, "portfolio_value_usd": 1000000}
        assert classify_wallet(w) == "unknown"

    def test_unknown_low_wr(self):
        from engine.smart_money import classify_wallet
        w = {"trades_total": 100, "trades_won": 40, "portfolio_value_usd": 500000}
        assert classify_wallet(w) == "unknown"


class TestWalletTracking:
    """Test wallet add/profile/update operations."""

    def test_add_wallet(self, isolated_state):
        from engine.smart_money import add_wallet
        w = add_wallet("0xabc123", alias="TestWhale")
        assert w["address"] == "0xabc123"
        assert w["alias"] == "TestWhale"
        assert w["tier"] == "unknown"

    def test_add_with_initial_data(self, isolated_state):
        from engine.smart_money import add_wallet
        w = add_wallet("0xabc123", initial_data={
            "trades_total": 100, "trades_won": 70,
            "portfolio_value_usd": 200000,
        })
        assert w["tier"] == "whale"
        assert w["win_rate"] == 0.7

    def test_profile_nonexistent(self, isolated_state):
        from engine.smart_money import profile_wallet
        result = profile_wallet("0xnothing")
        assert "error" in result

    def test_profile_existing(self, isolated_state):
        from engine.smart_money import add_wallet, profile_wallet
        add_wallet("0xabc", initial_data={"trades_total": 60, "trades_won": 40, "portfolio_value_usd": 50000})
        profile = profile_wallet("0xabc")
        assert profile["is_smart_money"] is True

    def test_record_outcome_updates_stats(self, isolated_state):
        from engine.smart_money import add_wallet, record_trade_outcome
        add_wallet("0xtest", initial_data={"trades_total": 50, "trades_won": 35})
        result = record_trade_outcome("0xtest", "market1", won=True)
        assert result["updated"] is True
        assert result["trades_total"] == 51


class TestSmartMoneySignals:
    """Test signal generation from wallet activity."""

    def test_signal_from_smart_money(self, isolated_state):
        from engine.smart_money import add_wallet, record_wallet_entry
        add_wallet("0xwhale", initial_data={
            "trades_total": 100, "trades_won": 70,
            "portfolio_value_usd": 200000,
        })
        result = record_wallet_entry("0xwhale", "market1", "YES", 5000, 0.55, "Will it rain?")
        assert result["signal"] is not None
        assert result["signal"]["type"] == "smart_money_entry"
        assert result["signal"]["signal_strength"] > 0

    def test_no_signal_from_unknown(self, isolated_state):
        from engine.smart_money import add_wallet, record_wallet_entry
        add_wallet("0xnoob", initial_data={"trades_total": 5, "trades_won": 2})
        result = record_wallet_entry("0xnoob", "market1", "YES", 100, 0.50)
        assert result["signal"] is None

    def test_signal_cooldown(self, isolated_state):
        from engine.smart_money import add_wallet, record_wallet_entry
        add_wallet("0xwhale", initial_data={
            "trades_total": 100, "trades_won": 70,
            "portfolio_value_usd": 200000,
        })
        r1 = record_wallet_entry("0xwhale", "market1", "YES", 5000, 0.55)
        assert r1["signal"] is not None
        # Second entry on same market within cooldown → no new signal
        r2 = record_wallet_entry("0xwhale", "market1", "YES", 3000, 0.60)
        assert r2["signal"] is None


class TestMarketEnrichment:
    """Test smart money enrichment for markets."""

    def test_no_smart_money(self, isolated_state):
        from engine.smart_money import enrich_market
        result = enrich_market("market1")
        assert result["smart_money_present"] is False
        assert result["conviction_boost"] == 0.0

    def test_with_smart_money(self, isolated_state):
        from engine.smart_money import add_wallet, record_wallet_entry, enrich_market
        add_wallet("0xwhale", initial_data={
            "trades_total": 100, "trades_won": 70,
            "portfolio_value_usd": 200000,
        })
        record_wallet_entry("0xwhale", "market1", "YES", 5000, 0.55)
        result = enrich_market("market1")
        assert result["smart_money_present"] is True
        assert result["conviction_boost"] > 0
        assert result["dominant_direction"] == "YES"


# ============================================================================
# WEATHER EDGE CALCULATOR TESTS
# ============================================================================

class TestNormalCDF:
    """Test the normal CDF implementation."""

    def test_standard_normal_at_zero(self):
        from engine.weather_edge import normal_cdf
        assert abs(normal_cdf(0, 0, 1) - 0.5) < 0.001

    def test_standard_normal_at_negative(self):
        from engine.weather_edge import normal_cdf
        assert normal_cdf(-3, 0, 1) < 0.01

    def test_standard_normal_at_positive(self):
        from engine.weather_edge import normal_cdf
        assert normal_cdf(3, 0, 1) > 0.99

    def test_shifted_mean(self):
        from engine.weather_edge import normal_cdf
        # CDF at mean should be 0.5
        assert abs(normal_cdf(10, 10, 2) - 0.5) < 0.001

    def test_zero_sigma(self):
        from engine.weather_edge import normal_cdf
        assert normal_cdf(5, 3, 0) == 1.0
        assert normal_cdf(2, 3, 0) == 0.0


class TestBucketProbability:
    """Test temperature bucket probability computation."""

    def test_total_probability_sums_to_one(self):
        from engine.weather_edge import compute_bucket_probabilities
        buckets = compute_bucket_probabilities(15.0, 2.0, [10, 12, 14, 16, 18, 20])
        total = sum(b["probability"] for b in buckets)
        assert abs(total - 1.0) < 0.001

    def test_peak_at_forecast(self):
        from engine.weather_edge import compute_bucket_probabilities
        buckets = compute_bucket_probabilities(15.0, 1.5, [13, 14, 15, 16, 17])
        # The bucket containing the forecast mean should have highest probability
        probs = [(b["label"], b["probability"]) for b in buckets]
        # 15-16 bucket contains the mean
        bucket_15_16 = [b for b in buckets if b["low"] == 15 and b["high"] == 16]
        assert len(bucket_15_16) == 1
        assert bucket_15_16[0]["probability"] > 0.2

    def test_wide_uncertainty_flattens_distribution(self):
        from engine.weather_edge import compute_bucket_probabilities
        # Use wider bucket range so tail buckets don't dominate with high sigma
        narrow = compute_bucket_probabilities(15.0, 1.0, [10, 12, 14, 15, 16, 18, 20])
        wide = compute_bucket_probabilities(15.0, 5.0, [10, 12, 14, 15, 16, 18, 20])
        # With wide uncertainty, the peak interior bucket should have lower probability
        # Exclude the open-ended tail buckets (first and last) which grow with sigma
        narrow_interior = [b["probability"] for b in narrow if b["low"] != float("-inf") and b["high"] != float("inf")]
        wide_interior = [b["probability"] for b in wide if b["low"] != float("-inf") and b["high"] != float("inf")]
        assert max(wide_interior) < max(narrow_interior)

    def test_empty_edges(self):
        from engine.weather_edge import compute_bucket_probabilities
        assert compute_bucket_probabilities(15.0, 2.0, []) == []


class TestWeatherEdge:
    """Test the full weather edge computation pipeline."""

    def test_underpriced_bucket_detected(self):
        from engine.weather_edge import compute_weather_edge
        # Forecast: 15°C, sigma 1.5°C
        # Bucket 14-16 should be ~50% but priced at 20%
        result = compute_weather_edge(
            forecast_mean=15.0,
            days_ahead=1,
            bucket_edges=[12, 14, 16, 18],
            market_prices=[0.05, 0.20, 0.50, 0.15, 0.05],
        )
        assert "error" not in result
        actionable = result["actionable_trades"]
        # The 14-16 bucket should be flagged as underpriced
        buy_yes = [a for a in actionable if a["action"] == "BUY_YES"]
        assert len(buy_yes) > 0

    def test_no_edge_when_fairly_priced(self):
        from engine.weather_edge import compute_weather_edge, compute_bucket_probabilities
        # Set prices = fair probabilities → no edge
        buckets = compute_bucket_probabilities(15.0, 1.2, [13, 14, 15, 16, 17])
        fair_prices = [b["probability"] for b in buckets]
        result = compute_weather_edge(15.0, 1, [13, 14, 15, 16, 17], fair_prices)
        assert result["actionable_count"] == 0

    def test_structural_arb_detection(self):
        from engine.weather_edge import compute_weather_edge
        # Prices sum to 0.85 → 15% arb gap
        result = compute_weather_edge(
            forecast_mean=15.0, days_ahead=1,
            bucket_edges=[13, 15, 17],
            market_prices=[0.15, 0.30, 0.25, 0.15],
        )
        assert result["has_structural_arb"] is True
        assert result["arb_gap"] > 0.10

    def test_price_count_mismatch_error(self):
        from engine.weather_edge import compute_weather_edge
        result = compute_weather_edge(15.0, 1, [13, 15], [0.3, 0.7])
        assert "error" in result

    def test_confidence_set_correctly(self):
        from engine.weather_edge import compute_weather_edge, CONFIDENCE_WEATHER
        result = compute_weather_edge(15.0, 1, [13, 15, 17],
                                       [0.10, 0.30, 0.40, 0.10])
        assert result["confidence"] == CONFIDENCE_WEATHER

    def test_days_ahead_affects_sigma(self):
        from engine.weather_edge import get_forecast_uncertainty
        sigma_0 = get_forecast_uncertainty(0)
        sigma_7 = get_forecast_uncertainty(7)
        assert sigma_7 > sigma_0  # Further out = more uncertain


class TestWeatherScan:
    """Test scanning multiple weather markets."""

    def test_scan_finds_opportunities(self):
        from engine.weather_edge import scan_weather_markets
        markets = [
            {
                "market_id": "ankara-temp",
                "title": "Ankara temperature March 25",
                "lat": 39.93, "lon": 32.86,
                "date": "2026-03-25",
                "forecast_mean": 13.0,
                "bucket_edges": [10, 11, 12, 13, 14, 15],
                "market_prices": [0.05, 0.05, 0.15, 0.30, 0.20, 0.10, 0.05],
            }
        ]
        result = scan_weather_markets(markets)
        assert result["total_scanned"] == 1
        assert result["actionable"] >= 0  # May or may not find edge

    def test_scan_skips_missing_forecast(self):
        from engine.weather_edge import scan_weather_markets
        markets = [
            {
                "market_id": "no-forecast",
                "date": "2026-03-25",
                "bucket_edges": [10, 15],
                "market_prices": [0.3, 0.4, 0.3],
            }
        ]
        result = scan_weather_markets(markets)
        assert result["skipped"] == 1


class TestWeatherCLI:
    """Test weather edge module via CLI."""

    def test_edge_command(self):
        edges = json.dumps([13, 15, 17])
        prices = json.dumps([0.10, 0.30, 0.40, 0.10])
        data, rc = run_cmd("weather_edge.py", "edge", "15.0", "1", edges, prices)
        assert rc == 0
        assert "buckets" in data
        assert "actionable_count" in data


# ============================================================================
# INTEGRATION TESTS — Modules working together
# ============================================================================

class TestKellyRiskIntegration:
    """Test Kelly sizing feeding into risk management."""

    def test_kelly_respects_risk_limits(self, isolated_state):
        from engine.kelly import size_position
        from engine.risk import can_trade

        # Kelly says bet $30
        sizing = size_position(0.70, 0.50, 500, max_position=100)
        assert sizing["action"] == "BET"

        # Risk engine approves (within limits)
        trade = {
            "market_id": "m1",
            "category": "weather",
            "position_usd": sizing["position_usd"],
        }
        gate = can_trade(500, [], trade)
        assert gate["allowed"] is True

    def test_kelly_blocked_by_drawdown(self, isolated_state):
        from engine.kelly import size_position
        from engine.risk import can_trade

        sizing = size_position(0.70, 0.50, 500, max_position=100)
        trade = {
            "market_id": "m1",
            "category": "weather",
            "position_usd": sizing["position_usd"],
        }
        # 25% drawdown → halt
        state = {
            "halted": False, "halt_reason": None,
            "consecutive_losses": 0,
            "peak_bankroll": 1000,
            "daily_pnl": 0, "weekly_pnl": 0,
        }
        gate = can_trade(750, [], trade, risk_state=state)
        # 25% drawdown from 1000 → HALT
        assert gate["allowed"] is False


class TestWeatherKellyIntegration:
    """Test weather edge → Kelly sizing pipeline."""

    def test_weather_edge_to_kelly_sizing(self):
        from engine.weather_edge import compute_weather_edge
        from engine.kelly import size_position

        result = compute_weather_edge(
            forecast_mean=15.0, days_ahead=1,
            bucket_edges=[12, 14, 16, 18],
            market_prices=[0.05, 0.15, 0.50, 0.20, 0.05],
        )

        # For each actionable trade, run through Kelly
        for trade in result.get("actionable_trades", []):
            if trade["action"] == "BUY_YES":
                sizing = size_position(
                    trade["probability"], trade["market_price"],
                    bankroll=500, confidence=result["confidence"],
                )
                # Should either BET or SKIP — never error
                assert sizing["action"] in ("BET", "SKIP")


class TestSmartMoneyEnrichmentIntegration:
    """Test smart money signals enriching weather trades."""

    def test_enrichment_boosts_conviction(self, isolated_state):
        from engine.smart_money import add_wallet, record_wallet_entry, enrich_market
        from engine.kelly import size_position

        # Set up smart money wallet
        add_wallet("0xweather_whale", initial_data={
            "trades_total": 100, "trades_won": 72,
            "portfolio_value_usd": 300000,
        })
        record_wallet_entry("0xweather_whale", "ankara-temp", "YES", 10000, 0.55)

        enrichment = enrich_market("ankara-temp")
        assert enrichment["smart_money_present"] is True

        # Size with and without conviction boost
        base = size_position(0.65, 0.50, 500, confidence=0.85)
        boosted = size_position(0.65, 0.50, 500,
                                confidence=min(0.85 + enrichment["conviction_boost"], 1.0))

        if base["action"] == "BET" and boosted["action"] == "BET":
            assert boosted["position_usd"] >= base["position_usd"]


# ============================================================================
# TRADE PIPELINE TESTS — Full wired integration
# ============================================================================

class TestTradePipelineEvaluate:
    """Test the full evaluate pipeline: signal → enrich → kelly → risk."""

    def test_good_signal_produces_trade(self, isolated_state):
        from engine.trade_pipeline import evaluate_signal
        from engine.risk import save_risk_state, default_risk_state

        # Set up risk state with bankroll
        rs = default_risk_state()
        rs["current_bankroll"] = 500
        save_risk_state(rs)

        result = evaluate_signal({
            "market_id": "weather-ankara",
            "category": "weather",
            "fair_prob": 0.70,
            "market_price": 0.50,
            "bankroll": 500,
        })

        assert result["action"] == "TRADE"
        assert result["position_usd"] > 0
        assert result["direction"] == "YES"
        assert len(result["stages"]) == 4  # SIGNAL, ENRICH, SIZE, RISK_GATE
        assert all(s["status"] != "BLOCKED" for s in result["stages"])

    def test_no_edge_skips(self, isolated_state):
        from engine.trade_pipeline import evaluate_signal

        result = evaluate_signal({
            "market_id": "no-edge",
            "category": "weather",
            "fair_prob": 0.50,
            "market_price": 0.50,
            "bankroll": 500,
        })

        assert result["action"] == "SKIP"

    def test_low_confidence_blocked(self, isolated_state):
        from engine.trade_pipeline import evaluate_signal

        result = evaluate_signal({
            "market_id": "low-conf",
            "category": "weather",
            "fair_prob": 0.60,
            "market_price": 0.50,
            "confidence": 0.3,  # Below MIN_CONFIDENCE_TO_TRADE
            "bankroll": 500,
        })

        assert result["action"] == "SKIP"
        assert "confidence" in result["reason"].lower()

    def test_risk_halted_blocks_trade(self, isolated_state):
        from engine.trade_pipeline import evaluate_signal
        from engine.risk import save_risk_state, default_risk_state

        rs = default_risk_state()
        rs["current_bankroll"] = 500
        rs["halted"] = True
        rs["halt_reason"] = "5 consecutive losses"
        save_risk_state(rs)

        result = evaluate_signal({
            "market_id": "halted-test",
            "category": "weather",
            "fair_prob": 0.80,
            "market_price": 0.50,
            "bankroll": 500,
        })

        assert result["action"] == "BLOCKED"

    def test_smart_money_enrichment_wired(self, isolated_state):
        from engine.trade_pipeline import evaluate_signal
        from engine.smart_money import add_wallet, record_wallet_entry

        add_wallet("0xwhale", initial_data={
            "trades_total": 100, "trades_won": 70,
            "portfolio_value_usd": 200000,
        })
        record_wallet_entry("0xwhale", "enriched-market", "YES", 5000, 0.55)

        result = evaluate_signal({
            "market_id": "enriched-market",
            "category": "weather",
            "fair_prob": 0.70,
            "market_price": 0.50,
            "bankroll": 500,
        })

        # Check enrichment stage ran
        enrich_stage = [s for s in result["stages"] if s["stage"] == "ENRICH"][0]
        assert enrich_stage["smart_money_present"] is True
        assert enrich_stage["status"] == "BOOST"

    def test_pipeline_logs_events(self, isolated_state):
        from engine.trade_pipeline import evaluate_signal, get_pipeline_history

        evaluate_signal({
            "market_id": "log-test",
            "category": "weather",
            "fair_prob": 0.70,
            "market_price": 0.50,
            "bankroll": 500,
        })

        history = get_pipeline_history()
        assert len(history) >= 1
        assert history[-1]["market_id"] == "log-test"


class TestTradePipelineWeather:
    """Test the weather convenience pipeline."""

    def test_weather_market_evaluation(self, isolated_state):
        from engine.trade_pipeline import evaluate_weather_market

        result = evaluate_weather_market(
            forecast_mean=15.0,
            days_ahead=1,
            bucket_edges=[12, 14, 16, 18],
            market_prices=[0.05, 0.15, 0.50, 0.20, 0.05],
            bankroll=500,
        )

        assert "weather_analysis" in result
        assert "pipeline_results" in result
        assert result["weather_analysis"]["forecast_mean"] == 15.0
        assert result["trades_approved"] >= 0
        assert result["trades_skipped"] >= 0


class TestTradePipelineStatus:
    """Test pipeline status reporting."""

    def test_status_returns_all_subsystems(self, isolated_state):
        from engine.trade_pipeline import get_pipeline_status

        status = get_pipeline_status()

        assert status["pipeline_operational"] is True
        assert "risk" in status
        assert "smart_money" in status
        assert "bankroll" in status


class TestTradePipelineCLI:
    """Test pipeline CLI commands."""

    def test_evaluate_cli(self, isolated_state):
        signal = json.dumps({
            "market_id": "cli-test",
            "category": "weather",
            "fair_prob": 0.70,
            "market_price": 0.50,
            "bankroll": 500,
        })
        data, rc = run_cmd("trade_pipeline.py", "evaluate", signal)
        assert rc == 0
        assert data.get("action") in ("TRADE", "SKIP", "BLOCKED")

    def test_status_cli(self, isolated_state):
        data, rc = run_cmd("trade_pipeline.py", "status")
        assert rc == 0
        assert data.get("pipeline_operational") is True


class TestEvolveCLIWiring:
    """Test that trading commands are wired into the evolve CLI."""

    def test_kelly_size_via_evolve(self):
        result = subprocess.run(
            ["bash", str(ENGINE_DIR.parent / "engine" / "evolve"), "kelly-size", "0.70", "0.50", "1000"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("action") == "BET"

    def test_risk_drawdown_via_evolve(self):
        result = subprocess.run(
            ["bash", str(ENGINE_DIR.parent / "engine" / "evolve"), "risk-drawdown", "1000", "880"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("level") == "WARNING"

    def test_weather_edge_via_evolve(self):
        result = subprocess.run(
            ["bash", str(ENGINE_DIR.parent / "engine" / "evolve"), "weather-edge",
             "15.0", "1", json.dumps([13, 15, 17]), json.dumps([0.10, 0.30, 0.40, 0.10])],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "buckets" in data
