#!/usr/bin/env python3
"""
POSITION MANAGER — The phantom position killer.

This is the module that prevents the v1-v3 catastrophe. The root cause was:
    Position counter incremented on ORDER CREATION, not BLOCKCHAIN CONFIRMATION.
    278 phantom positions in 3 hours → forced liquidation → $300 loss.

Rules enforced by this module:
1. A position DOES NOT EXIST until on-chain confirmed
2. Orders have 3 states: PENDING → CONFIRMED | FAILED | EXPIRED
3. PENDING orders count toward exposure BUT NOT toward position count
4. If an order stays PENDING > timeout → auto-mark EXPIRED
5. Every position has a unique ID = market_id + direction + timestamp
6. Reconciliation: compare local state vs on-chain state periodically

Usage:
    python engine/positions.py open <market_id> <direction> <size_usd> <price>
    python engine/positions.py confirm <order_id> [tx_hash]
    python engine/positions.py fail <order_id> [reason]
    python engine/positions.py close <position_id> <exit_price>
    python engine/positions.py list [--status open|pending|all]
    python engine/positions.py reconcile <on_chain_json>
    python engine/positions.py status
    python engine/positions.py expire-stale [--timeout-seconds 300]
"""

import json
import os
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from engine.stats import now, wilson_lower
    from engine.risk import (
        check_exposure, check_drawdown, record_trade_result,
        load_risk_state, MAX_SINGLE_MARKET_PCT, MAX_OPEN_POSITIONS,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now, wilson_lower
    from risk import (
        check_exposure, check_drawdown, record_trade_result,
        load_risk_state, MAX_SINGLE_MARKET_PCT, MAX_OPEN_POSITIONS,
    )

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
POSITIONS_FILE = STATE_DIR / "positions.json"

# --- Order/Position States ---
ORDER_PENDING = "PENDING"        # Submitted to CLOB, not yet on-chain
ORDER_CONFIRMED = "CONFIRMED"    # On-chain confirmed → becomes a POSITION
ORDER_FAILED = "FAILED"          # CLOB rejected or tx reverted
ORDER_EXPIRED = "EXPIRED"        # Timed out waiting for confirmation

POSITION_OPEN = "OPEN"           # Active on-chain position
POSITION_CLOSED = "CLOSED"       # Exited (sold or resolved)

# --- Constants ---
ORDER_TIMEOUT_SECONDS = 300      # 5 minutes to confirm, then expire
MAX_PENDING_ORDERS = 5           # Max concurrent unconfirmed orders
RECONCILE_TOLERANCE_USD = 1.0    # Allow $1 rounding difference in reconciliation


def _gen_order_id(market_id: str, direction: str) -> str:
    """Generate a unique order ID."""
    raw = f"{market_id}_{direction}_{time.time()}"
    return "ORD_" + hashlib.md5(raw.encode()).hexdigest()[:10]


def _gen_position_id(market_id: str, direction: str) -> str:
    """Generate a unique position ID."""
    raw = f"{market_id}_{direction}_{time.time()}"
    return "POS_" + hashlib.md5(raw.encode()).hexdigest()[:10]


def _load_positions() -> dict:
    """Load position state from disk."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if POSITIONS_FILE.exists():
        try:
            with open(POSITIONS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "orders": [],           # Pending/failed/expired orders
        "positions": [],        # Confirmed open positions
        "closed_positions": [], # History of closed positions
        "stats": {
            "total_orders": 0,
            "confirmed_orders": 0,
            "failed_orders": 0,
            "expired_orders": 0,
            "phantom_prevented": 0,  # Times we caught a phantom
        },
    }


def _save_positions(state: dict):
    """Atomically save position state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Trim history to prevent unbounded growth
    state["closed_positions"] = state["closed_positions"][-500:]
    state["orders"] = [o for o in state["orders"]
                       if o["status"] == ORDER_PENDING][-100:] + \
                      [o for o in state["orders"]
                       if o["status"] != ORDER_PENDING][-200:]

    tmp = str(POSITIONS_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, str(POSITIONS_FILE))


def submit_order(
    market_id: str,
    direction: str,
    size_usd: float,
    price: float,
    bankroll: float = 0,
) -> dict:
    """Submit a new order (NOT a position yet).

    The order enters PENDING state. It ONLY becomes a position
    when confirm_order() is called with the on-chain tx hash.

    Pre-flight checks:
    1. Max pending orders not exceeded
    2. Market exposure limit including pending orders
    3. Duplicate detection (same market+direction within 60s)

    Returns:
        Dict with order_id and status, or error.
    """
    state = _load_positions()

    # --- Pre-flight check 1: Max pending orders ---
    pending = [o for o in state["orders"] if o["status"] == ORDER_PENDING]
    if len(pending) >= MAX_PENDING_ORDERS:
        return {
            "error": f"Too many pending orders ({len(pending)}/{MAX_PENDING_ORDERS}). "
                     f"Wait for confirmations or expire stale orders.",
            "pending_count": len(pending),
        }

    # --- Pre-flight check 2: Duplicate detection ---
    now_ts = time.time()
    for o in pending:
        if (o["market_id"] == market_id and o["direction"] == direction
                and now_ts - o.get("submitted_epoch", 0) < 60):
            return {
                "error": f"Duplicate order: {market_id} {direction} submitted <60s ago. "
                         f"Existing order: {o['order_id']}. This prevents phantom positions.",
                "existing_order": o["order_id"],
                "phantom_prevented": True,
            }

    # --- Pre-flight check 3: Exposure including pending ---
    all_exposure = []
    for p in state["positions"]:
        if p["status"] == POSITION_OPEN:
            all_exposure.append({
                "market_id": p["market_id"],
                "category": p.get("category", "unknown"),
                "position_usd": p["size_usd"],
            })
    # Include pending orders as exposure too (conservative)
    for o in pending:
        all_exposure.append({
            "market_id": o["market_id"],
            "category": o.get("category", "unknown"),
            "position_usd": o["size_usd"],
        })

    if bankroll > 0:
        exposure = check_exposure(all_exposure + [{
            "market_id": market_id,
            "category": "unknown",
            "position_usd": size_usd,
        }], bankroll)

        if not exposure.get("can_trade", True):
            return {
                "error": "Exposure limit would be exceeded including pending orders",
                "violations": exposure.get("violations", []),
            }

    # --- Create order ---
    order_id = _gen_order_id(market_id, direction)
    order = {
        "order_id": order_id,
        "market_id": market_id,
        "direction": direction,
        "size_usd": round(size_usd, 2),
        "price": round(price, 4),
        "shares": round(size_usd / price, 2) if price > 0 else 0,
        "status": ORDER_PENDING,
        "submitted_at": now(),
        "submitted_epoch": time.time(),
        "confirmed_at": None,
        "tx_hash": None,
        "fail_reason": None,
    }

    state["orders"].append(order)
    state["stats"]["total_orders"] = state["stats"].get("total_orders", 0) + 1
    _save_positions(state)

    return {
        "order_id": order_id,
        "status": ORDER_PENDING,
        "market_id": market_id,
        "direction": direction,
        "size_usd": round(size_usd, 2),
        "message": "Order PENDING. Call confirm_order() after on-chain confirmation.",
    }


def confirm_order(order_id: str, tx_hash: str = "") -> dict:
    """Confirm an order is on-chain → promote to POSITION.

    THIS is the only way a position is created.
    No confirmation = no position. Period.
    """
    state = _load_positions()

    order = None
    for o in state["orders"]:
        if o["order_id"] == order_id:
            order = o
            break

    if not order:
        return {"error": f"Order {order_id} not found"}

    if order["status"] != ORDER_PENDING:
        return {"error": f"Order {order_id} is {order['status']}, cannot confirm"}

    # Promote to position
    order["status"] = ORDER_CONFIRMED
    order["confirmed_at"] = now()
    order["tx_hash"] = tx_hash

    position_id = _gen_position_id(order["market_id"], order["direction"])
    position = {
        "position_id": position_id,
        "order_id": order_id,
        "market_id": order["market_id"],
        "direction": order["direction"],
        "size_usd": order["size_usd"],
        "entry_price": order["price"],
        "shares": order["shares"],
        "status": POSITION_OPEN,
        "opened_at": now(),
        "tx_hash": tx_hash,
        "current_price": order["price"],
        "unrealized_pnl": 0.0,
        "category": order.get("category", "unknown"),
    }

    state["positions"].append(position)
    state["stats"]["confirmed_orders"] = state["stats"].get("confirmed_orders", 0) + 1
    _save_positions(state)

    return {
        "position_id": position_id,
        "status": POSITION_OPEN,
        "order_id": order_id,
        "market_id": order["market_id"],
        "direction": order["direction"],
        "size_usd": order["size_usd"],
        "message": "Position CONFIRMED and tracked.",
    }


def fail_order(order_id: str, reason: str = "CLOB rejected") -> dict:
    """Mark an order as failed. NO position created.

    This is the critical path that v1-v3 got wrong:
    they incremented the position counter here instead of in confirm_order().
    """
    state = _load_positions()

    for o in state["orders"]:
        if o["order_id"] == order_id:
            if o["status"] != ORDER_PENDING:
                return {"error": f"Order {order_id} is {o['status']}, cannot fail"}

            o["status"] = ORDER_FAILED
            o["fail_reason"] = reason
            state["stats"]["failed_orders"] = state["stats"].get("failed_orders", 0) + 1
            state["stats"]["phantom_prevented"] = state["stats"].get("phantom_prevented", 0) + 1
            _save_positions(state)

            return {
                "order_id": order_id,
                "status": ORDER_FAILED,
                "reason": reason,
                "message": "Order FAILED. No position created. Phantom position prevented.",
            }

    return {"error": f"Order {order_id} not found"}


def close_position(position_id: str, exit_price: float, resolved: bool = False) -> dict:
    """Close an open position and record P&L.

    Args:
        position_id: The position to close.
        exit_price: Price at which position was exited.
        resolved: True if market resolved (vs manual exit).
    """
    state = _load_positions()

    for p in state["positions"]:
        if p["position_id"] == position_id:
            if p["status"] != POSITION_OPEN:
                return {"error": f"Position {position_id} is {p['status']}, cannot close"}

            # Compute P&L
            if p["direction"] == "YES":
                # Bought YES at entry_price, sold/resolved at exit_price
                pnl_per_share = exit_price - p["entry_price"]
            else:
                # Bought NO at (1-entry_price), resolved/sold at (1-exit_price)
                pnl_per_share = (1 - exit_price) - (1 - p["entry_price"])
                # Simplifies to: entry_price - exit_price
                pnl_per_share = p["entry_price"] - exit_price

            pnl = round(pnl_per_share * p["shares"], 2)
            win = pnl > 0

            p["status"] = POSITION_CLOSED
            p["exit_price"] = round(exit_price, 4)
            p["realized_pnl"] = pnl
            p["closed_at"] = now()
            p["resolved"] = resolved

            # Move to closed positions
            state["closed_positions"].append(dict(p))
            state["positions"] = [
                pos for pos in state["positions"]
                if pos["position_id"] != position_id
            ]

            # Record in risk engine
            try:
                record_trade_result(win, pnl)
            except Exception:
                pass

            _save_positions(state)

            return {
                "position_id": position_id,
                "status": POSITION_CLOSED,
                "pnl": pnl,
                "win": win,
                "entry_price": p["entry_price"],
                "exit_price": exit_price,
                "shares": p["shares"],
            }

    return {"error": f"Position {position_id} not found"}


def expire_stale_orders(timeout_seconds: int = ORDER_TIMEOUT_SECONDS) -> dict:
    """Expire pending orders that have been waiting too long.

    This prevents phantom positions from orders that were submitted
    but never confirmed (network issues, CLOB downtime, etc.).
    """
    state = _load_positions()
    cutoff = time.time() - timeout_seconds
    expired = []

    for o in state["orders"]:
        if o["status"] == ORDER_PENDING and o.get("submitted_epoch", 0) < cutoff:
            o["status"] = ORDER_EXPIRED
            o["fail_reason"] = f"Expired after {timeout_seconds}s without confirmation"
            expired.append(o["order_id"])
            state["stats"]["expired_orders"] = state["stats"].get("expired_orders", 0) + 1
            state["stats"]["phantom_prevented"] = state["stats"].get("phantom_prevented", 0) + 1

    _save_positions(state)

    return {
        "expired_count": len(expired),
        "expired_orders": expired,
        "timeout_seconds": timeout_seconds,
        "message": f"Expired {len(expired)} stale orders. No phantom positions created.",
    }


def reconcile(on_chain_positions: list) -> dict:
    """Reconcile local state against on-chain reality.

    This is the safety net: compare what we THINK we have vs what's
    actually on-chain. Any discrepancy is a bug or phantom.

    Args:
        on_chain_positions: List of dicts from chain with:
            - market_id, direction, size, value

    Returns:
        Dict with matches, phantoms (local but not on-chain),
        and orphans (on-chain but not local).
    """
    state = _load_positions()
    local_positions = {
        (p["market_id"], p["direction"]): p
        for p in state["positions"] if p["status"] == POSITION_OPEN
    }
    chain_positions = {
        (p.get("market_id", ""), p.get("direction", "")): p
        for p in on_chain_positions
    }

    matches = []
    phantoms = []  # Local but not on-chain
    orphans = []   # On-chain but not local
    discrepancies = []

    for key, local in local_positions.items():
        if key in chain_positions:
            chain = chain_positions[key]
            chain_size = float(chain.get("size", 0))
            local_size = local.get("shares", 0)

            if abs(chain_size - local_size) <= RECONCILE_TOLERANCE_USD:
                matches.append({"market_id": key[0], "direction": key[1], "status": "MATCH"})
            else:
                discrepancies.append({
                    "market_id": key[0],
                    "direction": key[1],
                    "local_size": local_size,
                    "chain_size": chain_size,
                    "diff": round(chain_size - local_size, 2),
                })
        else:
            phantoms.append({
                "position_id": local["position_id"],
                "market_id": key[0],
                "direction": key[1],
                "local_size": local.get("shares", 0),
                "status": "PHANTOM — exists locally but NOT on-chain",
            })

    for key, chain in chain_positions.items():
        if key not in local_positions:
            orphans.append({
                "market_id": key[0],
                "direction": key[1],
                "chain_size": float(chain.get("size", 0)),
                "status": "ORPHAN — exists on-chain but NOT locally",
            })

    # Auto-close phantoms
    for phantom in phantoms:
        for p in state["positions"]:
            if p["position_id"] == phantom["position_id"]:
                p["status"] = POSITION_CLOSED
                p["closed_at"] = now()
                p["fail_reason"] = "PHANTOM: reconciliation found no on-chain position"
                state["closed_positions"].append(dict(p))
        state["positions"] = [
            p for p in state["positions"]
            if p.get("position_id") != phantom["position_id"]
        ]
        state["stats"]["phantom_prevented"] = state["stats"].get("phantom_prevented", 0) + 1

    _save_positions(state)

    return {
        "matches": len(matches),
        "phantoms": len(phantoms),
        "orphans": len(orphans),
        "discrepancies": len(discrepancies),
        "phantom_details": phantoms,
        "orphan_details": orphans,
        "discrepancy_details": discrepancies,
        "clean": len(phantoms) == 0 and len(orphans) == 0 and len(discrepancies) == 0,
        "reconciled_at": now(),
    }


def get_open_positions() -> list:
    """Get all confirmed open positions (NOT pending orders)."""
    state = _load_positions()
    return [p for p in state["positions"] if p["status"] == POSITION_OPEN]


def get_pending_orders() -> list:
    """Get all pending (unconfirmed) orders."""
    state = _load_positions()
    return [o for o in state["orders"] if o["status"] == ORDER_PENDING]


def get_position_status() -> dict:
    """Get full position management status."""
    state = _load_positions()
    open_pos = [p for p in state["positions"] if p["status"] == POSITION_OPEN]
    pending = [o for o in state["orders"] if o["status"] == ORDER_PENDING]

    total_exposure = sum(p["size_usd"] for p in open_pos)
    total_unrealized = sum(p.get("unrealized_pnl", 0) for p in open_pos)

    # P&L from closed positions
    closed = state.get("closed_positions", [])
    total_realized = sum(p.get("realized_pnl", 0) for p in closed)
    wins = sum(1 for p in closed if p.get("realized_pnl", 0) > 0)

    return {
        "open_positions": len(open_pos),
        "pending_orders": len(pending),
        "total_exposure_usd": round(total_exposure, 2),
        "total_unrealized_pnl": round(total_unrealized, 2),
        "total_realized_pnl": round(total_realized, 2),
        "closed_count": len(closed),
        "win_rate": round(wins / len(closed), 3) if closed else 0,
        "phantoms_prevented": state["stats"].get("phantom_prevented", 0),
        "confirmation_rate": round(
            state["stats"].get("confirmed_orders", 0) /
            max(state["stats"].get("total_orders", 1), 1), 3
        ),
        "positions": open_pos,
        "pending": pending,
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
        if cmd == "open":
            if len(sys.argv) < 6:
                print(json.dumps({"error": "Usage: open <market_id> <direction> <size_usd> <price>"}))
                sys.exit(1)
            bankroll = float(sys.argv[6]) if len(sys.argv) > 6 else 0
            result = submit_order(sys.argv[2], sys.argv[3], float(sys.argv[4]),
                                  float(sys.argv[5]), bankroll)
            print(json.dumps(result, indent=2))

        elif cmd == "confirm":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: confirm <order_id> [tx_hash]"}))
                sys.exit(1)
            tx = sys.argv[3] if len(sys.argv) > 3 else ""
            result = confirm_order(sys.argv[2], tx)
            print(json.dumps(result, indent=2))

        elif cmd == "fail":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: fail <order_id> [reason]"}))
                sys.exit(1)
            reason = sys.argv[3] if len(sys.argv) > 3 else "CLOB rejected"
            result = fail_order(sys.argv[2], reason)
            print(json.dumps(result, indent=2))

        elif cmd == "close":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: close <position_id> <exit_price>"}))
                sys.exit(1)
            result = close_position(sys.argv[2], float(sys.argv[3]))
            print(json.dumps(result, indent=2))

        elif cmd == "list":
            status_filter = "open"
            if "--status" in sys.argv:
                idx = sys.argv.index("--status")
                status_filter = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "open"

            state = _load_positions()
            if status_filter == "open":
                positions = [p for p in state["positions"] if p["status"] == POSITION_OPEN]
            elif status_filter == "pending":
                positions = [o for o in state["orders"] if o["status"] == ORDER_PENDING]
            else:
                positions = state["positions"] + state["orders"]
            print(json.dumps({"positions": positions, "count": len(positions)}, indent=2))

        elif cmd == "reconcile":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: reconcile <on_chain_json>"}))
                sys.exit(1)
            on_chain = json.loads(sys.argv[2])
            result = reconcile(on_chain)
            print(json.dumps(result, indent=2))

        elif cmd == "expire-stale":
            timeout = ORDER_TIMEOUT_SECONDS
            if "--timeout-seconds" in sys.argv:
                idx = sys.argv.index("--timeout-seconds")
                timeout = int(sys.argv[idx + 1])
            result = expire_stale_orders(timeout)
            print(json.dumps(result, indent=2))

        elif cmd == "status":
            result = get_position_status()
            print(json.dumps(result, indent=2))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
