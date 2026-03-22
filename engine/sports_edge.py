#!/usr/bin/env python3
"""
SPORTS EDGE CALCULATOR — Calibrated odds vs market mispricing.

Same philosophy as weather: use REAL probability models, not LLM guessing.
Sports has mature, calibrated probability sources:
- ESPN win probabilities (pre-game and live)
- FiveThirtyEight Elo ratings → win probabilities
- Vegas/sportsbook lines → implied probabilities (with vig removal)
- Historical head-to-head records

The edge: Retail Polymarket traders don't remove vig from sportsbook lines,
don't compute Elo from scratch, and don't aggregate multiple models.
We do all three, then compare against market prices.

Supported sports:
- NFL, NBA, MLB, NHL (team win/loss)
- Soccer (1X2: home/draw/away)
- Tennis, MMA (head-to-head)
- Props/totals (over/under with historical distributions)

Usage:
    python engine/sports_edge.py elo <team_a_elo> <team_b_elo> [--home-advantage N]
    python engine/sports_edge.py devig <odds_json>
    python engine/sports_edge.py edge <fair_prob> <market_price>
    python engine/sports_edge.py evaluate <signal_json>
    python engine/sports_edge.py multi-source <sources_json> <market_prices_json>
"""

import json
import math
import os
import sys
from pathlib import Path

try:
    from engine.stats import now, wilson_lower
    from engine.kelly import size_position, DEFAULT_KELLY_FRACTION
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now, wilson_lower
    from kelly import size_position, DEFAULT_KELLY_FRACTION

# --- Constants ---
MIN_EDGE_PCT = 0.03             # 3% minimum edge
CONFIDENCE_SPORTS_SINGLE = 0.70  # Single-source confidence
CONFIDENCE_SPORTS_MULTI = 0.80   # Multi-source agreement
CONFIDENCE_SPORTS_STRONG = 0.90  # 3+ sources agree within 3%

# Default home advantage in Elo points by sport
HOME_ADVANTAGE = {
    "nfl": 48,
    "nba": 100,
    "mlb": 24,
    "nhl": 33,
    "soccer": 67,
    "default": 50,
}

# Vig assumptions by source type
TYPICAL_VIG = {
    "vegas": 0.045,       # ~4.5% juice on -110/-110
    "pinnacle": 0.020,    # ~2% on sharp books
    "bovada": 0.050,      # ~5% on soft books
    "espn": 0.0,          # ESPN probabilities are vig-free
    "fivethirtyeight": 0.0,
    "elo": 0.0,
}


def elo_win_probability(elo_a: float, elo_b: float, home_advantage: float = 0) -> dict:
    """Compute win probability from Elo ratings.

    Uses the standard logistic Elo formula:
        P(A wins) = 1 / (1 + 10^((elo_b - elo_a - home_adv) / 400))

    Args:
        elo_a: Elo rating of team/player A.
        elo_b: Elo rating of team/player B.
        home_advantage: Elo points added to team A for home field.

    Returns:
        Dict with probabilities for both sides.
    """
    diff = elo_a + home_advantage - elo_b
    p_a = 1.0 / (1.0 + 10.0 ** (-diff / 400.0))
    p_b = 1.0 - p_a

    return {
        "team_a_prob": round(p_a, 4),
        "team_b_prob": round(p_b, 4),
        "elo_diff": round(diff, 1),
        "method": "elo",
    }


def american_odds_to_prob(odds: float) -> float:
    """Convert American odds to implied probability.

    -150 means bet $150 to win $100 → implied prob = 150/(150+100) = 0.60
    +200 means bet $100 to win $200 → implied prob = 100/(200+100) = 0.333
    """
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    elif odds > 0:
        return 100 / (odds + 100)
    return 0.5


def decimal_odds_to_prob(odds: float) -> float:
    """Convert decimal odds to implied probability.

    2.50 → 1/2.50 = 0.40
    """
    if odds <= 0:
        return 0.0
    return 1.0 / odds


def remove_vig(implied_probs: list, method: str = "proportional") -> list:
    """Remove bookmaker vig (overround) from implied probabilities.

    The sum of implied probabilities from a sportsbook > 1.0.
    The excess is the vig. We need to remove it to get fair probabilities.

    Methods:
    - "proportional": Divide each probability by the sum (most common)
    - "power": Shin's method (better for favorites vs longshots)
    - "additive": Subtract equal amount from each

    Args:
        implied_probs: List of implied probabilities (sum > 1.0).
        method: Vig removal method.

    Returns:
        List of fair probabilities (sum ≈ 1.0).
    """
    total = sum(implied_probs)
    if total <= 0:
        return implied_probs

    if method == "proportional":
        return [round(p / total, 4) for p in implied_probs]
    elif method == "additive":
        excess = total - 1.0
        per_outcome = excess / len(implied_probs)
        return [round(max(p - per_outcome, 0.001), 4) for p in implied_probs]
    elif method == "power":
        # Shin's method: solve for z where sum(p_i / (1 + z*p_i)) = 1
        # Approximation: iterative proportional
        fair = [p / total for p in implied_probs]
        # One iteration of power adjustment
        for _ in range(3):
            adj = [p ** 0.95 for p in fair]
            s = sum(adj)
            fair = [a / s for a in adj]
        return [round(p, 4) for p in fair]
    else:
        return [round(p / total, 4) for p in implied_probs]


