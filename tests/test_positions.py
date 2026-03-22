#!/usr/bin/env python3
"""
Tests for the position manager — the phantom position killer.

These tests validate the exact failure mode that killed v1-v3:
position counting on order creation instead of on-chain confirmation.
"""

import json
import os
import sys
import time
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    monkeypatch.setenv("EVOLUTION_STATE_DIR", str(state_dir))
    monkeypatch.chdir(tmp_path)

    import engine.positions as pos
    import engine.risk as risk

    monkeypatch.setattr(pos, "STATE_DIR", state_dir)
    monkeypatch.setattr(pos, "POSITIONS_FILE", state_dir / "positions.json")
    monkeypatch.setattr(risk, "STATE_DIR", state_dir)
    monkeypatch.setattr(risk, "RISK_STATE_FILE", state_dir / "risk_state.json")

    return state_dir


# ============================================================================
# THE PHANTOM POSITION TEST — This is the v1-v3 bug
# ============================================================================

class TestPhantomPositionPrevention:
    """The core invariant: failed orders MUST NOT create positions."""

    def test_failed_order_creates_no_position(self, isolated_state):
        """THE v1-v3 BUG: CLOB rejects order but position counter increments."""
        from engine.positions import submit_order, fail_order, get_open_positions

        # Submit order
        result = submit_order("market1", "YES", 25.0, 0.50)
        order_id = result["order_id"]
        assert result["status"] == "PENDING"

        # CLOB rejects it (this is where v1-v3 failed)
        fail_result = fail_order(order_id, "CLOB rejected: insufficient liquidity")
        assert fail_result["status"] == "FAILED"
        assert "phantom" in fail_result["message"].lower()

        # THE CRITICAL ASSERTION: no position was created
        positions = get_open_positions()
        assert len(positions) == 0

    def test_expired_order_creates_no_position(self, isolated_state):
        """Orders that time out must not become positions."""
        from engine.positions import submit_order, expire_stale_orders, get_open_positions

        result = submit_order("market2", "NO", 15.0, 0.60)
        assert result["status"] == "PENDING"

        # Expire immediately (timeout=0)
        expired = expire_stale_orders(timeout_seconds=0)
        assert expired["expired_count"] == 1

        positions = get_open_positions()
        assert len(positions) == 0

    def test_only_confirmed_orders_become_positions(self, isolated_state):
        """ONLY confirm_order() creates a position."""
        from engine.positions import submit_order, confirm_order, get_open_positions

        result = submit_order("market3", "YES", 30.0, 0.45)
        order_id = result["order_id"]

        # Before confirmation: no position
        assert len(get_open_positions()) == 0

        # Confirm with tx hash
        confirm_result = confirm_order(order_id, tx_hash="0xabc123def456")
        assert confirm_result["status"] == "OPEN"

        # NOW we have a position
        positions = get_open_positions()
        assert len(positions) == 1
        assert positions[0]["market_id"] == "market3"
        assert positions[0]["tx_hash"] == "0xabc123def456"

    def test_278_phantom_scenario(self, isolated_state):
        """Simulate the v1-v3 catastrophe: 278 rapid orders, all failing."""
        from engine.positions import submit_order, fail_order, get_open_positions, MAX_PENDING_ORDERS

        # Submit up to max pending
        order_ids = []
        for i in range(MAX_PENDING_ORDERS):
            result = submit_order(f"market_{i}", "YES", 5.0, 0.50)
            if "order_id" in result:
                order_ids.append(result["order_id"])

        # Max pending should block further orders
        blocked = submit_order("market_overflow", "YES", 5.0, 0.50)
        assert "error" in blocked
        assert "pending" in blocked["error"].lower()

        # Fail all orders
        for oid in order_ids:
            fail_order(oid)

        # ZERO positions. In v1-v3, this would have been 278.
        assert len(get_open_positions()) == 0


class TestDuplicateOrderPrevention:
    """Prevent duplicate orders to same market+direction within 60s."""

    def test_blocks_duplicate_within_60s(self, isolated_state):
        from engine.positions import submit_order

        result1 = submit_order("market_dup", "YES", 10.0, 0.55)
        assert "order_id" in result1

        # Same market+direction within 60s → blocked
        result2 = submit_order("market_dup", "YES", 10.0, 0.55)
        assert "error" in result2
        assert result2.get("phantom_prevented") is True

    def test_allows_different_direction(self, isolated_state):
        from engine.positions import submit_order

        r1 = submit_order("market_dir", "YES", 10.0, 0.55)
        assert "order_id" in r1

        # Same market, different direction → allowed
        r2 = submit_order("market_dir", "NO", 10.0, 0.45)
        assert "order_id" in r2

    def test_allows_different_market(self, isolated_state):
        from engine.positions import submit_order

        r1 = submit_order("market_a", "YES", 10.0, 0.55)
        assert "order_id" in r1

        r2 = submit_order("market_b", "YES", 10.0, 0.55)
        assert "order_id" in r2


