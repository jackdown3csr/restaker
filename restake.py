"""
Galactica Auto-Restaking Bot
Automatically claims and re-stakes rewards from Galactica Network staking contract.
"""

import os
import sys
import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account
import pandas as pd
from colorama import Fore, init

# Initialize colorama for Windows
init(autoreset=True)

# Load environment variables (try .env.local first, then .env)
load_dotenv('.env.local')
load_dotenv()

class GalacticaRestaker:
    """Main class for auto-restaking Galactica Network rewards"""
    
    def __init__(self, config_path: str = "config.yaml", dry_run: bool = False):
        """Initialize the restaker with configuration"""
        self.config = self._load_config(config_path)
        self.dry_run = dry_run
        self.setup_logging()
        self.w3 = self._setup_web3()
        self.account = self._setup_account()
        self.staking_contract = self._setup_staking_contract()
        # Default to data/history.csv if the config entry is missing
        self.csv_file = (
            self.config.get('export', {}).get('csv_file')
            or 'data/history.csv'
        )
        
        if self.dry_run:
            self.logger.warning(f"{Fore.YELLOW}⚠ DRY RUN MODE - No transactions will be sent!")
        
        self.logger.info(f"{Fore.GREEN}✓ Galactica Restaker initialized successfully")
        self.logger.info(f"Wallet: {self.account.address}")
        self.logger.info(f"Network: {self.config['network']['name']} (Chain ID: {self.config['network']['chain_id']})")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"{Fore.RED}✗ Error loading config: {e}")
            sys.exit(1)
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config['logging']['level'])
        
        # Create logs directory if it doesn't exist
        Path("logs").mkdir(exist_ok=True)
        
        # Configure logging
        handlers = [logging.StreamHandler()]
        
        if self.config['logging']['log_to_file']:
            file_handler = logging.FileHandler(
                self.config['logging']['log_file'],
                encoding='utf-8'
            )
            handlers.append(file_handler)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_web3(self) -> Web3:
        """Setup Web3 connection to Galactica Network"""
        rpc_url = os.getenv('RPC_URL', self.config['network']['rpc_url'])
        
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            if not w3.is_connected():
                raise ConnectionError("Failed to connect to Galactica Network")
            
            # Verify chain ID
            chain_id = w3.eth.chain_id
            expected_chain_id = self.config['network']['chain_id']
            
            if chain_id != expected_chain_id:
                raise ValueError(
                    f"Wrong network! Expected chain ID {expected_chain_id}, got {chain_id}"
                )
            
            self.logger.info(f"{Fore.GREEN}✓ Connected to {self.config['network']['name']}")
            return w3
            
        except Exception as e:
            self.logger.error(f"{Fore.RED}✗ Web3 connection failed: {e}")
            sys.exit(1)
    
    def _setup_account(self) -> Account:
        """Setup wallet account from private key"""
        private_key = os.getenv('PRIVATE_KEY')
        
        if not private_key:
            self.logger.error(f"{Fore.RED}✗ PRIVATE_KEY not found in .env file")
            sys.exit(1)
        
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        try:
            account = Account.from_key(private_key)
            # Address is already in checksum format from Account.from_key()
            return account
        except Exception as e:
            self.logger.error(f"{Fore.RED}✗ Invalid private key: {e}")
            sys.exit(1)
    
    def _setup_staking_contract(self):
        """Setup staking contract instance"""
        contract_address = (
            os.getenv('STAKING_CONTRACT')
            or self.config.get('network', {}).get('staking_contract')
        )
        
        if not contract_address:
            self.logger.error(f"{Fore.RED}✗ Staking contract address not configured")
            sys.exit(1)
        
        # Minimal ABI for the functions we need
        abi = [
            {
                "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
                "name": "addRewardToStake",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "createStake",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
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
            },
            {
                "inputs": [{"internalType": "address", "name": "", "type": "address"}],
                "name": "stakes",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "address", "name": "", "type": "address"}],
                "name": "rewards",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )
        
        self.logger.info(f"{Fore.GREEN}✓ Staking contract loaded: {contract_address}")
        return contract
    
    def get_pending_rewards(self) -> float:
        """Get pending rewards for the wallet"""
        try:
            pending_wei = self.staking_contract.functions.showPendingReward(
                self.account.address
            ).call()
            
            pending_gnet = self.w3.from_wei(pending_wei, 'ether')
            return float(pending_gnet)
            
        except Exception as e:
            self.logger.error(f"{Fore.RED}✗ Error fetching pending rewards: {e}")
            return 0.0
    
    def get_current_stake(self) -> float:
        """Get current staked amount"""
        try:
            stake_wei = self.staking_contract.functions.getStake(
                self.account.address
            ).call()
            
            stake_gnet = self.w3.from_wei(stake_wei, 'ether')
            return float(stake_gnet)
            
        except Exception as e:
            self.logger.error(f"{Fore.RED}✗ Error fetching stake: {e}")
            return 0.0
    
    def get_gas_price(self) -> int:
        """Get current gas price, capped by config max"""
        try:
            gas_price = self.w3.eth.gas_price
            max_gas_price = self.w3.to_wei(
                self.config['gas']['max_gas_price_gwei'],
                'gwei'
            )
            
            if gas_price > max_gas_price:
                self.logger.warning(
                    f"{Fore.YELLOW}⚠ Gas price too high: "
                    f"{self.w3.from_wei(gas_price, 'gwei')} Gwei "
                    f"(max: {self.config['gas']['max_gas_price_gwei']} Gwei)"
                )
                return None
            
            return gas_price
            
        except Exception as e:
            self.logger.error(f"{Fore.RED}✗ Error fetching gas price: {e}")
            return None
    
    def execute_restake(self) -> Optional[Dict[str, Any]]:
        """
        Execute the two-step restake workflow:
        1. Call createStake(value=0) to trigger updateReward modifier
        2. Call addRewardToStake() to move rewards into stake
        
        The Galactica staking contract requires this two-transaction approach because
        addRewardToStake reads from the rewards mapping, which is only populated when
        updateReward runs. createStake(0) triggers updateReward without adding new stake.
        
        Returns:
            Dictionary with transaction details if successful, None if skipped/failed
        """
        try:
            # Check if we have enough rewards to make restaking worthwhile
            pending_rewards = self.get_pending_rewards()
            min_threshold = self.config['restaking']['min_reward_threshold']

            if pending_rewards < min_threshold:
                self.logger.info(
                    f"{Fore.YELLOW}⏭ Skipping restake: "
                    f"{pending_rewards:.4f} GNET < {min_threshold} GNET threshold"
                )
                return None

            self.logger.info(f"{Fore.CYAN}→ Pending rewards: {pending_rewards:.6f} GNET")

            # Verify gas price is within acceptable limits
            gas_price = self.get_gas_price()
            if gas_price is None:
                self.logger.warning(f"{Fore.YELLOW}⚠ Aborting due to high gas price")
                return None

            stake_before = self.get_current_stake()
            nonce = self.w3.eth.get_transaction_count(self.account.address)

            # --- Step 1: createStake(value=0) triggers updateReward modifier ---
            # This populates the rewards mapping with current pending rewards
            try:
                gas_estimate_step1 = self.staking_contract.functions.createStake().estimate_gas({
                    'from': self.account.address,
                    'nonce': nonce,
                    'value': 0,
                    'gasPrice': gas_price
                })
                gas_limit_step1 = int(gas_estimate_step1 * self.config['gas']['gas_limit_multiplier']) + 20000
            except Exception as e:
                self.logger.error(f"{Fore.RED}✗ Gas estimation for createStake failed: {e}")
                return None

            # --- Step 2: addRewardToStake moves rewards into stake ---
            # This must happen after Step 1 completes on-chain
            try:
                gas_estimate_step2 = self.staking_contract.functions.addRewardToStake(
                    self.account.address
                ).estimate_gas({
                    'from': self.account.address,
                    'nonce': nonce + 1,
                    'gasPrice': gas_price
                })
                # Add buffer to gas estimate for safety (multiplier + fixed amount)
                gas_limit_step2 = int(gas_estimate_step2 * self.config['gas']['gas_limit_multiplier']) + 20000
            except Exception as e:
                self.logger.error(f"{Fore.RED}✗ Gas estimation for addRewardToStake failed: {e}")
                return None

            self.logger.debug(
                f"Gas estimates -> Step1: {gas_estimate_step1} (limit {gas_limit_step1}), "
                f"Step2: {gas_estimate_step2} (limit {gas_limit_step2})"
            )

            # --- DRY RUN MODE: Preview transactions without broadcasting ---
            if self.dry_run:
                gas_cost_step1 = gas_limit_step1 * gas_price
                gas_cost_step2 = gas_limit_step2 * gas_price
                total_gas_cost = float(self.w3.from_wei(gas_cost_step1 + gas_cost_step2, 'ether'))

                self.logger.info(f"\n{Fore.YELLOW}{'='*60}")
                self.logger.info(f"{Fore.YELLOW}DRY RUN - Transaction Preview:")
                self.logger.info(f"{Fore.YELLOW}{'='*60}")
                self.logger.info(f"{Fore.CYAN}STEP 1 → createStake(value=0)")
                self.logger.info(f"  Gas limit: {gas_limit_step1:,}")
                self.logger.info(f"  Estimated gas cost: {float(self.w3.from_wei(gas_cost_step1, 'ether')):.6f} GNET")
                self.logger.info(f"{Fore.CYAN}STEP 2 → addRewardToStake()")
                self.logger.info(f"  Gas limit: {gas_limit_step2:,}")
                self.logger.info(f"  Estimated gas cost: {float(self.w3.from_wei(gas_cost_step2, 'ether')):.6f} GNET")
                self.logger.info(f"{Fore.CYAN}Total estimated gas cost: {total_gas_cost:.6f} GNET")
                self.logger.info(f"{Fore.CYAN}Amount to restake: {pending_rewards:.6f} GNET")
                self.logger.info(f"{Fore.CYAN}New total stake: {stake_before + pending_rewards:.6f} GNET")
                self.logger.info(f"{Fore.YELLOW}{'='*60}\n")
                self.logger.warning(f"{Fore.YELLOW}⚠ DRY RUN - Transactions NOT sent!")

                return {
                    'timestamp': datetime.now(),
                    'amount_restaked': pending_rewards,
                    'stake_before': stake_before,
                    'stake_after': stake_before + pending_rewards,
                    'tx_hash': 'DRY_RUN',
                    'gas_used': gas_limit_step1 + gas_limit_step2,
                    'gas_cost': total_gas_cost,
                    'status': 'Dry Run'
                }

            # --- REAL MODE: Build and broadcast transactions ---
            total_gas_used = 0
            total_gas_cost = 0.0

            # Build Step 1 transaction: createStake(value=0)
            # This triggers updateReward() to populate the rewards mapping
            tx1 = self.staking_contract.functions.createStake().build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': gas_limit_step1,
                'gasPrice': gas_price,
                'value': 0,
                'chainId': self.config['network']['chain_id']
            })

            # Sign transaction with private key (happens locally, never leaves machine)
            signed_tx1 = self.w3.eth.account.sign_transaction(tx1, private_key=self.account.key)
            raw_tx1 = signed_tx1.raw_transaction if hasattr(signed_tx1, 'raw_transaction') else signed_tx1.rawTransaction

            # Broadcast Step 1 and wait for confirmation
            self.logger.info(f"{Fore.CYAN}→ STEP 1: createStake(value=0)")
            tx1_hash = self.w3.eth.send_raw_transaction(raw_tx1)
            tx1_hash_hex = tx1_hash.hex()
            self.logger.info(f"  Tx sent: {tx1_hash_hex}")
            receipt1 = self.w3.eth.wait_for_transaction_receipt(tx1_hash, timeout=300)

            if receipt1['status'] != 1:
                self.logger.error(f"{Fore.RED}✗ createStake(0) failed - aborting")
                return {
                    'timestamp': datetime.now(),
                    'amount_restaked': 0,
                    'stake_before': stake_before,
                    'stake_after': stake_before,
                    'tx_hash': tx1_hash_hex,
                    'gas_used': receipt1['gasUsed'],
                    'gas_cost': float(self.w3.from_wei(receipt1['gasUsed'] * gas_price, 'ether')),
                    'status': 'Failed'
                }

            gas_used_step1 = receipt1['gasUsed']
            gas_cost_step1 = float(self.w3.from_wei(gas_used_step1 * gas_price, 'ether'))
            total_gas_used += gas_used_step1
            total_gas_cost += gas_cost_step1

            self.logger.info(f"  ✓ Step 1 confirmed (gas used: {gas_used_step1:,})")

            # Verify rewards are now available in the rewards mapping
            # (updateReward populated this during Step 1 execution)
            rewards_after_step1 = self.staking_contract.functions.rewards(self.account.address).call()
            rewards_after_step1_gnet = float(self.w3.from_wei(rewards_after_step1, 'ether'))

            if rewards_after_step1 == 0:
                self.logger.warning(f"{Fore.YELLOW}⚠ No rewards available after updateReward - skipping addRewardToStake")
                return {
                    'timestamp': datetime.now(),
                    'amount_restaked': 0,
                    'stake_before': stake_before,
                    'stake_after': stake_before,
                    'tx_hash': tx1_hash_hex,
                    'gas_used': total_gas_used,
                    'gas_cost': total_gas_cost,
                    'status': 'NoRewards'
                }

            self.logger.info(f"{Fore.CYAN}→ Rewards ready to restake: {rewards_after_step1_gnet:.6f} GNET")

            # Build Step 2 transaction: addRewardToStake()
            # This moves rewards from the rewards mapping into the stakes mapping
            tx2 = self.staking_contract.functions.addRewardToStake(self.account.address).build_transaction({
                'from': self.account.address,
                'nonce': nonce + 1,
                'gas': gas_limit_step2,
                'gasPrice': gas_price,
                'chainId': self.config['network']['chain_id']
            })

            signed_tx2 = self.w3.eth.account.sign_transaction(tx2, private_key=self.account.key)
            raw_tx2 = signed_tx2.raw_transaction if hasattr(signed_tx2, 'raw_transaction') else signed_tx2.rawTransaction

            self.logger.info(f"{Fore.CYAN}→ STEP 2: addRewardToStake()")
            tx2_hash = self.w3.eth.send_raw_transaction(raw_tx2)
            tx2_hash_hex = tx2_hash.hex()
            self.logger.info(f"  Tx sent: {tx2_hash_hex}")
            receipt2 = self.w3.eth.wait_for_transaction_receipt(tx2_hash, timeout=300)

            if receipt2['status'] != 1:
                self.logger.error(f"{Fore.RED}✗ addRewardToStake failed")
                return {
                    'timestamp': datetime.now(),
                    'amount_restaked': 0,
                    'stake_before': stake_before,
                    'stake_after': stake_before,
                    'tx_hash': tx2_hash_hex,
                    'gas_used': total_gas_used + receipt2['gasUsed'],
                    'gas_cost': total_gas_cost + float(self.w3.from_wei(receipt2['gasUsed'] * gas_price, 'ether')),
                    'status': 'Failed'
                }

            gas_used_step2 = receipt2['gasUsed']
            gas_cost_step2 = float(self.w3.from_wei(gas_used_step2 * gas_price, 'ether'))
            total_gas_used += gas_used_step2
            total_gas_cost += gas_cost_step2

            stake_after = self.get_current_stake()

            self.logger.info(f"{Fore.GREEN}✓ Restake successful!")
            self.logger.info(f"  Amount restaked: {rewards_after_step1_gnet:.6f} GNET")
            self.logger.info(f"  New total stake: {stake_after:.6f} GNET")
            self.logger.info(f"  Gas used: {total_gas_used:,} ({total_gas_cost:.6f} GNET)")
            self.logger.info(f"  Explorer Step1: {self.config['network']['explorer']}tx/{tx1_hash_hex}")
            self.logger.info(f"  Explorer Step2: {self.config['network']['explorer']}tx/{tx2_hash_hex}")

            return {
                'timestamp': datetime.now(),
                'amount_restaked': rewards_after_step1_gnet,
                'stake_before': stake_before,
                'stake_after': stake_after,
                'tx_hash': tx2_hash_hex,
                'gas_used': total_gas_used,
                'gas_cost': total_gas_cost,
                'status': 'Success'
            }

        except ContractLogicError as e:
            self.logger.error(f"{Fore.RED}✗ Contract error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"{Fore.RED}✗ Restake failed: {e}")
            return None
    
    def save_to_history(self, record: Dict[str, Any]):
        """Save restake record to CSV file for historical tracking"""
        if not record:
            return
        
        try:
            csv_path = Path(self.csv_file)
            if csv_path.parent and not csv_path.parent.exists():
                csv_path.parent.mkdir(parents=True, exist_ok=True)

            df_record = pd.DataFrame([{
                'Timestamp': record['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'Amount Restaked (GNET)': record['amount_restaked'],
                'Stake Before': record['stake_before'],
                'Stake After': record['stake_after'],
                'TX Hash': record['tx_hash'],
                'Gas Used': record['gas_used'],
                'Gas Cost (GNET)': record['gas_cost'],
                'Status': record['status']
            }])

            if csv_path.exists():
                df_record.to_csv(csv_path, mode='a', header=False, index=False)
            else:
                df_record.to_csv(csv_path, index=False)

            self.logger.info(f"{Fore.GREEN}✓ History saved to {csv_path}")

        except Exception as e:
            self.logger.error(f"{Fore.RED}✗ Error saving history: {e}")
    

    def run(self):
        """Main execution method"""
        self.logger.info(f"\n{Fore.CYAN}{'='*60}")
        self.logger.info(f"{Fore.CYAN}Galactica Auto-Restaking Bot - Starting")
        self.logger.info(f"{Fore.CYAN}{'='*60}\n")
        
        try:
            # Display current status
            current_stake = self.get_current_stake()
            pending_rewards = self.get_pending_rewards()
            
            self.logger.info(f"{Fore.CYAN}Current Status:")
            self.logger.info(f"  Staked: {current_stake:.6f} GNET")
            self.logger.info(f"  Pending rewards: {pending_rewards:.6f} GNET")
            
            # Execute restake
            result = self.execute_restake()
            
            # Save to history
            if result:
                self.save_to_history(result)
            
            self.logger.info(f"\n{Fore.GREEN}✓ Run completed successfully\n")
            
        except Exception as e:
            self.logger.error(f"\n{Fore.RED}✗ Error during execution: {e}\n")
            raise

def main():
    """Entry point for the script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Galactica Auto-Restaking Bot')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Simulate restake without sending transaction')
    args = parser.parse_args()
    
    try:
        restaker = GalacticaRestaker(dry_run=args.dry_run)
        restaker.run()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}✗ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
