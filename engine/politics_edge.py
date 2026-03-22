#!/usr/bin/env python3
"""
POLITICS & ECONOMICS EDGE CALCULATOR — Smart money over crowd wisdom.

Political and economic markets are the MOST efficient on Polymarket.
Every pollster, pundit, and political junkie is already trading.
Our edge is NOT prediction — it's:

1. POLLING AGGREGATION: Combine multiple polls with recency weighting
   and pollster quality scoring (like 538 but for Polymarket)
2. SMART MONEY EMPHASIS: When smart money wallets move on political
   markets, that's the strongest signal we have
3. STRUCTURAL ARBS: Multi-outcome political markets (e.g., "Who wins
   the primary?") often have price_sum < 1.0
4. STALE MARKET DETECTION: Events that have already been decided but
   market hasn't updated yet (fastest-finger edge)

Honest about what we CAN'T do:
- We cannot out-predict Nate Silver on elections
- We cannot forecast Fed rate decisions better than bond traders
- Sub-3% edges in politics are noise, not signal

Usage:
    python engine/politics_edge.py aggregate-polls <polls_json>
    python engine/politics_edge.py evaluate <signal_json>
    python engine/politics_edge.py structural-arb <outcomes_json> <prices_json>
    python engine/politics_edge.py stale-check <market_id> <known_result> <current_prices_json>
"""

import json
import math
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from engine.stats import now, wilson_lower
    from engine.kelly import size_position, DEFAULT_KELLY_FRACTION
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now, wilson_lower
    from kelly import size_position, DEFAULT_KELLY_FRACTION

# --- Constants ---
MIN_EDGE_PCT_POLITICS = 0.04    # 4% minimum — politics markets are efficient
CONFIDENCE_POLLS_SINGLE = 0.55  # Single poll = low confidence
CONFIDENCE_POLLS_MULTI = 0.65   # Multiple polls agreeing
CONFIDENCE_POLLS_STRONG = 0.75  # 5+ polls, A+ pollsters, recent
CONFIDENCE_SMART_MONEY = 0.80   # Smart money signal on politics
CONFIDENCE_STALE_MARKET = 0.95  # Known result, market hasn't updated

# Pollster quality tiers (inspired by 538's pollster ratings)
POLLSTER_QUALITY = {
    "A+": 1.0,
    "A": 0.90,
    "A-": 0.85,
    "B+": 0.75,
    "B": 0.65,
    "B-": 0.55,
    "C+": 0.45,
    "C": 0.35,
    "C-": 0.25,
    "D": 0.15,
    "unrated": 0.40,
}

# Recency decay: polls lose value over time
POLL_HALF_LIFE_DAYS = 14  # Poll weight halves every 14 days


def _recency_weight(poll_date: str) -> float:
    """Compute recency weight for a poll using exponential decay.

    Recent polls get more weight. A poll from 14 days ago gets 50% weight.
    """
    try:
        poll_dt = datetime.fromisoformat(poll_date.replace("Z", "+00:00"))
        # Ensure timezone-aware
        if poll_dt.tzinfo is None:
            poll_dt = poll_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.5  # Unknown date gets default weight

    age_days = (datetime.now(timezone.utc) - poll_dt).total_seconds() / 86400
    if age_days < 0:
        age_days = 0

    # Exponential decay: weight = 2^(-age/half_life)
    return 2.0 ** (-age_days / POLL_HALF_LIFE_DAYS)


