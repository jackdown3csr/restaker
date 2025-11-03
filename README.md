# Galactica Auto-Restaking Bot

Local Python utility that claims pending rewards from the Galactica staking contract and immediately restakes them back into your position.

## Requirements
- Windows 10/11 for Task Scheduler automation (manual runs work on any OS)
- Python 3.10 or newer (project tested with Python 3.13)
- Galactica mainnet RPC endpoint and staking contract address

## Quick Start
1. **Clone and install**
   ```cmd
   git clone https://github.com/<your-account>/restaker.git
   cd restaker
   pip install -r requirements.txt
   ```

2. **Configure secrets** – either run `python setup.py` and follow the prompts or create `.env.local` manually:
   ```env
   PRIVATE_KEY=0xYOUR_PRIVATE_KEY
   WALLET_ADDRESS=0xYOUR_ADDRESS
   RPC_URL=https://galactica-mainnet.g.alchemy.com/public
   STAKING_CONTRACT=0xSTAKING_CONTRACT_ADDRESS
   ```

3. **Check pending rewards** (optional sanity check):
   ```cmd
   python test_balance.py
   ```

4. **Dry run the bot** – see the planned transactions without broadcasting them:
   ```cmd
   python restake.py --dry-run
   ```

5. **Run for real** – call without the flag once you are ready:
   ```cmd
   python restake.py
   ```

Each successful run writes a line to `data/history.csv` and the console dashboard can summarize the totals:
```cmd
python dashboard.py
```

## Automating with Windows Task Scheduler
1. Open Task Scheduler (`Win + R`, enter `taskschd.msc`).
2. Create Basic Task → name it "Galactica Auto-Restake".
3. Choose a trigger that matches how often you want to compound (Daily, Hourly, etc.).
4. Action → Start a program:
   - Program/script: `C:\Python313\python.exe`
   - Arguments: `C:\path\to\restaker\restake.py`
   - Start in: `C:\path\to\restaker`
5. Enable **Run with highest privileges**.

> **Note:** Step 4 should point to whatever interpreter you installed. If you use a different Python location (for example, a virtual environment), replace the path accordingly—the code works with any Python 3.10+ interpreter.

## Security Checklist
- `.env.local` remains on disk and is already git-ignored.
- Keep the machine offline from untrusted users; the script signs transactions locally.
- Review Task Scheduler logs and `logs/restake.log` periodically.

## Troubleshooting
- **Missing packages:** re-run `pip install -r requirements.txt`.
- **Connection issues:** verify `RPC_URL` and your internet connection.
- **Gas cap reached:** the bot skips transactions if current gas price exceeds `gas.max_gas_price_gwei` in `config.yaml` (default 50 Gwei).

## License
MIT – contribute, fork, or adapt as you wish. Pull requests welcome.
