"""Quick utility to inspect wallet balances and pending rewards."""

import os
import sys
from pathlib import Path

import yaml
from colorama import Fore, init
from dotenv import load_dotenv
from web3 import Web3

init(autoreset=True)


STAKING_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "showPendingReward",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getStake",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def load_config() -> dict:
    """Load config.yaml so defaults match the main bot."""
    config_path = Path("config.yaml")
    if not config_path.exists():
        print(f"{Fore.RED}✗ Missing config.yaml – run python setup.py first")
        sys.exit(1)

    with config_path.open() as handle:
        return yaml.safe_load(handle)


def ensure_wallet_present() -> str:
    """Ensure WALLET_ADDRESS is provided before continuing."""
    wallet = os.getenv('WALLET_ADDRESS')
    if not wallet:
        print(f"{Fore.RED}✗ WALLET_ADDRESS not set in .env.local")
        print(f"{Fore.YELLOW}→ Add it by running python setup.py or editing .env.local")
        sys.exit(1)

    if not wallet.startswith('0x'):
        wallet = '0x' + wallet
    return wallet


def main() -> None:
    load_dotenv('.env.local')
    load_dotenv()

    config = load_config()

    rpc_url = os.getenv('RPC_URL') or config['network']['rpc_url']
    staking_contract = (
        os.getenv('STAKING_CONTRACT')
        or config['network'].get('staking_contract')
    )
    if not staking_contract:
        print(f"{Fore.RED}✗ Staking contract address missing from configuration")
        sys.exit(1)

    wallet_raw = ensure_wallet_present()
    wallet_address = Web3.to_checksum_address(wallet_raw)

    print(f"{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.CYAN}Galactica Network – Wallet Diagnostics")
    print(f"{Fore.CYAN}{'=' * 60}")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"{Fore.RED}✗ Unable to reach Galactica RPC: {rpc_url}")
        sys.exit(1)

    print(f"{Fore.GREEN}✓ Connected (Chain ID {w3.eth.chain_id})")
    print(f"  RPC endpoint: {rpc_url}")
    print(f"  Staking contract: {staking_contract}")

    print(f"\n{Fore.WHITE}Wallet: {wallet_address}")

    try:
        balance_gnet = w3.from_wei(w3.eth.get_balance(wallet_address), 'ether')
        print(f"{Fore.GREEN}✓ Wallet balance: {float(balance_gnet):.6f} GNET")
    except Exception as exc:
        print(f"{Fore.RED}✗ Error fetching wallet balance: {exc}")

    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(staking_contract),
            abi=STAKING_ABI,
        )
        staked = w3.from_wei(contract.functions.getStake(wallet_address).call(), 'ether')
        pending = w3.from_wei(
            contract.functions.showPendingReward(wallet_address).call(),
            'ether',
        )

        total = float(staked) + float(pending)
        print(f"{Fore.GREEN}✓ Staked: {float(staked):.6f} GNET")
        print(f"{Fore.GREEN}✓ Pending rewards: {float(pending):.6f} GNET")
        print(f"{Fore.WHITE}  Total exposure: {total:.6f} GNET")
    except Exception as exc:
        print(f"{Fore.RED}✗ Error fetching staking data: {exc}")

    print(f"\n{Fore.CYAN}{'=' * 60}")


if __name__ == "__main__":
    main()