def aggregate_polls(polls: list) -> dict:
    """Aggregate multiple polls into a consensus probability estimate.

    Each poll is a dict with:
        - pollster: str (name)
        - rating: str (A+, A, B, etc.)
        - date: str (YYYY-MM-DD or ISO)
        - sample_size: int
        - results: dict mapping candidate/outcome → percentage (0-100)

    Weighting factors:
    1. Pollster quality (A+ = 1.0, D = 0.15)
    2. Recency (half-life = 14 days)
    3. Sample size (log-scaled)

    Returns:
        Dict with weighted consensus probabilities.
    """
    if not polls:
        return {"error": "No polls provided"}

    # Collect all outcomes
    all_outcomes = set()
    for p in polls:
        all_outcomes.update(p.get("results", {}).keys())

    if not all_outcomes:
        return {"error": "No results in polls"}

    outcomes = sorted(all_outcomes)

    # Compute weighted average
    weighted_sums = {o: 0.0 for o in outcomes}
    total_weight = 0.0

    poll_details = []
    for p in polls:
        rating = p.get("rating", "unrated")
        quality = POLLSTER_QUALITY.get(rating, 0.40)
        recency = _recency_weight(p.get("date", ""))
        sample = p.get("sample_size", 500)
        sample_factor = math.log(max(sample, 10)) / math.log(2000)  # Normalized to ~1.0 at n=2000
        sample_factor = min(max(sample_factor, 0.3), 1.5)

        weight = quality * recency * sample_factor
        total_weight += weight

        results = p.get("results", {})
        for o in outcomes:
            pct = results.get(o, 0) / 100.0  # Convert percentage to probability
            weighted_sums[o] += pct * weight

        poll_details.append({
            "pollster": p.get("pollster", "unknown"),
            "rating": rating,
            "quality_weight": round(quality, 2),
            "recency_weight": round(recency, 2),
            "sample_weight": round(sample_factor, 2),
            "total_weight": round(weight, 3),
            "date": p.get("date", ""),
        })

    if total_weight == 0:
        return {"error": "All polls have zero weight"}

    # Normalize
    raw_probs = {o: weighted_sums[o] / total_weight for o in outcomes}

    # Ensure probabilities sum to 1.0
    prob_sum = sum(raw_probs.values())
    if prob_sum > 0:
        fair_probs = {o: round(v / prob_sum, 4) for o, v in raw_probs.items()}
    else:
        fair_probs = {o: round(1.0 / len(outcomes), 4) for o in outcomes}

    # Confidence based on poll count and quality
    n_polls = len(polls)
    avg_quality = sum(POLLSTER_QUALITY.get(p.get("rating", "unrated"), 0.4) for p in polls) / n_polls
    avg_recency = sum(_recency_weight(p.get("date", "")) for p in polls) / n_polls

    if n_polls >= 5 and avg_quality >= 0.7 and avg_recency >= 0.5:
        confidence = CONFIDENCE_POLLS_STRONG
    elif n_polls >= 3 and avg_quality >= 0.5:
        confidence = CONFIDENCE_POLLS_MULTI
    else:
        confidence = CONFIDENCE_POLLS_SINGLE

    # Measure disagreement across polls
    disagreements = []
    for o in outcomes:
        vals = [p.get("results", {}).get(o, 0) / 100.0 for p in polls]
        if len(vals) >= 2:
            mean = sum(vals) / len(vals)
            sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))
            disagreements.append(sd)

    avg_disagreement = sum(disagreements) / len(disagreements) if disagreements else 0

    return {
        "outcomes": outcomes,
        "fair_probs": fair_probs,
        "confidence": confidence,
        "num_polls": n_polls,
        "avg_quality": round(avg_quality, 2),
        "avg_recency": round(avg_recency, 2),
        "avg_disagreement": round(avg_disagreement, 4),
        "poll_details": poll_details,
    }


def detect_structural_arb(outcomes: list, market_prices: list) -> dict:
    """Detect structural arbitrage in multi-outcome political markets.

    When sum(prices) < 1.0, there's guaranteed profit by buying all outcomes.
    This happens frequently in political markets with 5+ candidates.

    Args:
        outcomes: List of outcome labels.
        market_prices: List of current prices.

    Returns:
        Dict with arb analysis.
    """
    if len(outcomes) != len(market_prices):
        return {"error": "Outcome count doesn't match price count"}

    price_sum = sum(market_prices)
    arb_gap = 1.0 - price_sum

    # Per-outcome analysis
    outcome_analysis = []
    for label, price in zip(outcomes, market_prices):
        outcome_analysis.append({
            "label": label,
            "price": round(price, 4),
            "implied_prob": round(price / price_sum, 4) if price_sum > 0 else 0,
        })

    if arb_gap > 0.01:
        # Calculate profit from buying all outcomes
        cost = price_sum
        guaranteed_payout = 1.0
        profit = guaranteed_payout - cost
        roi = profit / cost if cost > 0 else 0

        return {
            "has_arb": True,
            "arb_gap": round(arb_gap, 4),
            "arb_gap_pct": round(arb_gap * 100, 2),
            "total_cost": round(cost, 4),
            "guaranteed_payout": 1.0,
            "guaranteed_profit": round(profit, 4),
            "roi_pct": round(roi * 100, 2),
            "outcomes": outcome_analysis,
            "strategy": "Buy all outcomes proportionally",
            "confidence": 0.95,  # Structural arb is near-certain
        }
    elif arb_gap < -0.01:
        return {
            "has_arb": False,
            "overpriced": True,
            "overround": round(-arb_gap, 4),
            "overround_pct": round(-arb_gap * 100, 2),
            "outcomes": outcome_analysis,
            "note": "Prices sum > 1.0: market is overpriced, no buy-all arb exists",
        }
    else:
        return {
            "has_arb": False,
            "price_sum": round(price_sum, 4),
            "outcomes": outcome_analysis,
            "note": "Prices are fairly balanced (sum ≈ 1.0)",
        }


def detect_stale_market(
    known_result: str,
    outcomes: list,
    market_prices: list,
) -> dict:
    """Detect markets where the result is known but prices haven't updated.

    This is the "fastest finger" edge: when a news event resolves a market
    but the price still reflects uncertainty.

    Args:
        known_result: The outcome that has been determined.
        outcomes: List of all outcome labels.
        market_prices: Current prices.

    Returns:
        Dict with stale market analysis and trade signal.
    """
    if known_result not in outcomes:
        return {"error": f"Known result '{known_result}' not in outcomes {outcomes}"}

    idx = outcomes.index(known_result)
    current_price = market_prices[idx]

    # If the known winner is priced < 0.95, market is stale
    if current_price < 0.95:
        edge = 1.0 - current_price
        return {
            "stale": True,
            "known_result": known_result,
            "current_price": round(current_price, 4),
            "fair_price": 1.0,
            "edge": round(edge, 4),
            "edge_pct": round(edge * 100, 2),
            "confidence": CONFIDENCE_STALE_MARKET,
            "action": "BUY_YES",
            "urgency": "HIGH" if current_price < 0.80 else "MEDIUM",
            "note": f"Market prices {known_result} at {current_price:.2f} but outcome is known. Edge: {edge*100:.1f}%",
        }
    else:
        return {
            "stale": False,
            "known_result": known_result,
            "current_price": round(current_price, 4),
            "note": "Market has already adjusted to known result",
        }


