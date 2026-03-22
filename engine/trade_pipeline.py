#!/usr/bin/env python3
"""
TRADE PIPELINE — The full wired execution path.

This is the glue that connects all trading modules into one pipeline:

    weather_edge  →  smart_money enrichment  →  kelly sizing  →  risk gate  →  execute/skip

Every trade passes through ALL gates. No shortcuts. No bypasses.
This is what prevents the v1-v4 catastrophes.

Pipeline stages:
1. SIGNAL:    Weather edge or other signal source produces a candidate trade
2. ENRICH:    Smart money data adds conviction boost (or reduces it)
3. SIZE:      Kelly criterion computes optimal position size
4. GATE:      Risk management approves, adjusts, or blocks the trade
5. EXECUTE:   Trade is placed (or skipped with full audit trail)
6. RECORD:    Result logged to risk state, evolution state, and outcomes

Usage:
    python engine/trade_pipeline.py evaluate <signal_json>
    python engine/trade_pipeline.py execute <signal_json> <bankroll>
    python engine/trade_pipeline.py status
    python engine/trade_pipeline.py history [--limit N]
"""

import json
import os
import sys
from pathlib import Path

try:
    from engine.stats import now
    from engine.kelly import size_position, size_multi_position, DEFAULT_KELLY_FRACTION
    from engine.risk import can_trade, record_trade_result, load_risk_state, get_risk_dashboard
    from engine.smart_money import enrich_market, load_wallet_db
    from engine.weather_edge import compute_weather_edge, CONFIDENCE_WEATHER
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now
    from kelly import size_position, size_multi_position, DEFAULT_KELLY_FRACTION
    from risk import can_trade, record_trade_result, load_risk_state, get_risk_dashboard
    from smart_money import enrich_market, load_wallet_db
    from weather_edge import compute_weather_edge, CONFIDENCE_WEATHER

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
PIPELINE_LOG = STATE_DIR / "trade_pipeline.jsonl"

# --- Constants ---
CONVICTION_BOOST_WEIGHT = 0.10   # Smart money can add up to 10% conviction
MIN_CONFIDENCE_TO_TRADE = 0.50   # Below 50% confidence → skip (v4 lesson)