def devig_odds(odds_list: list, odds_format: str = "american") -> dict:
    """Convert odds to vig-free probabilities.

    Args:
        odds_list: List of odds for each outcome.
        odds_format: "american" (-150, +200), "decimal" (1.67, 3.00), "probability"

    Returns:
        Dict with implied probs, fair probs, and vig amount.
    """
    if odds_format == "american":
        implied = [american_odds_to_prob(o) for o in odds_list]
    elif odds_format == "decimal":
        implied = [decimal_odds_to_prob(o) for o in odds_list]
    elif odds_format == "probability":
        implied = list(odds_list)
    else:
        return {"error": f"Unknown odds format: {odds_format}"}

    total = sum(implied)
    vig = round(total - 1.0, 4) if total > 1.0 else 0.0
    fair = remove_vig(implied)

    return {
        "implied_probs": [round(p, 4) for p in implied],
        "fair_probs": fair,
        "vig": vig,
        "vig_pct": round(vig * 100, 2),
        "overround": round(total, 4),
    }


def aggregate_sources(sources: list) -> dict:
    """Aggregate multiple probability sources into a consensus estimate.

    Each source is a dict with:
        - name: str (e.g., "espn", "538", "vegas_pinnacle")
        - probs: list of probabilities per outcome
        - weight: float (0-1, relative trust in this source)

    Uses weighted average with source agreement as confidence measure.

    Returns:
        Dict with consensus probs, confidence, and agreement metrics.
    """
    if not sources:
        return {"error": "No sources provided"}

    n_outcomes = len(sources[0].get("probs", []))
    if n_outcomes == 0:
        return {"error": "No probabilities in sources"}

    # Weighted average
    total_weight = sum(s.get("weight", 1.0) for s in sources)
    consensus = [0.0] * n_outcomes

    for s in sources:
        probs = s.get("probs", [])
        if len(probs) != n_outcomes:
            continue
        w = s.get("weight", 1.0) / total_weight
        for i, p in enumerate(probs):
            consensus[i] += p * w

    consensus = [round(p, 4) for p in consensus]

    # Measure agreement: std dev across sources for each outcome
    disagreement = []
    for i in range(n_outcomes):
        vals = [s["probs"][i] for s in sources if len(s.get("probs", [])) > i]
        if len(vals) >= 2:
            mean = sum(vals) / len(vals)
            sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))
            disagreement.append(sd)
        else:
            disagreement.append(0.0)

    avg_disagreement = sum(disagreement) / len(disagreement) if disagreement else 0
    max_disagreement = max(disagreement) if disagreement else 0

    # Confidence based on agreement
    if len(sources) >= 3 and max_disagreement < 0.03:
        confidence = CONFIDENCE_SPORTS_STRONG
    elif len(sources) >= 2 and max_disagreement < 0.05:
        confidence = CONFIDENCE_SPORTS_MULTI
    else:
        confidence = CONFIDENCE_SPORTS_SINGLE

    return {
        "consensus_probs": consensus,
        "confidence": confidence,
        "num_sources": len(sources),
        "avg_disagreement": round(avg_disagreement, 4),
        "max_disagreement": round(max_disagreement, 4),
        "source_names": [s.get("name", "unknown") for s in sources],
    }


def compute_sports_edge(
    fair_probs: list,
    market_prices: list,
    confidence: float = CONFIDENCE_SPORTS_SINGLE,
    labels: list = None,
) -> dict:
    """Compute edge for a sports market.

    Args:
        fair_probs: Our estimated true probabilities per outcome.
        market_prices: Current Polymarket prices per outcome.
        confidence: Source confidence (0-1).
        labels: Optional outcome labels (e.g., ["Team A", "Team B"]).

    Returns:
        Dict with per-outcome edge analysis and actionable trades.
    """
    if len(fair_probs) != len(market_prices):
        return {"error": f"Probability count ({len(fair_probs)}) != price count ({len(market_prices)})"}

    if labels is None:
        labels = [f"Outcome_{i}" for i in range(len(fair_probs))]

    analysis = []
    actionable = []

    for i, (fp, mp, label) in enumerate(zip(fair_probs, market_prices, labels)):
        edge = fp - mp
        edge_pct = edge * 100

        entry = {
            "outcome_idx": i,
            "label": label,
            "fair_prob": fp,
            "market_price": mp,
            "edge": round(edge, 4),
            "edge_pct": round(edge_pct, 2),
        }

        if edge > MIN_EDGE_PCT:
            entry["action"] = "BUY_YES"
            entry["signal_strength"] = round(edge / max(mp, 0.01), 3)
            actionable.append(entry)
        elif edge < -MIN_EDGE_PCT:
            entry["action"] = "BUY_NO"
            entry["signal_strength"] = round(abs(edge) / max(1 - mp, 0.01), 3)
            actionable.append(entry)
        else:
            entry["action"] = "SKIP"
            entry["signal_strength"] = 0

        analysis.append(entry)

    price_sum = sum(market_prices)
    prob_sum = sum(fair_probs)

    return {
        "outcomes": analysis,
        "actionable_count": len(actionable),
        "actionable_trades": actionable,
        "confidence": confidence,
        "price_sum": round(price_sum, 4),
        "prob_sum": round(prob_sum, 4),
        "arb_gap": round(1.0 - price_sum, 4),
        "has_structural_arb": (1.0 - price_sum) > 0.01,
        "timestamp": now(),
    }


