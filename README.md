<div align="center">

# 🔒 Galactica veGNET Lock Extender

**Automatically keep your veGNET lock at maximum — maximize your gUBI rewards**

[![GitHub release](https://img.shields.io/github/v/release/jackdown3csr/restaker?style=for-the-badge&color=blue)](https://github.com/jackdown3csr/restaker/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6.svg?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)

[**📥 Download Latest Release**](https://github.com/jackdown3csr/restaker/releases/latest) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

</div>

---

## ✨ What Does It Do?

veGNET decays linearly over time. To keep your **maximum gUBI share**, you need to regularly extend your lock to the 730-day maximum. This tool does it automatically.

```
Lock: 1000 GNET → veGNET decays daily → Auto-Extend to max → Full veGNET maintained → Maximum gUBI
```

The bot calls `increaseUnlockTime()` on the [veGNET contract](https://explorer.galactica.com/address/0xdFbE5AC59027C6f38ac3E2eDF6292672A8eCffe4) to push your unlock date to the maximum allowed (now + 730 days, rounded to the nearest week). Gas cost is negligible (~0.00002 GNET per tx).

---

## 🔐 Security First

> **Your private key NEVER leaves your computer.**

| | GUI | CLI |
|--|:--:|:--:|
| Key Storage | 🔒 Windows DPAPI Encrypted | 📄 Local `.env.local` file |
| Same security as | Chrome/Edge passwords | File permissions |

📖 Full details in [SECURITY.md](SECURITY.md) — **all code is open source, audit it yourself!**

---

## 📦 Choose Your Version

<table>
<tr>
<td width="50%" valign="top">

### 🖥️ GUI Application
**Recommended for most users**

✅ One-click setup
✅ Dashboard with live stats
✅ Runs in system tray
✅ Built-in scheduler
✅ Desktop notifications
✅ Encrypted key storage
✅ Live log viewer

**Best for:** Set-and-forget users

</td>
<td width="50%" valign="top">

### ⌨️ CLI Script
**For advanced users**

✅ Full control
✅ Scriptable
✅ Task Scheduler integration
✅ `--dry-run` mode
✅ `--status` check
✅ `--interval` daemon mode

**Best for:** Power users, automation

</td>
</tr>
</table>

---

<details open>
<summary><h2>🖥️ GUI Version — Quick Start</h2></summary>

### Run from Source

```cmd
git clone https://github.com/jackdown3csr/restaker.git
cd restaker
pip install -r requirements.txt
python extend_gui.py
```

### What You'll See

The GUI opens with three tabs:

- **Dashboard** — Locked GNET, veGNET balance, days remaining, lock end date, extend button
- **Settings** — Wallet address, private key (DPAPI encrypted), auto-extend interval
- **Log** — Live log output

On first run, if you previously used the Restaker GUI, your wallet is imported automatically.

### System Tray

After setup, the app minimizes to your system tray:

- **Double-click** tray icon to show window
- **Right-click** for menu: Show Window, Extend Now, Quit
- Closing the window hides to tray (scheduler keeps running)

### Build EXE

```cmd
pip install pyinstaller
pyinstaller --onefile --noconsole --name GalacticaExtender extend_gui.py
```

</details>

---

<details open>
<summary><h2>⌨️ CLI Version — Quick Start</h2></summary>

### Setup

```cmd
git clone https://github.com/jackdown3csr/restaker.git
cd restaker
pip install -r requirements.txt
```

Create `.env.local`:
```env
PRIVATE_KEY=0xYOUR_PRIVATE_KEY
WALLET_ADDRESS=0xYOUR_ADDRESS
```

### Usage

```cmd
# Check your lock status
python extend.py --status

# Dry run (preview without sending tx)
python extend.py --dry-run

# Extend once
python extend.py

# Run as daemon (extend every 24 hours)
python extend.py --interval 24
```

### Command-Line Flags

| Flag | Description |
|------|-------------|
| `--status` | Show lock info and exit |
| `--dry-run` | Preview transaction without sending |
| `--interval N` | Run every N hours (daemon mode) |

### Automating with Windows Task Scheduler

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_scheduler.ps1 -ScriptPath C:\path\to\restaker\extend.py
```

Or create a task manually:
1. Program: `C:\path\to\python.exe`
2. Arguments: `C:\path\to\restaker\extend.py`
3. Trigger: Daily / every 24h

</details>

---

## 📁 Project Structure

```
restaker/
├── extend.py              # CLI entry point (Lock Extender)
├── extend_gui.py          # GUI entry point (Lock Extender)
├── requirements.txt       # Python dependencies
├── config.yaml            # Network configuration
├── gui/                   # Legacy: Restaker GUI (v2.2)
│   ├── main.py
│   ├── config_manager.py
│   ├── scheduler.py
│   ├── setup_dialog.py
│   ├── tray.py
│   └── build.spec
├── restake.py             # Legacy: CLI restaker
├── restake_testnet.py     # Legacy: Testnet restaker
├── scripts/
│   └── setup_scheduler.ps1
└── data/
    └── history.csv
```

---

## 🔗 Links

- **Galactica Network:** [galactica.com](https://galactica.com)
- **veGNET / gUBI:** [app.galactica.com/ve-gnet](https://app.galactica.com/ve-gnet)
- **veGNET Contract:** [`0xdFbE5AC59027C6f38ac3E2eDF6292672A8eCffe4`](https://explorer.galactica.com/address/0xdFbE5AC59027C6f38ac3E2eDF6292672A8eCffe4)
- **Chain:** Galactica Mainnet (ID `613419`)

---

<details>
<summary><h2>📦 Legacy: Auto-Restaker (staking ends Feb 2026)</h2></summary>

> **Note:** GNET staking is ending mid-February 2026. The restaker below will stop working after that.
> If you had GNET staked, consider locking it as veGNET and using the Lock Extender above.

### What It Did

Automatically claimed pending GNET staking rewards and restaked them — compounding your gains.

```
Your Stake: 1000 GNET → Pending Reward: 5 GNET → Auto-Restaked → New Stake: 1005 GNET
```

### GUI Version

```cmd
python gui/main.py
```

### CLI Version

```cmd
# Configure
cp .env.example .env.local
# Edit .env.local with your wallet + key

# Dry run
python restake.py --dry-run

# Run
python restake.py
```

### Testnet

```cmd
python restake_testnet.py --dry-run
python restake_testnet.py
```

</details>

---

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

| Version | Date | Highlights |
|---------|------|------------|
| **3.0.0** | 2026-02-10 | 🔒 veGNET Lock Extender (GUI + CLI) |
| 2.2.0 | 2026-02-07 | 📊 Restaker: History viewer, dry-run mode |
| 2.0.0 | 2025-12-09 | 🖥️ Restaker: GUI App, DPAPI encryption |
| 1.0.0 | 2025-11-04 | Initial CLI restaker release |

---

## 📄 License

MIT — contribute, fork, or adapt as you wish. Pull requests welcome!

---

<div align="center">

**Made with ❤️ for the Galactica community**

⭐ Star this repo if it helped you!

</div>
