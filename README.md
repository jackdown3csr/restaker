# Galactica Auto-Restaking Bot

Local Python utility that claims pending rewards from the Galactica staking contract and immediately restakes them back into your position.

## Requirements
- Windows 10/11 for Task Scheduler automation (manual runs work on any OS)
- Python 3.10 or newer (project tested with Python 3.13)
- Your Galactica wallet private key

> **Note:** The staking contract (0x90B07E15Cfb173726de904ca548dd96f73c12428) and RPC endpoint are pre-configured in `.env.example`.

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
   ```
      (The RPC and staking contract are already set in `.env.example`.)
      Running `python setup.py` also lets you tune the minimum reward threshold, gas price cap, and CSV history location while writing everything to `config.yaml` and `.env.local`.

3. **Check pending rewards** (optional sanity check):
   ```cmd
   python test_balance.py
   ```

4. **Dry run the bot** – preview transactions without broadcasting them:
   ```cmd
   python restake.py --dry-run
   ```

5. **Run for real** – execute actual restaking once you're ready:
   ```cmd
   python restake.py
   ```

Each successful run appends to `data/history.csv`. View your performance summary anytime:
```cmd
python dashboard.py
```

## Command-Line Flags

**`python restake.py`**
- **No flags**: Normal operation - checks pending rewards and restakes if above threshold
- **`--dry-run`**: Preview mode - simulates the entire workflow and shows gas estimates without broadcasting transactions. Useful for testing configuration before committing real funds.

Example dry-run output:
```
DRY RUN - Transaction Preview:
STEP 1 → createStake(value=0)
  Gas limit: 85,234
  Estimated gas cost: 0.001234 GNET
STEP 2 → addRewardToStake()
  Gas limit: 92,156
  Estimated gas cost: 0.001456 GNET
Total estimated gas cost: 0.002690 GNET
Amount to restake: 1.234567 GNET
⚠ DRY RUN - Transactions NOT sent!
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
- **Gas cap reached:** the bot skips transactions if current gas price exceeds `gas.max_gas_price_gwei` in `config.yaml` (default 50 Gwei).

## License
MIT – contribute, fork, or adapt as you wish. Pull requests welcome.