def _log_pipeline_event(event: dict):
    """Append a pipeline event to the audit log."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, separators=(",", ":"))
    fd = os.open(str(PIPELINE_LOG), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def evaluate_signal(signal: dict) -> dict:
    """Run a trading signal through the full evaluation pipeline.

    Does NOT execute the trade — just evaluates it through all stages
    and returns the recommendation.

    Args:
        signal: Dict with at minimum:
            - market_id: str
            - category: str (weather, sports, politics, etc.)
            - fair_prob: float (your estimated true probability)
            - market_price: float (current market price)
            Optional:
            - direction: str (YES/NO, inferred from edge if missing)
            - confidence: float (0-1, defaults to CONFIDENCE_WEATHER for weather)
            - bankroll: float (defaults to loading from risk state)

    Returns:
        Dict with full pipeline analysis and recommendation.
    """
    market_id = signal.get("market_id", "unknown")
    category = signal.get("category", "unknown")
    fair_prob = signal.get("fair_prob", 0.5)
    market_price = signal.get("market_price", 0.5)
    confidence = signal.get("confidence", CONFIDENCE_WEATHER if category == "weather" else 0.7)

    # Load bankroll from risk state if not provided
    bankroll = signal.get("bankroll", 0)
    if bankroll <= 0:
        risk_state = load_risk_state()
        bankroll = risk_state.get("current_bankroll", 0)
    if bankroll <= 0:
        # Try loading from evolution state
        try:
            evo_state_file = STATE_DIR / "evolution.json"
            if evo_state_file.exists():
                with open(evo_state_file) as f:
                    evo = json.load(f)
                bankroll = evo.get("trading", {}).get("bankroll", 0)
        except (json.JSONDecodeError, IOError):
            pass

    stages = []

    # ─── STAGE 1: SIGNAL ───
    edge = fair_prob - market_price
    if edge > 0:
        direction = "YES"
    elif edge < 0:
        direction = "NO"
        edge = (1 - fair_prob) - (1 - market_price)
    else:
        direction = signal.get("direction", "YES")

    stages.append({
        "stage": "SIGNAL",
        "status": "PASS" if abs(edge) > 0.01 else "WEAK",
        "edge_bps": round(edge * 10000, 1),
        "direction": direction,
        "fair_prob": fair_prob,
        "market_price": market_price,
    })

    # ─── STAGE 2: ENRICH (Smart Money) ───
    enrichment = enrich_market(market_id)
    conviction_boost = 0.0

    if enrichment.get("smart_money_present"):
        raw_boost = enrichment.get("conviction_boost", 0) * CONVICTION_BOOST_WEIGHT

        # Only boost if smart money agrees with our direction
        if enrichment.get("dominant_direction") == direction:
            conviction_boost = raw_boost
            confidence = min(confidence + conviction_boost, 1.0)
            enrich_status = "BOOST"
        else:
            # Smart money disagrees — reduce confidence
            conviction_boost = -raw_boost * 0.5
            confidence = max(confidence + conviction_boost, 0.1)
            enrich_status = "CONTRA"
    else:
        enrich_status = "NEUTRAL"

    stages.append({
        "stage": "ENRICH",
        "status": enrich_status,
        "smart_money_present": enrichment.get("smart_money_present", False),
        "smart_money_count": enrichment.get("smart_money_count", 0),
        "conviction_boost": round(conviction_boost, 4),
        "confidence_after": round(confidence, 4),
    })

    # ─── Confidence gate (v4 lesson: sub-50% = noise) ───
    if confidence < MIN_CONFIDENCE_TO_TRADE:
        stages.append({
            "stage": "CONFIDENCE_GATE",
            "status": "BLOCKED",
            "reason": f"Confidence {confidence:.2f} below minimum {MIN_CONFIDENCE_TO_TRADE}",
        })
        result = {
            "action": "SKIP",
            "reason": f"Low confidence ({confidence:.2f})",
            "market_id": market_id,
            "stages": stages,
            "timestamp": now(),
        }
        _log_pipeline_event(result)
        return result

    # ─── STAGE 3: SIZE (Kelly) ───
    sizing = size_position(
        fair_prob=fair_prob,
        market_price=market_price,
        bankroll=bankroll,
        kelly_frac=DEFAULT_KELLY_FRACTION,
        confidence=confidence,
    )

    stages.append({
        "stage": "SIZE",
        "status": "PASS" if sizing["action"] == "BET" else "SKIP",
        "position_usd": sizing.get("position_usd", 0),
        "raw_kelly": sizing.get("raw_kelly", 0),
        "adj_kelly": sizing.get("adj_kelly", 0),
        "expected_profit": sizing.get("expected_profit", 0),
    })

    if sizing["action"] != "BET":
        result = {
            "action": "SKIP",
            "reason": sizing.get("reason", "Kelly says no"),
            "market_id": market_id,
            "stages": stages,
            "timestamp": now(),
        }
        _log_pipeline_event(result)
        return result

    # ─── STAGE 4: RISK GATE ───
    proposed_trade = {
        "market_id": market_id,
        "category": category,
        "position_usd": sizing["position_usd"],
        "direction": direction,
    }

    risk_state = load_risk_state()
    open_positions = risk_state.get("positions", [])
    gate = can_trade(bankroll, open_positions, proposed_trade, risk_state)

    stages.append({
        "stage": "RISK_GATE",
        "status": "PASS" if gate["allowed"] else "BLOCKED",
        "allowed": gate["allowed"],
        "adjusted_size": gate.get("adjusted_size", 0),
        "original_size": sizing["position_usd"],
        "reasons": gate.get("reasons", []),
    })

    if not gate["allowed"]:
        result = {
            "action": "BLOCKED",
            "reason": gate.get("reason", "Risk gate blocked"),
            "market_id": market_id,
            "stages": stages,
            "timestamp": now(),
        }
        _log_pipeline_event(result)
        return result

    # ─── ALL STAGES PASSED ───
    final_size = gate.get("adjusted_size", sizing["position_usd"])

    result = {
        "action": "TRADE",
        "market_id": market_id,
        "category": category,
        "direction": direction,
        "position_usd": round(final_size, 2),
        "fair_prob": fair_prob,
        "market_price": market_price,
        "confidence": round(confidence, 4),
        "edge_bps": round(edge * 10000, 1),
        "expected_profit": round(sizing.get("expected_profit", 0) * final_size / max(sizing["position_usd"], 0.01), 2),
        "bankroll_pct": round(final_size / bankroll * 100, 2) if bankroll > 0 else 0,
        "stages": stages,
        "timestamp": now(),
    }

    _log_pipeline_event(result)
    return result


def evaluate_weather_market(
    forecast_mean: float,
    days_ahead: int,
    bucket_edges: list,
    market_prices: list,
    market_id: str = "",
    bankroll: float = 0,
) -> dict:
    """Convenience: evaluate a weather market through the full pipeline.

    Computes weather edge, then runs each actionable bucket through
    enrich → kelly → risk gate.
    """
    edge_result = compute_weather_edge(forecast_mean, days_ahead, bucket_edges, market_prices)

    if "error" in edge_result:
        return edge_result

    evaluations = []
    for trade in edge_result.get("actionable_trades", []):
        signal = {
            "market_id": f"{market_id}_bucket_{trade.get('label', '')}",
            "category": "weather",
            "fair_prob": trade["probability"],
            "market_price": trade["market_price"],
            "confidence": CONFIDENCE_WEATHER,
            "bankroll": bankroll,
        }
        evaluation = evaluate_signal(signal)
        evaluations.append(evaluation)

    trades = [e for e in evaluations if e["action"] == "TRADE"]
    skips = [e for e in evaluations if e["action"] != "TRADE"]

    return {
        "weather_analysis": {
            "forecast_mean": forecast_mean,
            "forecast_sigma": edge_result.get("forecast_sigma"),
            "days_ahead": days_ahead,
            "total_buckets": edge_result["total_buckets"],
            "actionable_count": edge_result["actionable_count"],
            "arb_gap": edge_result.get("arb_gap", 0),
        },
        "pipeline_results": evaluations,
        "trades_approved": len(trades),
        "trades_skipped": len(skips),
        "total_position_usd": round(sum(t.get("position_usd", 0) for t in trades), 2),
        "total_expected_profit": round(sum(t.get("expected_profit", 0) for t in trades), 2),
        "timestamp": now(),
    }


def get_pipeline_status() -> dict:
    """Get overall pipeline status including all subsystems."""
    risk_state = load_risk_state()
    wallet_db = load_wallet_db()

    # Load evolution trading state
    evo_trading = {}
    try:
        evo_state_file = STATE_DIR / "evolution.json"
        if evo_state_file.exists():
            with open(evo_state_file) as f:
                evo = json.load(f)
            evo_trading = evo.get("trading", {})
    except (json.JSONDecodeError, IOError):
        pass

    bankroll = evo_trading.get("bankroll", risk_state.get("current_bankroll", 0))

    # Read recent pipeline events
    recent_events = []
    if PIPELINE_LOG.exists():
        try:
            with open(PIPELINE_LOG) as f:
                lines = f.readlines()
            for line in lines[-20:]:
                try:
                    recent_events.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        except IOError:
            pass

    recent_trades = [e for e in recent_events if e.get("action") == "TRADE"]
    recent_blocks = [e for e in recent_events if e.get("action") in ("BLOCKED", "SKIP")]

    return {
        "pipeline_operational": True,
        "trading_enabled": evo_trading.get("enabled", False),
        "bankroll": round(bankroll, 2),
        "risk": {
            "halted": risk_state.get("halted", False),
            "halt_reason": risk_state.get("halt_reason"),
            "consecutive_losses": risk_state.get("consecutive_losses", 0),
            "daily_pnl": round(risk_state.get("daily_pnl", 0), 2),
        },
        "smart_money": {
            "tracked_wallets": len(wallet_db.get("wallets", {})),
            "smart_money_count": wallet_db.get("stats", {}).get("smart_money_count", 0),
        },
        "recent_pipeline_events": len(recent_events),
        "recent_trades": len(recent_trades),
        "recent_blocks": len(recent_blocks),
        "last_event": recent_events[-1] if recent_events else None,
        "timestamp": now(),
    }


def get_pipeline_history(limit: int = 50) -> list:
    """Get recent pipeline events."""
    if not PIPELINE_LOG.exists():
        return []

    events = []
    with open(PIPELINE_LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return events[-limit:]


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "evaluate":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: evaluate <signal_json>"}))
                sys.exit(1)
            signal = json.loads(sys.argv[2])
            result = evaluate_signal(signal)
            print(json.dumps(result, indent=2))

        elif cmd == "evaluate-weather":
            if len(sys.argv) < 6:
                print(json.dumps({"error": "Usage: evaluate-weather <forecast_mean> <days_ahead> <bucket_edges_json> <market_prices_json> [bankroll]"}))
                sys.exit(1)
            bankroll = float(sys.argv[6]) if len(sys.argv) > 6 else 0
            result = evaluate_weather_market(
                forecast_mean=float(sys.argv[2]),
                days_ahead=int(sys.argv[3]),
                bucket_edges=json.loads(sys.argv[4]),
                market_prices=json.loads(sys.argv[5]),
                bankroll=bankroll,
            )
            print(json.dumps(result, indent=2))

        elif cmd == "execute":
            # evaluate + record to state (actual execution is external)
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: execute <signal_json>"}))
                sys.exit(1)
            signal = json.loads(sys.argv[2])
            result = evaluate_signal(signal)

            if result["action"] == "TRADE":
                result["execution_status"] = "APPROVED"
                result["note"] = "Trade approved by pipeline. Execute via CLOB API externally."
            else:
                result["execution_status"] = "REJECTED"

            print(json.dumps(result, indent=2))

        elif cmd == "status":
            result = get_pipeline_status()
            print(json.dumps(result, indent=2))

        elif cmd == "history":
            limit = 50
            if "--limit" in sys.argv:
                idx = sys.argv.index("--limit")
                limit = int(sys.argv[idx + 1])
            events = get_pipeline_history(limit)
            print(json.dumps({"events": events, "count": len(events)}, indent=2))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
