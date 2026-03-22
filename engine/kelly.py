#!/usr/bin/env python3
"""
KELLY CRITERION POSITION SIZING — The math that keeps you alive.

Implements fractional Kelly criterion for Polymarket prediction markets.
Handles binary outcomes (YES/NO), multi-outcome (MECE buckets like weather),
and portfolio-level Kelly with correlation adjustments.

The core insight: Kelly tells you HOW MUCH to bet, not WHETHER to bet.
Edge detection is upstream. This module assumes you have an edge and sizes it.

Usage:
    python engine/kelly.py size <fair_prob> <market_prob> <bankroll> [--fraction 0.25]
    python engine/kelly.py multi <probs_json> <prices_json> <bankroll> [--fraction 0.25]
    python engine/kelly.py portfolio <positions_json> <bankroll>
    python engine/kelly.py simulate <fair_prob> <market_prob> <bankroll> <n_bets> [--fraction 0.25]
"""

import json
import math
import os
import sys
from pathlib import Path

try:
    from engine.stats import now
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now

# --- Constants ---
DEFAULT_KELLY_FRACTION = 0.25   # Quarter-Kelly: industry standard for noisy edges
MIN_EDGE_BPS = 100             # 1% minimum edge to even consider a bet
MAX_POSITION_PCT = 0.10         # Never risk more than 10% of bankroll on one trade
MIN_POSITION_USD = 1.0          # Minimum $1 position (Polymarket minimum)
MAX_POSITION_USD = 50.0         # User-defined cap from v5 postmortem
CONFIDENCE_DECAY = 0.85         # Reduce Kelly when confidence < 1.0


def kelly_fraction_binary(fair_prob: float, market_price: float) -> float:
    """Compute Kelly fraction for a binary YES/NO market.

    Args:
        fair_prob: Your estimated true probability of YES (0-1).
        market_price: Current market price for YES (0-1).

    Returns:
        Optimal Kelly fraction of bankroll to bet (can be negative = bet NO).
        Returns 0.0 if no edge exists.

    The formula:
        f* = (p * b - q) / b
    where:
        p = true probability of winning
        q = 1 - p
        b = odds received (payout per $1 wagered) = (1 - market_price) / market_price for YES
    """
    if not (0 < fair_prob < 1) or not (0 < market_price < 1):
        return 0.0

    # Check YES side
    p = fair_prob
    q = 1.0 - p
    b_yes = (1.0 - market_price) / market_price  # payout ratio for YES

    f_yes = (p * b_yes - q) / b_yes if b_yes > 0 else 0.0

    # Check NO side
    p_no = 1.0 - fair_prob
    q_no = fair_prob
    market_no = 1.0 - market_price
    b_no = (1.0 - market_no) / market_no if market_no > 0 else 0.0

    f_no = (p_no * b_no - q_no) / b_no if b_no > 0 else 0.0

    # Return the better side (positive = YES, negative = NO)
    if f_yes > 0 and f_yes >= f_no:
        return f_yes
    elif f_no > 0:
        return -f_no  # Negative signals bet NO
    return 0.0


def kelly_fraction_multi(fair_probs: list, market_prices: list) -> list:
    """Compute Kelly fractions for MECE multi-outcome markets (e.g., weather buckets).

    For mutually exclusive, collectively exhaustive outcomes where sum(fair_probs) ≈ 1.0
    and sum(market_prices) may differ from 1.0 (that's the arb).

    Args:
        fair_probs: List of true probabilities for each outcome.
        market_prices: List of market prices for each outcome.

    Returns:
        List of Kelly fractions per outcome (positive = buy, 0 = skip).
    """
    if len(fair_probs) != len(market_prices):
        return [0.0] * len(fair_probs)

    fractions = []
    for fp, mp in zip(fair_probs, market_prices):
        if fp <= 0 or mp <= 0 or mp >= 1:
            fractions.append(0.0)
            continue
        # Each outcome is effectively a binary bet
        f = kelly_fraction_binary(fp, mp)
        fractions.append(max(f, 0.0))  # Only buy underpriced outcomes in MECE

    return fractions


