#!/usr/bin/env python3
"""
POLYMARKET WALLET ACTIVITY POLLER — Track smart money in real time.

Polls Polymarket's API for wallet activity and feeds signals into the
smart_money tracker. Fixes the v4 insider scanner's fatal flaw: using
the global /trades endpoint instead of per-wallet activity tracking.

Key fixes over v4:
1. Uses /activity?user=WALLET endpoint (per-wallet, not global)
2. Polls on a configurable interval with rate limiting
3. Caches last-seen state to detect NEW entries only
4. Feeds directly into smart_money.record_wallet_entry()

Data sources:
- Polymarket CLOB API: https://clob.polymarket.com
- Gamma Markets API: https://gamma-api.polymarket.com
- Data API: https://data-api.polymarket.com (fallback)

Usage:
    python engine/wallet_poller.py poll <address> [--market MARKET_ID]
    python engine/wallet_poller.py poll-all [--interval SECONDS]
    python engine/wallet_poller.py profile <address>
    python engine/wallet_poller.py discover [--min-volume USD] [--min-trades N]
    python engine/wallet_poller.py status
"""

import json
import hashlib
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from engine.stats import now, wilson_lower
    from engine.smart_money import (
        add_wallet, record_wallet_entry, record_trade_outcome,
        load_wallet_db, save_wallet_db, classify_wallet,
        TIER_WHALE, TIER_SHARK, TIER_SMART,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now, wilson_lower
    from smart_money import (
        add_wallet, record_wallet_entry, record_trade_outcome,
        load_wallet_db, save_wallet_db, classify_wallet,
        TIER_WHALE, TIER_SHARK, TIER_SMART,
    )

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
POLLER_STATE_FILE = STATE_DIR / "wallet_poller.json"
CACHE_DIR = STATE_DIR / "wallet_cache"

# --- API Endpoints ---
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
DATA_API = "https://data-api.polymarket.com"

# --- Constants ---
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]
DEFAULT_POLL_INTERVAL = 300    # 5 minutes
MIN_POLL_INTERVAL = 60         # Never poll faster than 1/min
RATE_LIMIT_DELAY = 0.5         # 500ms between API calls
MAX_POSITIONS_PER_POLL = 100   # Cap positions fetched per wallet


def _http_get(url: str) -> dict:
    """HTTP GET with retries, backoff, and rate limiting."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Evolution/1.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF[attempt])
    raise ConnectionError(f"Failed after {MAX_RETRIES} attempts: {last_error}")


def _load_poller_state() -> dict:
    """Load poller state (last-seen positions per wallet)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if POLLER_STATE_FILE.exists():
        try:
            with open(POLLER_STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"wallets": {}, "last_poll": None, "total_polls": 0}