class TestPositionLifecycle:
    """Test the full order → position → close lifecycle."""

    def test_full_winning_trade(self, isolated_state):
        from engine.positions import submit_order, confirm_order, close_position

        # 1. Submit order
        order = submit_order("winner_market", "YES", 20.0, 0.40)
        order_id = order["order_id"]

        # 2. Confirm on-chain
        confirm = confirm_order(order_id, "0xtxhash")
        position_id = confirm["position_id"]
        assert confirm["status"] == "OPEN"

        # 3. Close at profit (bought YES at 0.40, resolved at 1.0)
        close = close_position(position_id, 1.0, resolved=True)
        assert close["win"] is True
        assert close["pnl"] > 0
        # PnL = (1.0 - 0.40) * shares = 0.60 * 50 = 30.0
        assert close["pnl"] == 30.0

    def test_full_losing_trade(self, isolated_state):
        from engine.positions import submit_order, confirm_order, close_position

        order = submit_order("loser_market", "YES", 20.0, 0.60)
        confirm = confirm_order(order["order_id"])
        position_id = confirm["position_id"]

        # Resolved NO (YES shares worth 0)
        close = close_position(position_id, 0.0, resolved=True)
        assert close["win"] is False
        assert close["pnl"] < 0

    def test_no_trade_pnl(self, isolated_state):
        from engine.positions import submit_order, confirm_order, close_position

        order = submit_order("no_market", "NO", 20.0, 0.70)
        # Bought NO at 0.70 (i.e., paid 0.30 per NO share)
        confirm = confirm_order(order["order_id"])
        position_id = confirm["position_id"]

        # Market resolves NO (exit_price for YES = 0.0, so NO wins)
        close = close_position(position_id, 0.0, resolved=True)
        assert close["win"] is True
        assert close["pnl"] > 0

    def test_cannot_close_twice(self, isolated_state):
        from engine.positions import submit_order, confirm_order, close_position

        order = submit_order("close_twice", "YES", 10.0, 0.50)
        confirm = confirm_order(order["order_id"])
        pid = confirm["position_id"]

        close_position(pid, 1.0)
        result = close_position(pid, 1.0)
        assert "error" in result

    def test_cannot_confirm_twice(self, isolated_state):
        from engine.positions import submit_order, confirm_order

        order = submit_order("confirm_twice", "YES", 10.0, 0.50)
        confirm_order(order["order_id"])
        result = confirm_order(order["order_id"])
        assert "error" in result


class TestReconciliation:
    """Test local vs on-chain reconciliation."""

    def test_clean_reconciliation(self, isolated_state):
        from engine.positions import submit_order, confirm_order, reconcile

        order = submit_order("recon_market", "YES", 20.0, 0.50)
        confirm_order(order["order_id"])

        # On-chain matches local
        on_chain = [{"market_id": "recon_market", "direction": "YES", "size": 40.0}]
        result = reconcile(on_chain)
        assert result["clean"] is True
        assert result["phantoms"] == 0

    def test_detects_phantom(self, isolated_state):
        from engine.positions import submit_order, confirm_order, reconcile

        order = submit_order("phantom_test", "YES", 20.0, 0.50)
        confirm_order(order["order_id"])

        # On-chain is EMPTY — our local position is a phantom
        result = reconcile([])
        assert result["phantoms"] == 1
        assert len(result["phantom_details"]) == 1
        assert "PHANTOM" in result["phantom_details"][0]["status"]

    def test_detects_orphan(self, isolated_state):
        from engine.positions import reconcile

        # On-chain has a position we don't know about
        on_chain = [{"market_id": "orphan_market", "direction": "NO", "size": 100}]
        result = reconcile(on_chain)
        assert result["orphans"] == 1

    def test_phantom_auto_closed(self, isolated_state):
        from engine.positions import submit_order, confirm_order, reconcile, get_open_positions

        order = submit_order("auto_close", "YES", 20.0, 0.50)
        confirm_order(order["order_id"])
        assert len(get_open_positions()) == 1

        # Reconcile against empty chain → phantom detected and auto-closed
        reconcile([])
        assert len(get_open_positions()) == 0


class TestPositionStatus:
    """Test position status reporting."""

    def test_status_empty(self, isolated_state):
        from engine.positions import get_position_status

        status = get_position_status()
        assert status["open_positions"] == 0
        assert status["pending_orders"] == 0
        assert status["phantoms_prevented"] == 0

    def test_status_with_positions(self, isolated_state):
        from engine.positions import submit_order, confirm_order, get_position_status

        order = submit_order("status_market", "YES", 25.0, 0.50)
        confirm_order(order["order_id"])

        status = get_position_status()
        assert status["open_positions"] == 1
        assert status["total_exposure_usd"] == 25.0

    def test_phantoms_prevented_counter(self, isolated_state):
        from engine.positions import submit_order, fail_order, get_position_status

        order = submit_order("fail_market", "YES", 10.0, 0.50)
        fail_order(order["order_id"])

        status = get_position_status()
        assert status["phantoms_prevented"] == 1


class TestExposureSafety:
    """Test that pending orders count toward exposure."""

    def test_pending_orders_count_as_exposure(self, isolated_state):
        from engine.positions import submit_order, get_pending_orders

        submit_order("exp_market_1", "YES", 10.0, 0.50)
        submit_order("exp_market_2", "NO", 15.0, 0.40)

        pending = get_pending_orders()
        assert len(pending) == 2
        total = sum(o["size_usd"] for o in pending)
        assert total == 25.0
