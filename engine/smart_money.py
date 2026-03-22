#!/usr/bin/env python3
"""
SMART MONEY TRACKER — Follow the wallets that actually win.

Profiles Polymarket wallets, tracks their positions, and generates
signals when high-WR wallets enter new markets. This is the module
that turns the v4 insider scanner concept into something that works.

Key fixes over v4:
1. Per-wallet activity tracking (not global /trades endpoint)
2. Persistent wallet database with win rate history
3. Signal enrichment (not standalone strategy) — feeds into conviction scoring
4. Minimum 65% WR + 50 trades for "smart money" classification

Usage:
    python engine/smart_money.py add-wallet <address> [--alias NAME]
    python engine/smart_money.py profile <address>
    python engine/smart_money.py update-all
    python engine/smart_money.py signals [--min-wr 0.65] [--min-trades 50]
    python engine/smart_money.py enrich <market_id>
    python engine/smart_money.py status
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from engine.stats import now, wilson_lower
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now, wilson_lower

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
WALLET_DB_FILE = STATE_DIR / "smart_money.json"

# --- Constants ---
MIN_TRADES_SMART = 50          # Minimum resolved trades to qualify as smart money
MIN_WR_SMART = 0.65            # Minimum win rate for smart money status
MIN_WR_SIGNAL = 0.60           # Minimum WR to generate any signal at all
WHALE_THRESHOLD_USD = 10000    # Position > $10K = whale
ENTRY_RECENCY_HOURS = 48       # Only signal entries from last 48 hours
SIGNAL_COOLDOWN_HOURS = 24     # Don't re-signal same wallet+market within 24h
MAX_TRACKED_WALLETS = 200      # Cap to prevent unbounded growth

# Wallet tiers
TIER_WHALE = "whale"           # >$100K portfolio, 65%+ WR
TIER_SHARK = "shark"           # >$10K portfolio, 65%+ WR
TIER_SMART = "smart"           # 65%+ WR, 50+ trades
TIER_PROMISING = "promising"   # 60-65% WR, 30+ trades
TIER_UNKNOWN = "unknown"       # Insufficient data


def default_wallet_db() -> dict:
    """Create an empty wallet database."""
    return {
        "version": 1,
        "wallets": {},
        "signals": [],
        "last_full_update": None,
        "stats": {
            "total_wallets": 0,
            "smart_money_count": 0,
            "signals_generated": 0,
        },
    }


def load_wallet_db() -> dict:
    """Load wallet database from disk."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if WALLET_DB_FILE.exists():
        try:
            with open(WALLET_DB_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return default_wallet_db()


def save_wallet_db(db: dict):
    """Atomically save wallet database."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(WALLET_DB_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(db, f, indent=2)
    os.replace(tmp, str(WALLET_DB_FILE))


def classify_wallet(wallet: dict) -> str:
    """Classify a wallet into tiers based on performance data.

    Args:
        wallet: Dict with trades_total, trades_won, portfolio_value_usd.

    Returns:
        Tier string (whale/shark/smart/promising/unknown).
    """
    total = wallet.get("trades_total", 0)
    won = wallet.get("trades_won", 0)
    portfolio = wallet.get("portfolio_value_usd", 0)

    if total < 20:
        return TIER_UNKNOWN

    wr = won / total if total > 0 else 0

    if wr >= MIN_WR_SMART and portfolio >= 100000 and total >= MIN_TRADES_SMART:
        return TIER_WHALE
    elif wr >= MIN_WR_SMART and portfolio >= 10000 and total >= MIN_TRADES_SMART:
        return TIER_SHARK
    elif wr >= MIN_WR_SMART and total >= MIN_TRADES_SMART:
        return TIER_SMART
    elif wr >= MIN_WR_SIGNAL and total >= 30:
        return TIER_PROMISING
    else:
        return TIER_UNKNOWN


def add_wallet(address: str, alias: str = "", initial_data: dict = None) -> dict:
    """Add a wallet to the tracking database.

    Args:
        address: Wallet address (0x...).
        alias: Human-readable name.
        initial_data: Optional dict with known stats (trades_total, trades_won, etc.).

    Returns:
        The wallet entry.
    """
    db = load_wallet_db()

    if len(db["wallets"]) >= MAX_TRACKED_WALLETS and address not in db["wallets"]:
        # Evict lowest-tier wallet
        worst = None
        worst_score = float("inf")
        for addr, w in db["wallets"].items():
            score = w.get("trades_won", 0)
            if score < worst_score:
                worst_score = score
                worst = addr
        if worst:
            del db["wallets"][worst]

    wallet = db["wallets"].get(address, {
        "address": address,
        "alias": alias,
        "added_at": now(),
        "last_updated": None,
        "trades_total": 0,
        "trades_won": 0,
        "trades_lost": 0,
        "portfolio_value_usd": 0,
        "active_positions": [],
        "recent_entries": [],
        "tier": TIER_UNKNOWN,
        "win_rate": 0.0,
        "wilson_lower": 0.0,
        "notes": "",
    })

    if initial_data:
        wallet.update({k: v for k, v in initial_data.items() if k != "address"})

    if alias:
        wallet["alias"] = alias

    # Recompute derived fields
    total = wallet.get("trades_total", 0)
    won = wallet.get("trades_won", 0)
    wallet["win_rate"] = round(won / total, 4) if total > 0 else 0.0
    wallet["wilson_lower"] = wilson_lower(won, total)
    wallet["tier"] = classify_wallet(wallet)

    db["wallets"][address] = wallet
    db["stats"]["total_wallets"] = len(db["wallets"])
    db["stats"]["smart_money_count"] = sum(
        1 for w in db["wallets"].values()
        if w.get("tier") in (TIER_WHALE, TIER_SHARK, TIER_SMART)
    )

    save_wallet_db(db)
    return wallet


def profile_wallet(address: str) -> dict:
    """Get the full profile for a tracked wallet.

    Returns wallet data with computed metrics, or error if not tracked.
    """
    db = load_wallet_db()
    wallet = db["wallets"].get(address)
    if not wallet:
        return {"error": f"Wallet {address} not tracked. Use add-wallet first."}

    total = wallet.get("trades_total", 0)
    won = wallet.get("trades_won", 0)

    profile = {
        **wallet,
        "win_rate": round(won / total, 4) if total > 0 else 0,
        "wilson_lower": wilson_lower(won, total),
        "tier": classify_wallet(wallet),
        "is_smart_money": classify_wallet(wallet) in (TIER_WHALE, TIER_SHARK, TIER_SMART),
        "confidence": "high" if total >= 100 else "medium" if total >= 50 else "low",
    }

    return profile


def record_wallet_entry(address: str, market_id: str, direction: str,
                        amount_usd: float, price: float, market_title: str = "") -> dict:
    """Record a new position entry by a tracked wallet.

    This is called when we detect a wallet taking a new position.
    Generates a signal if the wallet qualifies as smart money.
    """
    db = load_wallet_db()
    wallet = db["wallets"].get(address)
    if not wallet:
        return {"error": f"Wallet {address} not tracked"}

    entry = {
        "market_id": market_id,
        "market_title": market_title,
        "direction": direction,
        "amount_usd": round(amount_usd, 2),
        "price": round(price, 4),
        "timestamp": now(),
    }

    # Add to recent entries (keep last 50)
    wallet.setdefault("recent_entries", [])
    wallet["recent_entries"].append(entry)
    wallet["recent_entries"] = wallet["recent_entries"][-50:]

    # Generate signal if smart money
    signal = None
    tier = classify_wallet(wallet)
    if tier in (TIER_WHALE, TIER_SHARK, TIER_SMART):
        # Check cooldown
        recent_signals = [
            s for s in db.get("signals", [])
            if s.get("address") == address
            and s.get("market_id") == market_id
        ]
        # Parse timestamps for cooldown check
        in_cooldown = False
        for s in recent_signals:
            try:
                sig_time = datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - sig_time).total_seconds() < SIGNAL_COOLDOWN_HOURS * 3600:
                    in_cooldown = True
                    break
            except (ValueError, KeyError):
                continue

        if not in_cooldown:
            # Compute signal strength
            wr = wallet.get("trades_won", 0) / max(wallet.get("trades_total", 1), 1)
            wl = wilson_lower(wallet.get("trades_won", 0), wallet.get("trades_total", 0))

            # Signal strength = Wilson lower * tier multiplier * amount factor
            tier_mult = {TIER_WHALE: 1.5, TIER_SHARK: 1.2, TIER_SMART: 1.0}.get(tier, 0.5)
            amount_factor = min(amount_usd / 1000, 2.0)  # Cap at 2x for $2K+ trades
            strength = round(wl * tier_mult * max(amount_factor, 0.5), 4)

            signal = {
                "type": "smart_money_entry",
                "address": address,
                "alias": wallet.get("alias", ""),
                "tier": tier,
                "market_id": market_id,
                "market_title": market_title,
                "direction": direction,
                "amount_usd": round(amount_usd, 2),
                "price": round(price, 4),
                "win_rate": round(wr, 4),
                "wilson_lower": wl,
                "signal_strength": strength,
                "timestamp": now(),
            }

            db.setdefault("signals", [])
            db["signals"].append(signal)
            db["signals"] = db["signals"][-500:]  # Keep last 500 signals
            db["stats"]["signals_generated"] = db["stats"].get("signals_generated", 0) + 1

    db["wallets"][address] = wallet
    save_wallet_db(db)

    return {
        "recorded": True,
        "entry": entry,
        "signal": signal,
        "wallet_tier": tier,
    }


def record_trade_outcome(address: str, market_id: str, won: bool, pnl: float = 0) -> dict:
    """Record a resolved trade outcome for a wallet.

    Updates the wallet's win/loss stats and reclassifies tier.
    """
    db = load_wallet_db()
    wallet = db["wallets"].get(address)
    if not wallet:
        return {"error": f"Wallet {address} not tracked"}

    wallet["trades_total"] = wallet.get("trades_total", 0) + 1
    if won:
        wallet["trades_won"] = wallet.get("trades_won", 0) + 1
    else:
        wallet["trades_lost"] = wallet.get("trades_lost", 0) + 1

    wallet["win_rate"] = round(
        wallet["trades_won"] / wallet["trades_total"], 4
    )
    wallet["wilson_lower"] = wilson_lower(wallet["trades_won"], wallet["trades_total"])
    wallet["tier"] = classify_wallet(wallet)
    wallet["last_updated"] = now()

    db["wallets"][address] = wallet
    db["stats"]["smart_money_count"] = sum(
        1 for w in db["wallets"].values()
        if w.get("tier") in (TIER_WHALE, TIER_SHARK, TIER_SMART)
    )
    save_wallet_db(db)

    return {
        "updated": True,
        "address": address,
        "new_win_rate": wallet["win_rate"],
        "new_tier": wallet["tier"],
        "trades_total": wallet["trades_total"],
    }


def get_signals(min_wr: float = MIN_WR_SIGNAL, min_trades: int = 30,
                hours: float = ENTRY_RECENCY_HOURS) -> list:
    """Get recent smart money signals, filtered by quality.

    Returns signals from wallets that meet minimum WR and trade count thresholds.
    Only includes signals from the last `hours` hours.
    """
    db = load_wallet_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    signals = []
    for s in db.get("signals", []):
        if s.get("timestamp", "") < cutoff:
            continue
        if s.get("win_rate", 0) < min_wr:
            continue
        # Check wallet still meets criteria
        wallet = db["wallets"].get(s.get("address", ""))
        if wallet and wallet.get("trades_total", 0) >= min_trades:
            signals.append(s)

    # Sort by signal strength descending
    signals.sort(key=lambda s: s.get("signal_strength", 0), reverse=True)
    return signals


def enrich_market(market_id: str) -> dict:
    """Enrich a market with smart money data.

    Checks if any tracked smart money wallets have positions on this market.
    Returns an enrichment dict suitable for adding to conviction scoring.
    """
    db = load_wallet_db()

    smart_entries = []
    for address, wallet in db["wallets"].items():
        if wallet.get("tier") in (TIER_WHALE, TIER_SHARK, TIER_SMART):
            for entry in wallet.get("recent_entries", []):
                if entry.get("market_id") == market_id:
                    smart_entries.append({
                        "address": address,
                        "alias": wallet.get("alias", ""),
                        "tier": wallet["tier"],
                        "direction": entry.get("direction"),
                        "amount_usd": entry.get("amount_usd", 0),
                        "win_rate": wallet.get("win_rate", 0),
                        "wilson_lower": wallet.get("wilson_lower", 0),
                    })

    if not smart_entries:
        return {
            "market_id": market_id,
            "smart_money_present": False,
            "conviction_boost": 0.0,
            "entries": [],
        }

    # Compute conviction boost
    # More smart money wallets agreeing = higher conviction
    directions = {}
    for e in smart_entries:
        d = e.get("direction", "YES")
        directions[d] = directions.get(d, 0) + 1

    dominant_direction = max(directions, key=directions.get) if directions else "YES"
    agreement_ratio = directions.get(dominant_direction, 0) / len(smart_entries) if smart_entries else 0

    # Weighted by tier and WR
    tier_weights = {TIER_WHALE: 3, TIER_SHARK: 2, TIER_SMART: 1}
    weighted_score = sum(
        tier_weights.get(e["tier"], 0) * e.get("wilson_lower", 0)
        for e in smart_entries
    )
    max_possible = sum(tier_weights.get(e["tier"], 0) for e in smart_entries)

    conviction_boost = round(
        (weighted_score / max_possible) * agreement_ratio if max_possible > 0 else 0, 4
    )

    return {
        "market_id": market_id,
        "smart_money_present": True,
        "smart_money_count": len(smart_entries),
        "dominant_direction": dominant_direction,
        "agreement_ratio": round(agreement_ratio, 3),
        "conviction_boost": conviction_boost,
        "entries": smart_entries,
    }


def get_status() -> dict:
    """Get overall smart money tracker status."""
    db = load_wallet_db()

    wallets_by_tier = {}
    for w in db["wallets"].values():
        tier = w.get("tier", TIER_UNKNOWN)
        wallets_by_tier[tier] = wallets_by_tier.get(tier, 0) + 1

    recent_signals = get_signals(hours=24)

    return {
        "total_wallets": len(db["wallets"]),
        "wallets_by_tier": wallets_by_tier,
        "smart_money_count": db["stats"].get("smart_money_count", 0),
        "total_signals_generated": db["stats"].get("signals_generated", 0),
        "signals_last_24h": len(recent_signals),
        "top_signals": recent_signals[:5],
        "last_full_update": db.get("last_full_update"),
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
        if cmd == "add-wallet":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: add-wallet <address> [--alias NAME]"}))
                sys.exit(1)
            address = sys.argv[2]
            alias = ""
            if "--alias" in sys.argv:
                idx = sys.argv.index("--alias")
                alias = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
            result = add_wallet(address, alias)
            print(json.dumps(result, indent=2))

        elif cmd == "profile":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: profile <address>"}))
                sys.exit(1)
            result = profile_wallet(sys.argv[2])
            print(json.dumps(result, indent=2))

        elif cmd == "signals":
            min_wr = MIN_WR_SIGNAL
            min_trades = 30
            if "--min-wr" in sys.argv:
                idx = sys.argv.index("--min-wr")
                min_wr = float(sys.argv[idx + 1])
            if "--min-trades" in sys.argv:
                idx = sys.argv.index("--min-trades")
                min_trades = int(sys.argv[idx + 1])
            result = get_signals(min_wr, min_trades)
            print(json.dumps({"signals": result, "count": len(result)}, indent=2))

        elif cmd == "enrich":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: enrich <market_id>"}))
                sys.exit(1)
            result = enrich_market(sys.argv[2])
            print(json.dumps(result, indent=2))

        elif cmd == "status":
            result = get_status()
            print(json.dumps(result, indent=2))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
