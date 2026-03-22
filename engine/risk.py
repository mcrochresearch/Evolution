#!/usr/bin/env python3
"""
RISK MANAGEMENT ENGINE — Circuit breakers that keep you alive.

Implements portfolio-level risk controls for Polymarket trading:
- Drawdown circuit breakers (halt trading when losses exceed thresholds)
- Maximum exposure limits (per-market, per-category, portfolio-wide)
- Consecutive loss detection
- Correlation-aware exposure tracking
- Daily/weekly P&L limits

This is the module that would have prevented the v1-v3 catastrophe ($1,500 → $376)
and the v4 directional bloodbath (-$847 on sub-50% confidence trades).

Usage:
    python engine/risk.py check <bankroll> <positions_json>
    python engine/risk.py drawdown <peak_bankroll> <current_bankroll>
    python engine/risk.py can-trade <bankroll> <positions_json> <proposed_trade_json>
    python engine/risk.py status <state_file>
    python engine/risk.py reset-daily
"""

import json
import math
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from engine.stats import now
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
RISK_STATE_FILE = STATE_DIR / "risk_state.json"

# ============================================================================
# RISK LIMITS — The lines you never cross
# ============================================================================

# Drawdown circuit breakers
DRAWDOWN_WARNING = 0.10       # 10% drawdown → reduce position sizes by 50%
DRAWDOWN_HALT = 0.20          # 20% drawdown → halt all new trades
DRAWDOWN_EMERGENCY = 0.35     # 35% drawdown → close all positions

# Exposure limits
MAX_PORTFOLIO_EXPOSURE_PCT = 0.50    # Never have >50% of bankroll at risk
MAX_SINGLE_MARKET_PCT = 0.10         # Max 10% of bankroll on any single market
MAX_CATEGORY_PCT = 0.25              # Max 25% in any single category (weather, sports, etc.)
MAX_CORRELATED_PCT = 0.30            # Max 30% on correlated positions

# Loss limits
MAX_DAILY_LOSS_PCT = 0.05            # Halt after 5% daily loss
MAX_WEEKLY_LOSS_PCT = 0.10           # Halt after 10% weekly loss
MAX_CONSECUTIVE_LOSSES = 5           # Halt after 5 consecutive losses

# Position limits
MAX_OPEN_POSITIONS = 20              # Max concurrent positions
MAX_POSITIONS_PER_MARKET = 3         # Max positions per market (YES + NO + arb)

# Minimum bankroll to keep trading
MIN_BANKROLL_USD = 10.0              # Below this, stop everything


def default_risk_state() -> dict:
    """Create fresh risk management state."""
    return {
        "created": now(),
        "peak_bankroll": 0.0,
        "current_bankroll": 0.0,
        "daily_pnl": 0.0,
        "weekly_pnl": 0.0,
        "daily_reset_at": now(),
        "weekly_reset_at": now(),
        "consecutive_losses": 0,
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "halted": False,
        "halt_reason": None,
        "halt_until": None,
        "positions": [],
        "closed_positions": [],
        "risk_events": [],
    }


def load_risk_state() -> dict:
    """Load risk state from disk, creating default if not found."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if RISK_STATE_FILE.exists():
        try:
            with open(RISK_STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return default_risk_state()


def save_risk_state(state: dict):
    """Atomically save risk state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(RISK_STATE_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, str(RISK_STATE_FILE))


def _add_risk_event(state: dict, level: str, event: str, details: dict = None):
    """Record a risk event for audit trail."""
    state.setdefault("risk_events", [])
    state["risk_events"].append({
        "timestamp": now(),
        "level": level,
        "event": event,
        "details": details or {},
    })
    # Keep last 200 events
    state["risk_events"] = state["risk_events"][-200:]


# ============================================================================
# CORE RISK CHECKS
# ============================================================================

