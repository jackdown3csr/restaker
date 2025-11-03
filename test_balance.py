"""
Test script - Check wallet balance and staking info on Galactica Network
"""

import os
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables (try .env.local first, then .env)
load_dotenv('.env.local')
load_dotenv()

# Setup Web3
RPC_URL = "https://galactica-mainnet.g.alchemy.com/public"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Your wallet address (convert to checksum format)
WALLET_ADDRESS = Web3.to_checksum_address(os.getenv('WALLET_ADDRESS', '0xYOUR_ADDRESS_HERE'))

# Staking contract
STAKING_CONTRACT = Web3.to_checksum_address("0x90B07E15Cfb173726de904ca548dd96f73c12428")

# Minimal ABI
staking_abi = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "showPendingReward",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getStake",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

print("=" * 60)
print("Galactica Network - Balance Check")
print("=" * 60)

# Check connection
if w3.is_connected():
    print(f"✓ Connected to Galactica Network")
    print(f"  Chain ID: {w3.eth.chain_id}")
else:
    print("✗ Failed to connect")
    exit(1)

# Check wallet balance (native GNET)
try:
    balance_wei = w3.eth.get_balance(WALLET_ADDRESS)
    balance_gnet = w3.from_wei(balance_wei, 'ether')
    print(f"\n💰 Wallet Balance:")
    print(f"  Address: {WALLET_ADDRESS}")
    print(f"  Balance: {float(balance_gnet):.6f} GNET")
except Exception as e:
    print(f"✗ Error getting balance: {e}")

# Check staking info
try:
    contract = w3.eth.contract(
        address=STAKING_CONTRACT,
        abi=staking_abi
    )
    
    # Get staked amount
    staked_wei = contract.functions.getStake(WALLET_ADDRESS).call()
    staked_gnet = w3.from_wei(staked_wei, 'ether')
    
    # Get pending rewards
    pending_wei = contract.functions.showPendingReward(WALLET_ADDRESS).call()
    pending_gnet = w3.from_wei(pending_wei, 'ether')
    
    print(f"\n🔒 Staking Info:")
    print(f"  Staked: {float(staked_gnet):.6f} GNET")
    print(f"  Pending Rewards: {float(pending_gnet):.6f} GNET")
    print(f"  Total: {float(staked_gnet) + float(pending_gnet):.6f} GNET")
    
except Exception as e:
    print(f"✗ Error getting staking info: {e}")

print("\n" + "=" * 60)
