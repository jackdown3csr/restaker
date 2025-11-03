# Galactica Auto-Restaking Bot

Python project for automatically claiming and re-staking rewards from Galactica Network staking contract.

## Project Type
- Python script with web3.py
- Excel/CSV history tracking
- Data visualization with matplotlib
- Secure local execution with private key management

## Key Requirements
- Web3 interaction with Galactica mainnet (Chain ID: 613419)
- Claim rewards using `addRewardToStake()` function from Staking contract
- Track history in Excel/CSV format
- Generate charts for staking performance
- Windows Task Scheduler automation support
- Maximum security: private keys stored locally only

## Tech Stack
- Python 3.10+
- web3.py for blockchain interaction
- openpyxl/pandas for Excel export
- matplotlib/plotly for charts
- python-dotenv for environment variables

## Security Notes
- Private keys never leave local machine
- .env file in .gitignore
- No cloud deployment required