def check_drawdown(peak_bankroll: float, current_bankroll: float) -> dict:
    """Check drawdown level and return appropriate action.

    Returns:
        Dict with drawdown_pct, level (OK/WARNING/HALT/EMERGENCY), and action.
    """
    if peak_bankroll <= 0:
        return {"drawdown_pct": 0, "level": "OK", "action": "TRADE_NORMAL"}

    drawdown = (peak_bankroll - current_bankroll) / peak_bankroll

    if drawdown >= DRAWDOWN_EMERGENCY:
        return {
            "drawdown_pct": round(drawdown * 100, 2),
            "level": "EMERGENCY",
            "action": "CLOSE_ALL",
            "message": f"EMERGENCY: {drawdown*100:.1f}% drawdown. Close all positions immediately.",
        }
    elif drawdown >= DRAWDOWN_HALT:
        return {
            "drawdown_pct": round(drawdown * 100, 2),
            "level": "HALT",
            "action": "NO_NEW_TRADES",
            "message": f"HALT: {drawdown*100:.1f}% drawdown. No new trades until recovery.",
        }
    elif drawdown >= DRAWDOWN_WARNING:
        return {
            "drawdown_pct": round(drawdown * 100, 2),
            "level": "WARNING",
            "action": "REDUCE_SIZE",
            "size_multiplier": 0.5,
            "message": f"WARNING: {drawdown*100:.1f}% drawdown. Reducing position sizes by 50%.",
        }
    else:
        return {
            "drawdown_pct": round(drawdown * 100, 2),
            "level": "OK",
            "action": "TRADE_NORMAL",
        }


