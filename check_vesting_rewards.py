"""
Check if there are new vesting rewards to claim from RewardDistributor
"""
from web3 import Web3

RPC_URL = "https://galactica-mainnet.g.alchemy.com/public"
VESTING_PROXY = "0x80BCB71F63f11344F5483d108374fa394A587AbE"
USER_ADDRESS = "0x85830f211C5534eABAFd83b346eb61128a6995c9"

# ABI for RewardDistributor
ABI = [
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "userTotalRewardClaimed",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "currentEpoch",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "userLastClaimedEpoch",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalRewardClaimed",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "rewardMerkleRoot",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# AddEpoch event signature (with 0x prefix)
ADD_EPOCH_TOPIC = "0x" + Web3.keccak(text="AddEpoch(uint256,bytes32,uint256)").hex()

def check_vesting_status():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    if not w3.is_connected():
        print("❌ Cannot connect to RPC")
        return
    
    contract = w3.eth.contract(address=VESTING_PROXY, abi=ABI)
    
    # Read current state
    current_epoch = contract.functions.currentEpoch().call()
    user_last_epoch = contract.functions.userLastClaimedEpoch(USER_ADDRESS).call()
    user_total_claimed = contract.functions.userTotalRewardClaimed(USER_ADDRESS).call()
    total_claimed_all = contract.functions.totalRewardClaimed().call()
    merkle_root = contract.functions.rewardMerkleRoot().call()
    
    print("=" * 60)
    print("🔒 VESTING STATUS (RewardDistributor)")
    print("=" * 60)
    print(f"Contract: {VESTING_PROXY}")
    print(f"User:     {USER_ADDRESS}")
    print()
    print(f"📊 Current epoch:      {current_epoch}")
    print(f"📊 Your last claimed:  {user_last_epoch}")
    print(f"💰 Total claimed (you): {user_total_claimed / 10**18:.6f} GNET")
    print(f"💰 Total claimed (all): {total_claimed_all / 10**18:.6f} GNET")
    print(f"🌳 Merkle root:        {merkle_root.hex()[:20]}...")
    print()
    
    # Check if new epoch available
    if current_epoch > user_last_epoch:
        epochs_behind = current_epoch - user_last_epoch
        print(f"✅ NEW REWARDS AVAILABLE!")
        print(f"   You are {epochs_behind} epoch(s) behind.")
        print(f"   Go to Galactica staking page to claim!")
        return True
    else:
        print("⏳ No new rewards available.")
        print("   You have claimed all available epochs.")
        return False

def get_epoch_history():
    """Get history of epoch additions"""
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    print()
    print("=" * 60)
    print("📜 EPOCH HISTORY")
    print("=" * 60)
    
    current_block = w3.eth.block_number
    
    # Search for AddEpoch events
    logs = w3.eth.get_logs({
        "address": VESTING_PROXY,
        "topics": [ADD_EPOCH_TOPIC],
        "fromBlock": 0,
        "toBlock": current_block
    })
    
    if not logs:
        print("No epoch events found.")
        return
    
    for log in logs:
        block = log['blockNumber']
        # Parse epoch index from topic 1
        epoch_index = int(log['topics'][1].hex(), 16)
        
        # Get block timestamp
        block_data = w3.eth.get_block(block)
        timestamp = block_data['timestamp']
        
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp)
        
        print(f"Epoch {epoch_index}: Block {block} ({dt.strftime('%Y-%m-%d %H:%M:%S')})")

def get_estimated_next_epoch():
    """Estimate when next epoch might be based on history"""
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Get AddEpoch events
    current_block = w3.eth.block_number
    logs = w3.eth.get_logs({
        "address": VESTING_PROXY,
        "topics": [ADD_EPOCH_TOPIC],
        "fromBlock": 0,
        "toBlock": current_block
    })
    
    if len(logs) < 2:
        return None
    
    # Calculate average time between epochs
    from datetime import datetime, timedelta
    
    timestamps = []
    for log in logs:
        block = log['blockNumber']
        block_data = w3.eth.get_block(block)
        timestamps.append(block_data['timestamp'])
    
    # Calculate intervals
    intervals = []
    for i in range(1, len(timestamps)):
        intervals.append(timestamps[i] - timestamps[i-1])
    
    avg_interval = sum(intervals) / len(intervals)
    last_epoch_time = datetime.fromtimestamp(timestamps[-1])
    next_estimate = last_epoch_time + timedelta(seconds=avg_interval)
    
    return next_estimate, avg_interval / 86400  # return date and days


if __name__ == "__main__":
    has_rewards = check_vesting_status()
    get_epoch_history()
    
    # Estimate next epoch
    estimate = get_estimated_next_epoch()
    if estimate:
        next_date, avg_days = estimate
        print()
        print(f"📅 Average epoch interval: ~{avg_days:.1f} days")
        print(f"📅 Estimated next epoch: {next_date.strftime('%Y-%m-%d')}")
    
    print()
    print("=" * 60)
    print("ℹ️  Exact unclaimed amount requires Merkle proof from webapp.")
    print("   Claim at: https://app.galactica.com/gnet-vesting")
    print()
    print("💡 When 'Current epoch > Your last claimed', new rewards await!")
    print("=" * 60)
    
    # Copy-paste summary
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    contract = w3.eth.contract(address=VESTING_PROXY, abi=ABI)
    total_claimed_all = contract.functions.totalRewardClaimed().call()
    current_epoch = contract.functions.currentEpoch().call()
    
    # Get epoch history for summary
    current_block = w3.eth.block_number
    logs = w3.eth.get_logs({
        "address": VESTING_PROXY,
        "topics": [ADD_EPOCH_TOPIC],
        "fromBlock": 0,
        "toBlock": current_block
    })
    
    print()
    print("📋 COPY-PASTE SUMMARY:")
    print(f"Total claimed (all): {total_claimed_all / 10**18:.2f} GNET")
    print(f"Current epoch: {current_epoch}")
    print()
    print("Epoch History:")
    for log in logs:
        epoch_index = int(log['topics'][1].hex(), 16)
        block_data = w3.eth.get_block(log['blockNumber'])
        from datetime import datetime
        dt = datetime.fromtimestamp(block_data['timestamp'])
        print(f"Epoch {epoch_index}: {dt.strftime('%Y-%m-%d')}")
