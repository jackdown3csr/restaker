#!/usr/bin/env python3
"""
GNET Vesting Checker - Check claimable GNET rewards
Uses the gubi-admin API to get merkle proof data and compares with on-chain claimed amount.
"""

import requests
from web3 import Web3
from decimal import Decimal

# Configuration
RPC_URL = "https://galactica-mainnet.g.alchemy.com/public"
CHAIN_ID = 613419
VESTING_CONTRACT = "0x80BCB71F63f11344F5483d108374fa394A587AbE"
API_URL = "https://gubi-admin.galactica.com/api/claim/gnet/{address}?chainId={chain_id}"

# RewardDistributor ABI (minimal)
VESTING_ABI = [
    {
        "inputs": [],
        "name": "currentEpoch",
        "outputs": [{"type": "uint64"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"type": "address", "name": "account"}],
        "name": "userTotalRewardClaimed",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"type": "address", "name": "account"}],
        "name": "userLastClaimedEpoch",
        "outputs": [{"type": "uint64"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "components": [
                    {"name": "leafIndex", "type": "uint256"},
                    {"name": "account", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "merkleProof", "type": "bytes32[]"}
                ],
                "name": "claimInput",
                "type": "tuple"
            }
        ],
        "name": "userUnclaimedReward",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def get_api_claim_data(address: str) -> dict | None:
    """Fetch claim data from gubi-admin API."""
    url = API_URL.format(address=address.lower(), chain_id=CHAIN_ID)
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"API request failed: {e}")
        return None


def check_vesting(address: str):
    """Check GNET vesting status for an address."""
    print("=" * 60)
    print("GNET Vesting Checker")
    print("=" * 60)
    print(f"\nAddress: {address}")
    
    # Connect to RPC
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("❌ Failed to connect to RPC")
        return
    
    # Get contract instance
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(VESTING_CONTRACT),
        abi=VESTING_ABI
    )
    
    checksum_address = Web3.to_checksum_address(address)
    
    # Get on-chain data
    print("\n📊 On-chain data:")
    current_epoch = contract.functions.currentEpoch().call()
    user_last_epoch = contract.functions.userLastClaimedEpoch(checksum_address).call()
    total_claimed_wei = contract.functions.userTotalRewardClaimed(checksum_address).call()
    total_claimed = Decimal(total_claimed_wei) / Decimal(10**18)
    
    print(f"   Current epoch: {current_epoch}")
    print(f"   Your last claimed epoch: {user_last_epoch}")
    print(f"   Total already claimed: {total_claimed:.6f} GNET")
    
    # Get API data (merkle proof)
    print("\n🌐 API data (merkle proof):")
    api_data = get_api_claim_data(address)
    
    if api_data is None:
        print("   ❌ No vesting data found for this address")
        print("   (You may not be eligible for GNET vesting)")
        return
    
    total_entitled_wei = int(api_data['amount'])
    total_entitled = Decimal(total_entitled_wei) / Decimal(10**18)
    leaf_index = api_data['leafIndex']
    merkle_proof = api_data['merkleProof']
    
    print(f"   Leaf index: {leaf_index}")
    print(f"   Total entitled (in merkle tree): {total_entitled:.6f} GNET")
    print(f"   Merkle proof length: {len(merkle_proof)} elements")
    
    # Calculate claimable
    print("\n💰 Claimable calculation:")
    
    # Method 1: Simple calculation
    claimable_simple = total_entitled - total_claimed
    print(f"   Total entitled: {total_entitled:.6f} GNET")
    print(f"   Already claimed: {total_claimed:.6f} GNET")
    print(f"   ─────────────────────────────")
    
    if claimable_simple > 0:
        print(f"   🟢 Claimable now: {claimable_simple:.6f} GNET")
    else:
        print(f"   🔴 Nothing to claim (already claimed all)")
    
    # Method 2: Use contract's userUnclaimedReward function
    print("\n📝 Contract verification:")
    try:
        claim_input = (
            leaf_index,
            checksum_address,
            total_entitled_wei,
            merkle_proof
        )
        unclaimed_wei = contract.functions.userUnclaimedReward(claim_input).call()
        unclaimed = Decimal(unclaimed_wei) / Decimal(10**18)
        print(f"   Contract says unclaimed: {unclaimed:.6f} GNET")
        
        if unclaimed > 0:
            print(f"\n✅ You can claim {unclaimed:.6f} GNET!")
        else:
            print(f"\n⏳ Nothing to claim right now. Wait for next epoch.")
            
    except Exception as e:
        print(f"   ⚠️  Could not verify with contract: {e}")
    
    # Show merkle proof for reference
    print("\n🔐 Merkle proof (for manual claiming):")
    print(f"   leafIndex: {leaf_index}")
    print(f"   amount: {total_entitled_wei}")
    print(f"   proof: {merkle_proof[:2]}... ({len(merkle_proof)} items)")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        address = sys.argv[1]
    else:
        # Default address
        address = "0x85830f211C5534eABAFd83b346eb61128a6995c9"
    
    check_vesting(address)