def evaluate_sports_signal(signal: dict) -> dict:
    """Full evaluation of a sports signal.

    Accepts multiple data sources, aggregates, computes edge, and
    returns a pipeline-ready result.

    Args:
        signal: Dict with:
            - market_id: str
            - sport: str (nfl, nba, etc.)
            - outcomes: list of labels
            - sources: list of source dicts (name, probs, weight)
            - market_prices: list of current prices
            - Optional: home_team_idx (0 or 1)

    Returns:
        Dict ready to feed into trade_pipeline.evaluate_signal().
    """
    sources = signal.get("sources", [])
    market_prices = signal.get("market_prices", [])
    outcomes = signal.get("outcomes", [])
    sport = signal.get("sport", "default")

    if not sources:
        return {"error": "No probability sources provided"}

    # Aggregate sources
    consensus = aggregate_sources(sources)
    if "error" in consensus:
        return consensus

    fair_probs = consensus["consensus_probs"]
    confidence = consensus["confidence"]

    # Compute edge
    edge_result = compute_sports_edge(fair_probs, market_prices, confidence, outcomes)
    if "error" in edge_result:
        return edge_result

    # Build per-outcome signals for the pipeline
    trade_signals = []
    for trade in edge_result.get("actionable_trades", []):
        trade_signals.append({
            "market_id": f"{signal.get('market_id', '')}_{trade['label']}",
            "category": "sports",
            "fair_prob": trade["fair_prob"],
            "market_price": trade["market_price"],
            "confidence": confidence,
            "direction": "YES" if trade["action"] == "BUY_YES" else "NO",
            "label": trade["label"],
            "sport": sport,
        })

    return {
        "consensus": consensus,
        "edge_analysis": edge_result,
        "trade_signals": trade_signals,
        "actionable_count": len(trade_signals),
        "timestamp": now(),
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
        if cmd == "elo":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: elo <team_a_elo> <team_b_elo> [--home-advantage N]"}))
                sys.exit(1)
            ha = 0
            if "--home-advantage" in sys.argv:
                idx = sys.argv.index("--home-advantage")
                ha = float(sys.argv[idx + 1])
            result = elo_win_probability(float(sys.argv[2]), float(sys.argv[3]), ha)
            print(json.dumps(result, indent=2))

        elif cmd == "devig":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: devig <odds_json> [--format american|decimal|probability]"}))
                sys.exit(1)
            odds = json.loads(sys.argv[2])
            fmt = "american"
            if "--format" in sys.argv:
                idx = sys.argv.index("--format")
                fmt = sys.argv[idx + 1]
            result = devig_odds(odds, fmt)
            print(json.dumps(result, indent=2))

        elif cmd == "edge":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: edge <fair_prob> <market_price>"}))
                sys.exit(1)
            fp = float(sys.argv[2])
            mp = float(sys.argv[3])
            edge = fp - mp
            print(json.dumps({
                "fair_prob": fp, "market_price": mp,
                "edge": round(edge, 4), "edge_pct": round(edge * 100, 2),
                "has_edge": abs(edge) > MIN_EDGE_PCT,
                "direction": "BUY_YES" if edge > MIN_EDGE_PCT else ("BUY_NO" if edge < -MIN_EDGE_PCT else "SKIP"),
            }, indent=2))

        elif cmd == "evaluate":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: evaluate <signal_json>"}))
                sys.exit(1)
            signal = json.loads(sys.argv[2])
            result = evaluate_sports_signal(signal)
            print(json.dumps(result, indent=2))

        elif cmd == "multi-source":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: multi-source <sources_json> <market_prices_json>"}))
                sys.exit(1)
            sources = json.loads(sys.argv[2])
            prices = json.loads(sys.argv[3])
            consensus = aggregate_sources(sources)
            edge = compute_sports_edge(consensus["consensus_probs"], prices, consensus["confidence"])
            print(json.dumps({"consensus": consensus, "edge": edge}, indent=2))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