def size_position(
    fair_prob: float,
    market_price: float,
    bankroll: float,
    kelly_frac: float = DEFAULT_KELLY_FRACTION,
    confidence: float = 1.0,
    max_position: float = MAX_POSITION_USD,
) -> dict:
    """Compute the actual position size in dollars.

    Applies:
    1. Raw Kelly fraction
    2. Fractional Kelly (default 25% — reduces variance by 75%)
    3. Confidence decay (reduce size when signal confidence < 1.0)
    4. Hard caps: max % of bankroll, max USD, min USD

    Args:
        fair_prob: Your estimated true probability.
        market_price: Current market price.
        bankroll: Total available capital.
        kelly_frac: Fraction of full Kelly to use (0.25 = quarter Kelly).
        confidence: Signal confidence (0-1). Scales position down.
        max_position: Hard USD cap per trade.

    Returns:
        Dict with sizing details and the recommended position.
    """
    raw_kelly = kelly_fraction_binary(fair_prob, market_price)
    direction = "YES" if raw_kelly >= 0 else "NO"
    abs_kelly = abs(raw_kelly)

    # Edge in basis points
    if direction == "YES":
        edge = fair_prob - market_price
    else:
        edge = (1 - fair_prob) - (1 - market_price)

    edge_bps = edge * 10000

    # No edge or insufficient edge
    if abs_kelly == 0 or abs(edge_bps) < MIN_EDGE_BPS:
        return {
            "action": "SKIP",
            "reason": f"Insufficient edge ({edge_bps:.0f} bps, need {MIN_EDGE_BPS})",
            "edge_bps": round(edge_bps, 1),
            "raw_kelly": round(raw_kelly, 4),
            "position_usd": 0.0,
            "direction": direction,
        }

    # Apply fractional Kelly
    adj_kelly = abs_kelly * kelly_frac

    # Apply confidence decay
    if confidence < 1.0:
        adj_kelly *= max(confidence, 0.1) ** CONFIDENCE_DECAY

    # Compute dollar amount
    position_usd = bankroll * adj_kelly

    # Apply caps
    max_bankroll_pct = bankroll * MAX_POSITION_PCT
    position_usd = min(position_usd, max_bankroll_pct, max_position)
    position_usd = max(position_usd, 0.0)

    # Below minimum
    if position_usd < MIN_POSITION_USD:
        return {
            "action": "SKIP",
            "reason": f"Position too small (${position_usd:.2f} < ${MIN_POSITION_USD})",
            "edge_bps": round(edge_bps, 1),
            "raw_kelly": round(raw_kelly, 4),
            "position_usd": 0.0,
            "direction": direction,
        }

    # Compute expected value
    if direction == "YES":
        ev_per_dollar = fair_prob * (1.0 / market_price - 1) - (1 - fair_prob)
    else:
        mp_no = 1.0 - market_price
        ev_per_dollar = (1 - fair_prob) * (1.0 / mp_no - 1) - fair_prob

    expected_profit = position_usd * ev_per_dollar

    return {
        "action": "BET",
        "direction": direction,
        "position_usd": round(position_usd, 2),
        "shares": round(position_usd / (market_price if direction == "YES" else 1 - market_price), 2),
        "edge_bps": round(edge_bps, 1),
        "raw_kelly": round(raw_kelly, 4),
        "adj_kelly": round(adj_kelly, 4),
        "kelly_fraction_used": kelly_frac,
        "confidence": confidence,
        "expected_profit": round(expected_profit, 2),
        "max_loss": round(position_usd, 2),
        "bankroll_pct": round(position_usd / bankroll * 100, 2) if bankroll > 0 else 0,
        "fair_prob": fair_prob,
        "market_price": market_price,
    }


def size_multi_position(
    fair_probs: list,
    market_prices: list,
    bankroll: float,
    kelly_frac: float = DEFAULT_KELLY_FRACTION,
    confidence: float = 1.0,
    max_total_position: float = MAX_POSITION_USD,
) -> dict:
    """Size positions across a MECE multi-outcome market (weather buckets).

    Distributes capital across underpriced outcomes proportionally to Kelly fractions.
    Total spend capped at max_total_position.

    Returns dict with per-outcome sizing and aggregate stats.
    """
    kelly_fracs = kelly_fraction_multi(fair_probs, market_prices)

    positions = []
    total_kelly = sum(abs(f) for f in kelly_fracs)

    for i, (fp, mp, kf) in enumerate(zip(fair_probs, market_prices, kelly_fracs)):
        if kf <= 0 or mp <= 0 or mp >= 1:
            positions.append({
                "outcome_idx": i,
                "action": "SKIP",
                "position_usd": 0.0,
                "fair_prob": fp,
                "market_price": mp,
            })
            continue

        # Proportional allocation within the total budget
        if total_kelly > 0:
            weight = kf / total_kelly
        else:
            weight = 0

        budget = max_total_position * weight
        result = size_position(fp, mp, bankroll, kelly_frac, confidence, max_position=budget)
        result["outcome_idx"] = i
        positions.append(result)

    total_spent = sum(p.get("position_usd", 0) for p in positions)
    total_ev = sum(p.get("expected_profit", 0) for p in positions)
    active = [p for p in positions if p.get("action") == "BET"]

    return {
        "positions": positions,
        "active_count": len(active),
        "total_position_usd": round(total_spent, 2),
        "total_expected_profit": round(total_ev, 2),
        "bankroll_pct": round(total_spent / bankroll * 100, 2) if bankroll > 0 else 0,
        "mece_sum_fair": round(sum(fair_probs), 4),
        "mece_sum_market": round(sum(market_prices), 4),
        "arb_gap": round(1.0 - sum(market_prices), 4),
    }


