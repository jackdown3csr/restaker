"""
Vesting rewards checker for GUI notifications.

Checks if new vesting rewards are available to claim from RewardDistributor.
"""

import logging
from typing import Optional, Tuple
from web3 import Web3

logger = logging.getLogger(__name__)

# Mainnet RewardDistributor (Vesting)
VESTING_CONTRACT = "0x80BCB71F63f11344F5483d108374fa394A587AbE"

# Minimal ABI for checking epochs
VESTING_ABI = [
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
]


class VestingChecker:
    """Check for new vesting rewards."""
    
    def __init__(self, rpc_url: str, user_address: str):
        """
        Initialize vesting checker.
        
        Args:
            rpc_url: RPC endpoint URL
            user_address: User's wallet address
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.user_address = Web3.to_checksum_address(user_address)
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(VESTING_CONTRACT),
            abi=VESTING_ABI
        )
        self._last_checked_epoch: Optional[int] = None
    
    def check_new_rewards(self) -> Tuple[bool, int]:
        """
        Check if there are new vesting rewards to claim.
        
        Returns:
            Tuple of (has_new_rewards, epochs_behind)
        """
        try:
            current_epoch = self.contract.functions.currentEpoch().call()
            user_last_epoch = self.contract.functions.userLastClaimedEpoch(
                self.user_address
            ).call()
            
            epochs_behind = current_epoch - user_last_epoch
            has_new = epochs_behind > 0
            
            logger.debug(
                f"Vesting check: current={current_epoch}, "
                f"user_last={user_last_epoch}, behind={epochs_behind}"
            )
            
            return has_new, epochs_behind
            
        except Exception as e:
            logger.warning(f"Failed to check vesting: {e}")
            return False, 0
    
    def check_epoch_changed(self) -> Tuple[bool, int]:
        """
        Check if epoch changed since last check.
        
        Returns:
            Tuple of (epoch_changed, new_epoch)
        """
        try:
            current_epoch = self.contract.functions.currentEpoch().call()
            
            if self._last_checked_epoch is None:
                # First check - just store and don't notify
                self._last_checked_epoch = current_epoch
                return False, current_epoch
            
            if current_epoch > self._last_checked_epoch:
                self._last_checked_epoch = current_epoch
                return True, current_epoch
            
            return False, current_epoch
            
        except Exception as e:
            logger.warning(f"Failed to check epoch: {e}")
            return False, 0
