# Galactica Auto-Restaking Bot

Python project for automatically claiming and re-staking rewards from Galactica Network staking contract.

## Project Type
- Python script with web3.py
- CSV history tracking (lightweight, portable)
- Console-only dashboard
- Secure local execution with private key management

## Key Requirements
- Web3 interaction with Galactica mainnet (Chain ID: 613419)
- Two-step restake workflow: `createStake(0)` triggers `updateReward`, then `addRewardToStake()` moves rewards to stake
- Track history in CSV format
- Windows Task Scheduler automation support
- Maximum security: private keys stored locally only

## Tech Stack
- Python 3.10+
- web3.py for blockchain interaction
- pandas for CSV export
- colorama for colored terminal output
- python-dotenv for environment variables

## Security Notes
- Private keys never leave local machine
- .env file in .gitignore
- No cloud deployment required