def simulate_kelly(
    fair_prob: float,
    market_price: float,
    bankroll: float,
    n_bets: int,
    kelly_frac: float = DEFAULT_KELLY_FRACTION,
    n_simulations: int = 1000,
) -> dict:
    """Monte Carlo simulation of Kelly betting outcomes.

    Runs n_simulations paths of n_bets each to show the distribution
    of terminal bankrolls. This is how you validate your edge BEFORE
    risking real money.

    Returns percentile distribution and ruin probability.
    """
    import random

    raw_kelly = kelly_fraction_binary(fair_prob, market_price)
    direction = "YES" if raw_kelly >= 0 else "NO"
    abs_kelly = abs(raw_kelly) * kelly_frac

    if abs_kelly <= 0:
        return {"error": "No edge to simulate", "raw_kelly": raw_kelly}

    terminals = []
    ruin_count = 0
    max_drawdowns = []

    for _ in range(n_simulations):
        bal = bankroll
        peak = bankroll

        for _ in range(n_bets):
            bet_size = bal * min(abs_kelly, MAX_POSITION_PCT)
            bet_size = min(bet_size, MAX_POSITION_USD)

            if bet_size < MIN_POSITION_USD:
                break  # Effectively ruined

            # Simulate outcome
            if direction == "YES":
                win_prob = fair_prob
                payout = bet_size * (1.0 - market_price) / market_price
            else:
                win_prob = 1.0 - fair_prob
                mp_no = 1.0 - market_price
                payout = bet_size * (1.0 - mp_no) / mp_no

            if random.random() < win_prob:
                bal += payout
            else:
                bal -= bet_size

            peak = max(peak, bal)

        max_dd = (peak - bal) / peak if peak > 0 else 0
        max_drawdowns.append(max_dd)
        terminals.append(bal)

        if bal < MIN_POSITION_USD:
            ruin_count += 1

    terminals.sort()
    n = len(terminals)

    return {
        "n_simulations": n_simulations,
        "n_bets": n_bets,
        "kelly_fraction": kelly_frac,
        "direction": direction,
        "edge_bps": round((fair_prob - market_price) * 10000, 1),
        "starting_bankroll": bankroll,
        "percentiles": {
            "p5": round(terminals[int(n * 0.05)], 2),
            "p25": round(terminals[int(n * 0.25)], 2),
            "p50": round(terminals[int(n * 0.50)], 2),
            "p75": round(terminals[int(n * 0.75)], 2),
            "p95": round(terminals[int(n * 0.95)], 2),
        },
        "mean": round(sum(terminals) / n, 2),
        "ruin_probability": round(ruin_count / n, 4),
        "median_max_drawdown": round(sorted(max_drawdowns)[n // 2], 4),
        "profitable_pct": round(sum(1 for t in terminals if t > bankroll) / n * 100, 1),
    }


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "size":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: size <fair_prob> <market_prob> <bankroll> [--fraction F]"}))
                sys.exit(1)
            fair_prob = float(sys.argv[2])
            market_price = float(sys.argv[3])
            bankroll = float(sys.argv[4])
            frac = DEFAULT_KELLY_FRACTION
            if "--fraction" in sys.argv:
                idx = sys.argv.index("--fraction")
                frac = float(sys.argv[idx + 1])
            result = size_position(fair_prob, market_price, bankroll, frac)
            print(json.dumps(result, indent=2))

        elif cmd == "multi":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: multi <probs_json> <prices_json> <bankroll> [--fraction F]"}))
                sys.exit(1)
            fair_probs = json.loads(sys.argv[2])
            market_prices = json.loads(sys.argv[3])
            bankroll = float(sys.argv[4])
            frac = DEFAULT_KELLY_FRACTION
            if "--fraction" in sys.argv:
                idx = sys.argv.index("--fraction")
                frac = float(sys.argv[idx + 1])
            result = size_multi_position(fair_probs, market_prices, bankroll, frac)
            print(json.dumps(result, indent=2))

        elif cmd == "portfolio":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: portfolio <positions_json> <bankroll>"}))
                sys.exit(1)
            positions = json.loads(sys.argv[2])
            bankroll = float(sys.argv[3])
            total = sum(p.get("position_usd", 0) for p in positions)
            print(json.dumps({
                "total_exposure": round(total, 2),
                "bankroll_pct": round(total / bankroll * 100, 2) if bankroll > 0 else 0,
                "positions": len(positions),
                "remaining_capital": round(bankroll - total, 2),
            }, indent=2))

        elif cmd == "simulate":
            if len(sys.argv) < 6:
                print(json.dumps({"error": "Usage: simulate <fair_prob> <market_prob> <bankroll> <n_bets> [--fraction F]"}))
                sys.exit(1)
            fair_prob = float(sys.argv[2])
            market_price = float(sys.argv[3])
            bankroll = float(sys.argv[4])
            n_bets = int(sys.argv[5])
            frac = DEFAULT_KELLY_FRACTION
            if "--fraction" in sys.argv:
                idx = sys.argv.index("--fraction")
                frac = float(sys.argv[idx + 1])
            result = simulate_kelly(fair_prob, market_price, bankroll, n_bets, frac)
            print(json.dumps(result, indent=2))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
