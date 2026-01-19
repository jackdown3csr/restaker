<div align="center">

# 🌌 Galactica Auto-Restaking Bot

**Automatically compound your GNET staking rewards**

[![GitHub release](https://img.shields.io/github/v/release/jackdown3csr/restaker?style=for-the-badge&color=blue)](https://github.com/jackdown3csr/restaker/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6.svg?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)

[**📥 Download Latest Release**](https://github.com/jackdown3csr/restaker/releases/latest) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

</div>

---

## ✨ What Does It Do?

This bot automatically claims your pending GNET staking rewards and immediately restakes them - **compounding your gains** without manual intervention.

```
Your Stake: 1000 GNET  →  Pending Reward: 5 GNET  →  Auto-Restaked  →  New Stake: 1005 GNET
```

---

## 🔐 Security First

> **Your private key NEVER leaves your computer.**

| | GUI (v2.1) | CLI (v1.x) |
|--|:--:|:--:|
| Key Storage | 🔒 Windows DPAPI Encrypted | 📄 Local `.env.local` file |
| Same security as | Chrome/Edge passwords | File permissions |

📖 Full details in [SECURITY.md](SECURITY.md) — **all code is open source, audit it yourself!**

---

## 📦 Choose Your Version

<table>
<tr>
<td width="50%" valign="top">

### 🖥️ GUI Application (v2.1)
**Recommended for most users**

✅ One-click setup  
✅ Runs in system tray  
✅ Built-in scheduler  
✅ Desktop notifications  
✅ Encrypted key storage  
✅ Testnet support  
✅ **Vesting reward alerts**  

**Best for:** Set-and-forget users

</td>
<td width="50%" valign="top">

### ⌨️ CLI Script (v1.x)
**For advanced users**

✅ Full control  
✅ Scriptable  
✅ Task Scheduler integration  
✅ Testnet support  
✅ Detailed logging  

**Best for:** Power users, automation

</td>
</tr>
</table>

---

<details open>
<summary><h2>🖥️ GUI Version — Quick Start</h2></summary>

### Option A: Download Ready-to-Run EXE

1. **[📥 Download `GalacticaRestaker.exe`](https://github.com/jackdown3csr/restaker/releases/latest)** from Releases
2. **Run** — First-time setup wizard will appear
3. **Enter your wallet** address and private key
4. **Choose interval** (every 1/6/12/24 hours)
5. **Done!** — App runs in system tray 🎉

> 💡 Your private key is encrypted with Windows DPAPI before being saved.  
> Even administrators cannot decrypt it without your Windows password.

### Option B: Run from Source

```cmd
git clone https://github.com/jackdown3csr/restaker.git
cd restaker
pip install -r requirements.txt
python gui/main.py
```

### System Tray Usage

After setup, the app minimizes to your system tray (near the clock):

- **Galaxy spiral icon** — App is running
- **Right-click** for menu: Start/Pause, Run Now, Settings, Exit

The icon shows a teal galaxy spiral. Status changes are shown via Windows notifications.

### Build Your Own EXE

```cmd
pip install pyinstaller
pyinstaller gui/build.spec
# Output: dist/GalacticaRestaker.exe
```

</details>

---

<details>
<summary><h2>⌨️ CLI Version — Quick Start</h2></summary>

> **Note:** The staking contract (0x90B07E15Cfb173726de904ca548dd96f73c12428) and RPC endpoint are pre-configured in `.env.example`.

### Quick Start
1. **Clone and install**
   ```cmd
   git clone https://github.com/jackdown3csr/restaker.git
   cd restaker
   pip install -r requirements.txt
   ```

2. **Configure secrets** – either run `python setup.py` and follow the prompts or create `.env.local` manually:
   ```env
   PRIVATE_KEY=0xYOUR_PRIVATE_KEY
   WALLET_ADDRESS=0xYOUR_ADDRESS
   ```
      (The RPC and staking contract are already set in `.env.example`.)
   Running `python setup.py` also lets you tune the minimum reward threshold, gas price cap, and CSV history location while writing everything to `config.yaml` and `.env.local`. On Windows you can optionally run the bundled Task Scheduler helper (see below) after setup completes.

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
3. Choose a trigger (Daily, Weekly, Monthly, or custom interval via Advanced options).
4. Action → Start a program:
   - Program/script: `C:\path\to\python.exe`
   - Arguments: `C:\path\to\restaker\restake.py`
   - Start in: `C:\path\to\restaker`
5. Enable **Run with highest privileges**.

> **Note:** Step 4 should point to whatever interpreter you installed. If you use a different Python location (for example, a virtual environment), replace the path accordingly—the code works with any Python 3.10+ interpreter.

### Scheduler helper (Windows)
- Use `scripts/setup_scheduler.ps1` to auto-register the task without clicking through the UI.
- Example invocation:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/setup_scheduler.ps1 -ScriptPath C:\path\to\restaker\restake.py
   ```
   Add `-RepeatHours 6` or `-StartTime 04:30` (24-hour clock) to customize the schedule.
- Run the command from an elevated PowerShell window so the helper can request **Run with highest privileges** successfully.

## Cassiopeia Testnet
- Separate config/script keep mainnet history pristine.
- Default config lives in `config.testnet.yaml` (RPC: `https://galactica-cassiopeia.g.alchemy.com/public`, chain ID `843843`, contract `0xC0F305b12a73c6c8c6fd0EE0459c93f5C73e1AB3`). Logs go to `logs/restake_testnet.log`, CSV to `data/history_testnet.csv`.
- Create `.env.testnet` alongside `.env.local` if you want different credentials:
   ```env
   PRIVATE_KEY=0xYOUR_TESTNET_PRIVATE_KEY
   WALLET_ADDRESS=0xYOUR_TESTNET_ADDRESS
   ```
   Values fall back to `.env.local` / `.env` when not set.
- Run the bot on Cassiopeia:
   ```cmd
   python restake_testnet.py --dry-run
   python restake_testnet.py
   ```
   Pass `--config` if you clone the template config under a new name or `--env-file` to load extra dotenv files.

## Security Checklist
- `.env.local` remains on disk and is already git-ignored.
- Keep the machine offline from untrusted users; the script signs transactions locally.
- Review Task Scheduler logs and `logs/restake.log` periodically.

## Troubleshooting
- **Missing packages:** re-run `pip install -r requirements.txt`.
- **Gas cap reached:** the bot skips transactions if current gas price exceeds `gas.max_gas_price_gwei` in `config.yaml` (default 50 Gwei).

</details>

---

## 📁 Project Structure

```
restaker/
├── gui/                    # GUI Application (v2.1)
│   ├── main.py            # Entry point
│   ├── config_manager.py  # Encrypted config storage
│   ├── scheduler.py       # APScheduler wrapper
│   ├── setup_dialog.py    # First-run wizard
│   ├── tray.py            # System tray integration
│   └── build.spec         # PyInstaller config
├── scripts/               # Automation helpers
│   └── setup_scheduler.ps1
├── restake.py             # CLI entry point
├── restake_testnet.py     # Testnet launcher
├── dashboard.py           # History viewer
├── setup.py               # Interactive setup wizard
├── config.yaml            # Main configuration
└── config.testnet.yaml    # Testnet configuration
```

---

## 🔗 Links

- **Galactica Network:** [galactica.com](https://galactica.com)
- **Staking Dashboard:** [app.galactica.com/staking](https://app.galactica.com/staking)
- **Chain Info:** Chain ID `613419` (Mainnet) / `843843` (Cassiopeia Testnet)

---

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

| Version | Date | Highlights |
|---------|------|------------|
| **2.1.1** | 2026-01-19 | 🔔 Vesting reward notifications |
| 2.0.2 | 2025-12-10 | Bug fixes, dynamic menu |
| 2.0.0 | 2025-12-09 | 🖥️ GUI App, DPAPI encryption |
| 1.1.0 | 2025-11-05 | Cassiopeia testnet support |
| 1.0.0 | 2025-11-04 | Initial CLI release |

---

## 📄 License

MIT — contribute, fork, or adapt as you wish. Pull requests welcome!

---

<div align="center">

**Made with ❤️ for the Galactica community**

⭐ Star this repo if it helped you!

</div>