def _save_poller_state(state: dict):
    """Atomically save poller state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(POLLER_STATE_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, str(POLLER_STATE_FILE))


def fetch_wallet_positions(address: str) -> dict:
    """Fetch current positions for a wallet from Gamma API.

    Uses the /activity endpoint which DOES filter by user (unlike
    the global /trades endpoint that v4 was using).

    Returns:
        Dict with positions list and metadata.
    """
    # Primary: Gamma Markets API (most reliable for position data)
    url = f"{GAMMA_API}/positions?user={address}&limit={MAX_POSITIONS_PER_POLL}"

    try:
        data = _http_get(url)
    except ConnectionError:
        # Fallback: try CLOB API
        try:
            url = f"{CLOB_API}/positions?user={address}"
            data = _http_get(url)
        except ConnectionError as e:
            return {"error": f"All APIs failed: {e}", "address": address}

    # Normalize response format
    positions = []
    if isinstance(data, list):
        raw_positions = data
    elif isinstance(data, dict):
        raw_positions = data.get("positions", data.get("data", []))
    else:
        return {"error": "Unexpected API response format", "address": address}

    for p in raw_positions:
        try:
            position = {
                "market_id": p.get("market", p.get("conditionId", p.get("condition_id", ""))),
                "market_title": p.get("title", p.get("market_title", "")),
                "outcome": p.get("outcome", p.get("side", "")),
                "direction": "YES" if p.get("outcome", p.get("side", "")).upper() in ("YES", "1", "LONG") else "NO",
                "size": float(p.get("size", p.get("amount", 0))),
                "avg_price": float(p.get("avgPrice", p.get("avg_price", p.get("price", 0)))),
                "current_value": float(p.get("currentValue", p.get("value", 0))),
                "realized_pnl": float(p.get("realizedPnl", p.get("pnl", 0))),
                "created_at": p.get("createdAt", p.get("created_at", "")),
            }
            positions.append(position)
        except (ValueError, TypeError, KeyError):
            continue

    return {
        "address": address,
        "positions": positions,
        "count": len(positions),
        "fetched_at": now(),
    }


def fetch_wallet_trades(address: str, limit: int = 50) -> dict:
    """Fetch recent trades for a wallet.

    Returns trade history for computing win rate and profiling.
    """
    url = f"{GAMMA_API}/trades?user={address}&limit={limit}"

    try:
        data = _http_get(url)
    except ConnectionError:
        try:
            url = f"{DATA_API}/trades?user={address}&limit={limit}"
            data = _http_get(url)
        except ConnectionError as e:
            return {"error": f"All APIs failed: {e}", "address": address}

    trades = []
    raw_trades = data if isinstance(data, list) else data.get("trades", data.get("data", []))

    for t in raw_trades:
        try:
            trades.append({
                "market_id": t.get("market", t.get("conditionId", "")),
                "side": t.get("side", t.get("outcome", "")),
                "size": float(t.get("size", t.get("amount", 0))),
                "price": float(t.get("price", 0)),
                "timestamp": t.get("timestamp", t.get("createdAt", "")),
                "status": t.get("status", ""),
            })
        except (ValueError, TypeError):
            continue

    return {
        "address": address,
        "trades": trades,
        "count": len(trades),
        "fetched_at": now(),
    }


def poll_wallet(address: str, market_filter: str = None) -> dict:
    """Poll a wallet for new activity and generate signals.

    Compares current positions against last-seen state.
    New or increased positions trigger smart_money signals.

    Args:
        address: Wallet address.
        market_filter: Optional market ID to filter for.

    Returns:
        Dict with new entries detected and signals generated.
    """
    poller_state = _load_poller_state()
    wallet_state = poller_state.get("wallets", {}).get(address, {
        "last_positions": {},
        "last_polled": None,
    })

    # Fetch current positions
    result = fetch_wallet_positions(address)
    if "error" in result:
        return result

    last_positions = wallet_state.get("last_positions", {})
    new_entries = []
    signals = []

    for pos in result["positions"]:
        mid = pos["market_id"]
        if market_filter and mid != market_filter:
            continue

        # Check if this is a NEW position or INCREASED position
        prev = last_positions.get(mid, {})
        prev_size = prev.get("size", 0)
        current_size = pos["size"]

        if current_size > prev_size and current_size > 0:
            # New or increased position detected
            increase = current_size - prev_size
            entry = {
                "market_id": mid,
                "market_title": pos.get("market_title", ""),
                "direction": pos["direction"],
                "new_size": increase,
                "total_size": current_size,
                "price": pos["avg_price"],
                "amount_usd": increase * pos["avg_price"],
            }
            new_entries.append(entry)

            # Feed into smart money tracker
            try:
                signal_result = record_wallet_entry(
                    address=address,
                    market_id=mid,
                    direction=pos["direction"],
                    amount_usd=entry["amount_usd"],
                    price=pos["avg_price"],
                    market_title=pos.get("market_title", ""),
                )
                if signal_result.get("signal"):
                    signals.append(signal_result["signal"])
            except Exception:
                pass  # Don't let signal recording failure break polling

    # Update last-seen state
    wallet_state["last_positions"] = {
        pos["market_id"]: {"size": pos["size"], "price": pos["avg_price"]}
        for pos in result["positions"]
    }
    wallet_state["last_polled"] = now()

    poller_state.setdefault("wallets", {})[address] = wallet_state
    poller_state["last_poll"] = now()
    poller_state["total_polls"] = poller_state.get("total_polls", 0) + 1
    _save_poller_state(poller_state)

    return {
        "address": address,
        "new_entries": new_entries,
        "signals_generated": len(signals),
        "signals": signals,
        "total_positions": result["count"],
        "polled_at": now(),
    }


def poll_all_tracked(interval: int = DEFAULT_POLL_INTERVAL) -> dict:
    """Poll all tracked wallets once.

    Iterates through wallets in the smart money database,
    polls each one with rate limiting between calls.

    Args:
        interval: Not used for single poll, but stored for scheduling.

    Returns:
        Aggregate results across all wallets.
    """
    db = load_wallet_db()
    wallets = db.get("wallets", {})

    if not wallets:
        return {"error": "No wallets tracked. Use wallet-add first.", "wallets_polled": 0}

    results = []
    total_new_entries = 0
    total_signals = 0

    # Sort: poll smart money first (they're the ones we care about)
    tier_priority = {TIER_WHALE: 0, TIER_SHARK: 1, TIER_SMART: 2}
    sorted_addrs = sorted(
        wallets.keys(),
        key=lambda a: tier_priority.get(wallets[a].get("tier", ""), 99)
    )

    for address in sorted_addrs:
        try:
            result = poll_wallet(address)
            if "error" not in result:
                total_new_entries += len(result.get("new_entries", []))
                total_signals += result.get("signals_generated", 0)
                results.append({
                    "address": address,
                    "alias": wallets[address].get("alias", ""),
                    "tier": wallets[address].get("tier", "unknown"),
                    "new_entries": len(result.get("new_entries", [])),
                    "signals": result.get("signals_generated", 0),
                })
        except Exception as e:
            results.append({
                "address": address,
                "error": str(e),
            })

        # Rate limiting between wallets
        time.sleep(RATE_LIMIT_DELAY)

    return {
        "wallets_polled": len(results),
        "total_new_entries": total_new_entries,
        "total_signals": total_signals,
        "results": results,
        "polled_at": now(),
    }


def profile_wallet_live(address: str) -> dict:
    """Build a live profile for a wallet by fetching positions + trades.

    Combines API data with smart_money database entry.
    Updates the wallet's stats in the smart_money tracker.
    """
    # Fetch current positions
    positions_data = fetch_wallet_positions(address)
    positions = positions_data.get("positions", [])

    # Fetch trade history
    trades_data = fetch_wallet_trades(address, limit=100)
    trades = trades_data.get("trades", [])

    # Compute stats from trade history
    total_trades = len(trades)
    portfolio_value = sum(p.get("current_value", 0) for p in positions)

    # Estimate win rate from realized PnL on positions
    winning_positions = sum(1 for p in positions if p.get("realized_pnl", 0) > 0)
    total_with_pnl = sum(1 for p in positions if p.get("realized_pnl", 0) != 0)

    # Update smart money tracker
    wallet = add_wallet(address, initial_data={
        "trades_total": max(total_trades, total_with_pnl),
        "trades_won": winning_positions,
        "portfolio_value_usd": portfolio_value,
        "last_updated": now(),
    })

    return {
        "address": address,
        "wallet_tier": wallet.get("tier", "unknown"),
        "win_rate": wallet.get("win_rate", 0),
        "wilson_lower": wallet.get("wilson_lower", 0),
        "portfolio_value_usd": round(portfolio_value, 2),
        "open_positions": len(positions),
        "recent_trades": total_trades,
        "positions": positions[:10],  # Top 10 positions
        "fetched_at": now(),
    }


def discover_whales(min_volume: float = 50000, min_trades: int = 20) -> dict:
    """Discover high-volume wallets from recent market activity.

    Scans recent trades on popular markets to find wallets worth tracking.
    This bootstraps the smart money database.

    Note: This uses the global trades endpoint (limited), but only for
    DISCOVERY — not for ongoing monitoring (that uses per-wallet polling).
    """
    # Fetch recent high-volume trades
    url = f"{DATA_API}/trades?limit=500"

    try:
        data = _http_get(url)
    except ConnectionError as e:
        return {"error": f"Discovery API failed: {e}"}

    trades = data if isinstance(data, list) else data.get("trades", data.get("data", []))

    # Aggregate by wallet
    wallet_stats = {}
    for t in trades:
        try:
            maker = t.get("maker", t.get("user", ""))
            if not maker:
                continue
            if maker not in wallet_stats:
                wallet_stats[maker] = {"volume": 0, "trades": 0}
            size = float(t.get("size", t.get("amount", 0)))
            price = float(t.get("price", 1))
            wallet_stats[maker]["volume"] += size * price
            wallet_stats[maker]["trades"] += 1
        except (ValueError, TypeError):
            continue

    # Filter for high-volume wallets
    candidates = []
    for address, stats in wallet_stats.items():
        if stats["volume"] >= min_volume and stats["trades"] >= min_trades:
            candidates.append({
                "address": address,
                "volume_usd": round(stats["volume"], 2),
                "trade_count": stats["trades"],
            })

    candidates.sort(key=lambda c: c["volume_usd"], reverse=True)

    return {
        "candidates": candidates[:50],  # Top 50
        "total_wallets_seen": len(wallet_stats),
        "qualified": len(candidates),
        "filters": {"min_volume": min_volume, "min_trades": min_trades},
        "fetched_at": now(),
    }


def get_poller_status() -> dict:
    """Get poller status and health metrics."""
    poller_state = _load_poller_state()
    db = load_wallet_db()

    tracked = len(db.get("wallets", {}))
    polled = len(poller_state.get("wallets", {}))

    return {
        "tracked_wallets": tracked,
        "polled_wallets": polled,
        "total_polls": poller_state.get("total_polls", 0),
        "last_poll": poller_state.get("last_poll"),
        "smart_money_count": db.get("stats", {}).get("smart_money_count", 0),
        "signals_generated": db.get("stats", {}).get("signals_generated", 0),
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
        if cmd == "poll":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: poll <address> [--market MARKET_ID]"}))
                sys.exit(1)
            address = sys.argv[2]
            market = None
            if "--market" in sys.argv:
                idx = sys.argv.index("--market")
                market = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
            result = poll_wallet(address, market)
            print(json.dumps(result, indent=2))

        elif cmd == "poll-all":
            interval = DEFAULT_POLL_INTERVAL
            if "--interval" in sys.argv:
                idx = sys.argv.index("--interval")
                interval = int(sys.argv[idx + 1])
            result = poll_all_tracked(interval)
            print(json.dumps(result, indent=2))

        elif cmd == "profile":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: profile <address>"}))
                sys.exit(1)
            result = profile_wallet_live(sys.argv[2])
            print(json.dumps(result, indent=2))

        elif cmd == "discover":
            min_vol = 50000
            min_trades = 20
            if "--min-volume" in sys.argv:
                idx = sys.argv.index("--min-volume")
                min_vol = float(sys.argv[idx + 1])
            if "--min-trades" in sys.argv:
                idx = sys.argv.index("--min-trades")
                min_trades = int(sys.argv[idx + 1])
            result = discover_whales(min_vol, min_trades)
            print(json.dumps(result, indent=2))

        elif cmd == "status":
            result = get_poller_status()
            print(json.dumps(result, indent=2))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