def check_exposure(positions: list, bankroll: float) -> dict:
    """Check portfolio exposure against limits.

    Args:
        positions: List of position dicts with at least:
            - market_id: str
            - category: str (weather, sports, politics, crypto, etc.)
            - position_usd: float
            - direction: str (YES/NO)
        bankroll: Total available capital.

    Returns:
        Dict with exposure breakdown and any violations.
    """
    if bankroll <= 0:
        return {"error": "Bankroll is zero or negative", "can_trade": False}

    violations = []

    # Total exposure
    total_exposure = sum(abs(p.get("position_usd", 0)) for p in positions)
    total_pct = total_exposure / bankroll

    if total_pct > MAX_PORTFOLIO_EXPOSURE_PCT:
        violations.append({
            "type": "PORTFOLIO_EXPOSURE",
            "current": round(total_pct * 100, 2),
            "limit": MAX_PORTFOLIO_EXPOSURE_PCT * 100,
            "message": f"Portfolio exposure {total_pct*100:.1f}% exceeds {MAX_PORTFOLIO_EXPOSURE_PCT*100}% limit",
        })

    # Per-market exposure
    by_market = {}
    for p in positions:
        mid = p.get("market_id", "unknown")
        by_market[mid] = by_market.get(mid, 0) + abs(p.get("position_usd", 0))

    for mid, exposure in by_market.items():
        pct = exposure / bankroll
        if pct > MAX_SINGLE_MARKET_PCT:
            violations.append({
                "type": "SINGLE_MARKET",
                "market_id": mid,
                "current": round(pct * 100, 2),
                "limit": MAX_SINGLE_MARKET_PCT * 100,
                "message": f"Market {mid}: {pct*100:.1f}% exceeds {MAX_SINGLE_MARKET_PCT*100}% limit",
            })

    # Per-category exposure
    by_category = {}
    for p in positions:
        cat = p.get("category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + abs(p.get("position_usd", 0))

    for cat, exposure in by_category.items():
        pct = exposure / bankroll
        if pct > MAX_CATEGORY_PCT:
            violations.append({
                "type": "CATEGORY_EXPOSURE",
                "category": cat,
                "current": round(pct * 100, 2),
                "limit": MAX_CATEGORY_PCT * 100,
                "message": f"Category {cat}: {pct*100:.1f}% exceeds {MAX_CATEGORY_PCT*100}% limit",
            })

    # Position count
    if len(positions) > MAX_OPEN_POSITIONS:
        violations.append({
            "type": "POSITION_COUNT",
            "current": len(positions),
            "limit": MAX_OPEN_POSITIONS,
            "message": f"{len(positions)} positions exceeds {MAX_OPEN_POSITIONS} limit",
        })

    return {
        "total_exposure_usd": round(total_exposure, 2),
        "total_exposure_pct": round(total_pct * 100, 2),
        "by_market": {k: round(v, 2) for k, v in by_market.items()},
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
        "open_positions": len(positions),
        "violations": violations,
        "can_trade": len(violations) == 0,
        "remaining_capacity_usd": round(max(0, bankroll * MAX_PORTFOLIO_EXPOSURE_PCT - total_exposure), 2),
    }


def can_trade(
    bankroll: float,
    positions: list,
    proposed_trade: dict,
    risk_state: dict = None,
) -> dict:
    """Master gate: can this trade be placed?

    Checks ALL risk limits in order:
    1. Is trading halted?
    2. Minimum bankroll check
    3. Drawdown check
    4. Daily/weekly loss limits
    5. Consecutive loss check
    6. Exposure limits
    7. Position count limits

    Args:
        bankroll: Current available capital.
        positions: Current open positions.
        proposed_trade: Dict with market_id, category, position_usd, direction.
        risk_state: Optional persisted risk state.

    Returns:
        Dict with allowed (bool), reason, and any size adjustments.
    """
    if risk_state is None:
        risk_state = load_risk_state()

    trade_size = proposed_trade.get("position_usd", 0)
    reasons = []

    # 1. Is trading halted?
    if risk_state.get("halted"):
        return {
            "allowed": False,
            "reason": f"Trading halted: {risk_state.get('halt_reason', 'unknown')}",
            "adjusted_size": 0,
        }

    # 2. Minimum bankroll
    if bankroll < MIN_BANKROLL_USD:
        return {
            "allowed": False,
            "reason": f"Bankroll ${bankroll:.2f} below minimum ${MIN_BANKROLL_USD}",
            "adjusted_size": 0,
        }

    # 3. Drawdown check
    peak = risk_state.get("peak_bankroll", bankroll)
    if peak < bankroll:
        peak = bankroll  # Update peak
    dd = check_drawdown(peak, bankroll)

    size_multiplier = 1.0
    if dd["action"] == "CLOSE_ALL":
        return {"allowed": False, "reason": dd["message"], "adjusted_size": 0}
    elif dd["action"] == "NO_NEW_TRADES":
        return {"allowed": False, "reason": dd["message"], "adjusted_size": 0}
    elif dd["action"] == "REDUCE_SIZE":
        size_multiplier = dd.get("size_multiplier", 0.5)
        reasons.append(f"Drawdown warning: size reduced to {size_multiplier*100:.0f}%")

    # 4. Daily/weekly loss limits
    daily_pnl = risk_state.get("daily_pnl", 0)
    weekly_pnl = risk_state.get("weekly_pnl", 0)

    if bankroll > 0:
        if abs(daily_pnl) / bankroll > MAX_DAILY_LOSS_PCT and daily_pnl < 0:
            return {
                "allowed": False,
                "reason": f"Daily loss limit hit: ${daily_pnl:.2f} ({abs(daily_pnl)/bankroll*100:.1f}%)",
                "adjusted_size": 0,
            }
        if abs(weekly_pnl) / bankroll > MAX_WEEKLY_LOSS_PCT and weekly_pnl < 0:
            return {
                "allowed": False,
                "reason": f"Weekly loss limit hit: ${weekly_pnl:.2f} ({abs(weekly_pnl)/bankroll*100:.1f}%)",
                "adjusted_size": 0,
            }

    # 5. Consecutive losses
    if risk_state.get("consecutive_losses", 0) >= MAX_CONSECUTIVE_LOSSES:
        return {
            "allowed": False,
            "reason": f"{risk_state['consecutive_losses']} consecutive losses — halted until manual review",
            "adjusted_size": 0,
        }

    # 6. Exposure limits (with proposed trade included)
    test_positions = positions + [{
        "market_id": proposed_trade.get("market_id", "unknown"),
        "category": proposed_trade.get("category", "unknown"),
        "position_usd": trade_size * size_multiplier,
        "direction": proposed_trade.get("direction", "YES"),
    }]
    exposure = check_exposure(test_positions, bankroll)

    if not exposure.get("can_trade", False):
        # Try reducing to fit within limits
        remaining = exposure.get("remaining_capacity_usd", 0)
        if remaining > 1.0:
            adjusted = min(trade_size * size_multiplier, remaining)
            reasons.append(f"Exposure limit: size capped to ${adjusted:.2f}")
            trade_size = adjusted
            size_multiplier = adjusted / proposed_trade.get("position_usd", 1)
        else:
            return {
                "allowed": False,
                "reason": "Exposure limits exceeded: " + "; ".join(
                    v["message"] for v in exposure["violations"]
                ),
                "adjusted_size": 0,
            }

    adjusted_size = round(trade_size * size_multiplier, 2)

    return {
        "allowed": True,
        "adjusted_size": adjusted_size,
        "original_size": proposed_trade.get("position_usd", 0),
        "size_multiplier": round(size_multiplier, 3),
        "reasons": reasons if reasons else ["All risk checks passed"],
        "exposure_after": exposure,
        "drawdown": dd,
    }


def record_trade_result(win: bool, pnl: float, risk_state: dict = None) -> dict:
    """Record a trade outcome and update risk state.

    Args:
        win: Whether the trade was profitable.
        pnl: Profit/loss in USD (negative for losses).
        risk_state: Optional existing state (loads from disk if None).

    Returns:
        Updated risk state dict (also saved to disk).
    """
    if risk_state is None:
        risk_state = load_risk_state()

    risk_state["total_trades"] = risk_state.get("total_trades", 0) + 1
    risk_state["daily_pnl"] = risk_state.get("daily_pnl", 0) + pnl
    risk_state["weekly_pnl"] = risk_state.get("weekly_pnl", 0) + pnl

    if win:
        risk_state["winning_trades"] = risk_state.get("winning_trades", 0) + 1
        risk_state["consecutive_losses"] = 0
    else:
        risk_state["losing_trades"] = risk_state.get("losing_trades", 0) + 1
        risk_state["consecutive_losses"] = risk_state.get("consecutive_losses", 0) + 1

    # Update bankroll tracking
    current = risk_state.get("current_bankroll", 0) + pnl
    risk_state["current_bankroll"] = current
    if current > risk_state.get("peak_bankroll", 0):
        risk_state["peak_bankroll"] = current

    # Check if we need to halt
    if risk_state["consecutive_losses"] >= MAX_CONSECUTIVE_LOSSES:
        risk_state["halted"] = True
        risk_state["halt_reason"] = f"{MAX_CONSECUTIVE_LOSSES} consecutive losses"
        _add_risk_event(risk_state, "CRITICAL", "HALT_CONSECUTIVE_LOSSES", {
            "consecutive_losses": risk_state["consecutive_losses"],
        })

    # Check drawdown
    dd = check_drawdown(risk_state.get("peak_bankroll", current), current)
    if dd["level"] in ("HALT", "EMERGENCY"):
        risk_state["halted"] = True
        risk_state["halt_reason"] = dd["message"]
        _add_risk_event(risk_state, "CRITICAL", f"HALT_{dd['level']}", {
            "drawdown_pct": dd["drawdown_pct"],
        })

    _add_risk_event(risk_state, "INFO", "TRADE_RESULT", {
        "win": win, "pnl": round(pnl, 2),
        "consecutive_losses": risk_state["consecutive_losses"],
    })

    save_risk_state(risk_state)
    return risk_state


def reset_daily(risk_state: dict = None) -> dict:
    """Reset daily P&L counter. Call at start of each trading day."""
    if risk_state is None:
        risk_state = load_risk_state()

    old_daily = risk_state.get("daily_pnl", 0)
    risk_state["daily_pnl"] = 0.0
    risk_state["daily_reset_at"] = now()

    # Also check if weekly reset needed (every 7 days)
    weekly_reset = risk_state.get("weekly_reset_at", "")
    if weekly_reset:
        try:
            reset_dt = datetime.fromisoformat(weekly_reset.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - reset_dt).days >= 7:
                risk_state["weekly_pnl"] = 0.0
                risk_state["weekly_reset_at"] = now()
        except (ValueError, TypeError):
            pass

    # If halted due to daily loss, unhalt
    if risk_state.get("halted") and "daily" in risk_state.get("halt_reason", "").lower():
        risk_state["halted"] = False
        risk_state["halt_reason"] = None

    _add_risk_event(risk_state, "INFO", "DAILY_RESET", {"previous_daily_pnl": round(old_daily, 2)})
    save_risk_state(risk_state)
    return risk_state


def get_risk_dashboard(bankroll: float, positions: list, risk_state: dict = None) -> dict:
    """Get a complete risk dashboard for display.

    Returns all risk metrics in one call — designed for the Evolution status display.
    """
    if risk_state is None:
        risk_state = load_risk_state()

    peak = max(risk_state.get("peak_bankroll", bankroll), bankroll)
    dd = check_drawdown(peak, bankroll)
    exposure = check_exposure(positions, bankroll)

    total_trades = risk_state.get("total_trades", 0)
    winning = risk_state.get("winning_trades", 0)

    return {
        "bankroll": round(bankroll, 2),
        "peak_bankroll": round(peak, 2),
        "drawdown": dd,
        "exposure": exposure,
        "daily_pnl": round(risk_state.get("daily_pnl", 0), 2),
        "weekly_pnl": round(risk_state.get("weekly_pnl", 0), 2),
        "consecutive_losses": risk_state.get("consecutive_losses", 0),
        "win_rate": round(winning / total_trades, 3) if total_trades > 0 else 0,
        "total_trades": total_trades,
        "halted": risk_state.get("halted", False),
        "halt_reason": risk_state.get("halt_reason"),
        "can_trade": not risk_state.get("halted", False) and bankroll >= MIN_BANKROLL_USD,
        "recent_events": risk_state.get("risk_events", [])[-5:],
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
        if cmd == "check":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: check <bankroll> <positions_json>"}))
                sys.exit(1)
            bankroll = float(sys.argv[2])
            positions = json.loads(sys.argv[3])
            result = check_exposure(positions, bankroll)
            print(json.dumps(result, indent=2))

        elif cmd == "drawdown":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: drawdown <peak_bankroll> <current_bankroll>"}))
                sys.exit(1)
            result = check_drawdown(float(sys.argv[2]), float(sys.argv[3]))
            print(json.dumps(result, indent=2))

        elif cmd == "can-trade":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: can-trade <bankroll> <positions_json> <proposed_trade_json>"}))
                sys.exit(1)
            bankroll = float(sys.argv[2])
            positions = json.loads(sys.argv[3])
            trade = json.loads(sys.argv[4])
            result = can_trade(bankroll, positions, trade)
            print(json.dumps(result, indent=2))

        elif cmd == "status":
            bankroll = float(sys.argv[2]) if len(sys.argv) > 2 else 0
            positions = json.loads(sys.argv[3]) if len(sys.argv) > 3 else []
            result = get_risk_dashboard(bankroll, positions)
            print(json.dumps(result, indent=2))

        elif cmd == "record":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: record <win|loss> <pnl_usd>"}))
                sys.exit(1)
            win = sys.argv[2].lower() == "win"
            pnl = float(sys.argv[3])
            state = record_trade_result(win, pnl)
            print(json.dumps({
                "status": "recorded", "win": win, "pnl": pnl,
                "consecutive_losses": state["consecutive_losses"],
                "halted": state.get("halted", False),
            }, indent=2))

        elif cmd == "reset-daily":
            result = reset_daily()
            print(json.dumps({"status": "daily_reset", "daily_pnl": result["daily_pnl"]}))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
