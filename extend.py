"""
Galactica Lock Extender — keeps veGNET at maximum by auto-extending lock.

Usage:
    python extend.py                  # interactive / one-shot extend to max
    python extend.py --dry-run        # simulate without sending tx
    python extend.py --interval 24    # extend every 24 hours (daemon)

Uses the same .env / .env.local secrets as the restaker CLI.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

# ── Config ─────────────────────────────────────────────────────────
RPC_URL = "https://galactica-mainnet.g.alchemy.com/public"
VEGNET_ADDRESS = "0xdFbE5AC59027C6f38ac3E2eDF6292672A8eCffe4"
CHAIN_ID = 613419
EXPLORER = "https://explorer.galactica.com"

WEEK = 7 * 86400  # VotingEscrow rounds to week boundaries
MAX_GAS_GWEI = 50.0
GAS_MULTIPLIER = 1.25

VEGNET_ABI = [
    {"inputs": [], "name": "MAXTIME", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "addr", "type": "address"}], "name": "locked", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "addr", "type": "address"}], "name": "lockEnd", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "addr", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "newUnlockTime", "type": "uint256"}], "name": "increaseUnlockTime", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "value", "type": "uint256"}], "name": "increaseAmount", "outputs": [], "stateMutability": "payable", "type": "function"},
]

# ── Logging ────────────────────────────────────────────────────────
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "extend.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("extend")


class GalacticaExtender:
    """Extend veGNET lock to the maximum possible duration."""

    def __init__(self, *, dry_run: bool = False):
        # Load secrets
        for env_file in [".env.local", ".env"]:
            if Path(env_file).exists():
                load_dotenv(env_file, override=False)

        self.private_key = os.getenv("PRIVATE_KEY", "")
        self.rpc_url = os.getenv("RPC_URL", RPC_URL)
        self.dry_run = dry_run

        if not self.private_key:
            raise SystemExit("PRIVATE_KEY not set — add it to .env or .env.local")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.account = Account.from_key(self.private_key)
        self.address = self.account.address
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(VEGNET_ADDRESS), abi=VEGNET_ABI
        )

        if not self.w3.is_connected():
            raise SystemExit(f"Cannot connect to RPC: {self.rpc_url}")

        chain = self.w3.eth.chain_id
        logger.info(f"Connected — chain {chain}, wallet {self.address}")

    # ── Read state ─────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Read current lock status."""
        locked_wei = self.contract.functions.locked(self.address).call()
        locked_gnet = float(self.w3.from_wei(locked_wei, "ether"))

        lock_end_ts = self.contract.functions.lockEnd(self.address).call()
        maxtime = self.contract.functions.MAXTIME().call()

        vegnet_wei = self.contract.functions.balanceOf(self.address).call()
        vegnet_bal = float(self.w3.from_wei(vegnet_wei, "ether"))

        now = time.time()
        remaining_s = max(lock_end_ts - now, 0)
        days_remaining = remaining_s / 86400

        # Max possible new unlock time (now + MAXTIME, rounded to week)
        max_new_ts = (int(now + maxtime) // WEEK) * WEEK

        return {
            "locked_gnet": locked_gnet,
            "vegnet_balance": vegnet_bal,
            "lock_end_ts": lock_end_ts,
            "lock_end": datetime.fromtimestamp(lock_end_ts, tz=timezone.utc),
            "days_remaining": days_remaining,
            "maxtime_days": maxtime / 86400,
            "max_new_ts": max_new_ts,
            "max_new_end": datetime.fromtimestamp(max_new_ts, tz=timezone.utc),
            "can_extend": max_new_ts > lock_end_ts,
            "extend_days": max((max_new_ts - lock_end_ts) / 86400, 0),
        }

    # ── Extend lock ────────────────────────────────────────────────

    def execute_extend(self) -> dict:
        """Extend lock to the maximum allowed time. Returns result dict."""
        status = self.get_status()

        if status["locked_gnet"] <= 0:
            logger.warning("No active lock found — nothing to extend")
            return {"status": "no_lock", **status}

        if not status["can_extend"]:
            logger.info(
                f"Lock already at max — ends {status['lock_end']:%Y-%m-%d} "
                f"({status['days_remaining']:.0f} days remaining)"
            )
            return {"status": "already_max", **status}

        new_ts = status["max_new_ts"]
        logger.info(
            f"Extending lock: {status['lock_end']:%Y-%m-%d} → "
            f"{status['max_new_end']:%Y-%m-%d} "
            f"(+{status['extend_days']:.0f} days)"
        )

        if self.dry_run:
            logger.info("[DRY RUN] Would send increaseUnlockTime — skipping")
            return {"status": "dry_run", "new_end": status["max_new_end"], **status}

        # Gas check
        gas_price = self.w3.eth.gas_price
        if gas_price > self.w3.to_wei(MAX_GAS_GWEI, "gwei"):
            gwei = float(self.w3.from_wei(gas_price, "gwei"))
            logger.warning(f"Gas too high: {gwei:.1f} Gwei > {MAX_GAS_GWEI} limit")
            return {"status": "gas_high", "gas_gwei": gwei, **status}

        fn = self.contract.functions.increaseUnlockTime(new_ts)

        try:
            nonce = self.w3.eth.get_transaction_count(self.address)
            gas_est = fn.estimate_gas({"from": self.address, "nonce": nonce})
            gas_limit = int(gas_est * GAS_MULTIPLIER) + 20_000

            tx = fn.build_transaction({
                "from": self.address,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": CHAIN_ID,
            })
            signed = self.w3.eth.account.sign_transaction(tx, private_key=self.account.key)
            raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            tx_hex = tx_hash.hex()
            logger.info(f"TX sent: {EXPLORER}/tx/{tx_hex}")

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            gas_used = receipt["gasUsed"]
            gas_cost = float(self.w3.from_wei(gas_used * gas_price, "ether"))

            if receipt["status"] == 1:
                logger.info(
                    f"✓ Lock extended to {status['max_new_end']:%Y-%m-%d} "
                    f"— gas {gas_used:,} ({gas_cost:.6f} GNET)"
                )
                return {
                    "status": "success",
                    "tx_hash": tx_hex,
                    "gas_used": gas_used,
                    "gas_cost_gnet": gas_cost,
                    "new_end": status["max_new_end"],
                    **status,
                }
            else:
                logger.error(f"TX reverted: {tx_hex}")
                return {"status": "reverted", "tx_hash": tx_hex, **status}

        except Exception as e:
            logger.error(f"TX failed: {e}")
            return {"status": "error", "error": str(e), **status}

    # ── Print status ───────────────────────────────────────────────

    def print_status(self):
        s = self.get_status()
        print(f"\n{'═' * 50}")
        print(f"  Galactica Lock Extender")
        print(f"{'═' * 50}")
        print(f"  Wallet:          {self.address}")
        print(f"  Locked:          {s['locked_gnet']:,.4f} GNET")
        print(f"  veGNET balance:  {s['vegnet_balance']:,.4f}")
        print(f"  Lock ends:       {s['lock_end']:%Y-%m-%d %H:%M} UTC")
        print(f"  Days remaining:  {s['days_remaining']:.1f}")
        print(f"  Max lock (days): {s['maxtime_days']:.0f}")
        if s["can_extend"]:
            print(f"  → Can extend by: {s['extend_days']:.0f} days")
            print(f"  → New end date:  {s['max_new_end']:%Y-%m-%d %H:%M} UTC")
        else:
            print(f"  → Already at maximum lock duration")
        print(f"{'═' * 50}\n")


# ── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Galactica Lock Extender — keep veGNET at maximum"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")
    parser.add_argument("--interval", type=int, default=0,
                        help="Re-run every N hours (0 = one-shot)")
    parser.add_argument("--status", action="store_true", help="Print status and exit")
    args = parser.parse_args()

    ext = GalacticaExtender(dry_run=args.dry_run)

    if args.status:
        ext.print_status()
        return

    if args.interval > 0:
        logger.info(f"Running in daemon mode — extend every {args.interval}h")
        while True:
            ext.print_status()
            result = ext.execute_extend()
            logger.info(f"Result: {result['status']}")
            logger.info(f"Next run in {args.interval}h…")
            time.sleep(args.interval * 3600)
    else:
        ext.print_status()
        result = ext.execute_extend()
        logger.info(f"Result: {result['status']}")


if __name__ == "__main__":
    main()