def evaluate_politics_signal(signal: dict) -> dict:
    """Full evaluation of a political/economics signal.

    Supports three signal types:
    1. "poll_aggregate": Aggregate polls → compute edge
    2. "structural_arb": Detect multi-outcome arbs
    3. "stale_market": Fast-finger on known results

    Args:
        signal: Dict with:
            - type: "poll_aggregate" | "structural_arb" | "stale_market"
            - market_id: str
            - outcomes: list of labels
            - market_prices: list
            - Plus type-specific fields

    Returns:
        Dict with analysis and pipeline-ready trade signals.
    """
    sig_type = signal.get("type", "poll_aggregate")
    market_id = signal.get("market_id", "unknown")
    outcomes = signal.get("outcomes", [])
    market_prices = signal.get("market_prices", [])

    if sig_type == "structural_arb":
        arb = detect_structural_arb(outcomes, market_prices)
        trade_signals = []
        if arb.get("has_arb"):
            # Buy all outcomes
            for i, (o, p) in enumerate(zip(outcomes, market_prices)):
                trade_signals.append({
                    "market_id": f"{market_id}_{o}",
                    "category": "politics",
                    "fair_prob": arb["outcomes"][i]["implied_prob"],
                    "market_price": p,
                    "confidence": arb["confidence"],
                    "direction": "YES",
                    "label": o,
                })
        return {
            "type": "structural_arb",
            "arb_analysis": arb,
            "trade_signals": trade_signals,
            "actionable_count": len(trade_signals),
            "timestamp": now(),
        }

    elif sig_type == "stale_market":
        known = signal.get("known_result", "")
        stale = detect_stale_market(known, outcomes, market_prices)
        trade_signals = []
        if stale.get("stale"):
            trade_signals.append({
                "market_id": f"{market_id}_{known}",
                "category": "politics",
                "fair_prob": 1.0,
                "market_price": stale["current_price"],
                "confidence": CONFIDENCE_STALE_MARKET,
                "direction": "YES",
                "label": known,
            })
        return {
            "type": "stale_market",
            "stale_analysis": stale,
            "trade_signals": trade_signals,
            "actionable_count": len(trade_signals),
            "timestamp": now(),
        }

    elif sig_type == "poll_aggregate":
        polls = signal.get("polls", [])
        if not polls:
            return {"error": "No polls provided for aggregation"}

        consensus = aggregate_polls(polls)
        if "error" in consensus:
            return consensus

        fair_probs = consensus["fair_probs"]
        confidence = consensus["confidence"]

        # Compute edge per outcome
        trade_signals = []
        for i, (outcome, fp) in enumerate(fair_probs.items()):
            if i >= len(market_prices):
                break
            mp = market_prices[i]
            edge = fp - mp

            if abs(edge) > MIN_EDGE_PCT_POLITICS:
                trade_signals.append({
                    "market_id": f"{market_id}_{outcome}",
                    "category": "politics",
                    "fair_prob": fp,
                    "market_price": mp,
                    "confidence": confidence,
                    "direction": "YES" if edge > 0 else "NO",
                    "label": outcome,
                    "edge_pct": round(edge * 100, 2),
                })

        return {
            "type": "poll_aggregate",
            "consensus": consensus,
            "trade_signals": trade_signals,
            "actionable_count": len(trade_signals),
            "timestamp": now(),
        }

    else:
        return {"error": f"Unknown signal type: {sig_type}"}


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "aggregate-polls":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: aggregate-polls <polls_json>"}))
                sys.exit(1)
            polls = json.loads(sys.argv[2])
            result = aggregate_polls(polls)
            print(json.dumps(result, indent=2))

        elif cmd == "evaluate":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: evaluate <signal_json>"}))
                sys.exit(1)
            signal = json.loads(sys.argv[2])
            result = evaluate_politics_signal(signal)
            print(json.dumps(result, indent=2))

        elif cmd == "structural-arb":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: structural-arb <outcomes_json> <prices_json>"}))
                sys.exit(1)
            outcomes = json.loads(sys.argv[2])
            prices = json.loads(sys.argv[3])
            result = detect_structural_arb(outcomes, prices)
            print(json.dumps(result, indent=2))

        elif cmd == "stale-check":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: stale-check <known_result> <outcomes_json> <prices_json>"}))
                sys.exit(1)
            result = detect_stale_market(sys.argv[2], json.loads(sys.argv[3]), json.loads(sys.argv[4]))
            print(json.dumps(result, indent=2))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
