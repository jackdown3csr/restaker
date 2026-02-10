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

## 🔐 Security

> **Your private key NEVER leaves your computer.**

- **GUI** — key is encrypted with Windows DPAPI (same protection as Chrome/Edge passwords)
- **CLI** — key lives in your local `.env.local` file

All code is open source — [audit it yourself](SECURITY.md).

---

## 🖥️ GUI — Quick Start

### Option A: Download EXE (easiest)

[**📥 Download GalacticaExtender.exe**](https://github.com/jackdown3csr/restaker/releases/latest) — no Python needed, just run it.

### Option B: Run from source

```cmd
git clone https://github.com/jackdown3csr/restaker.git
cd restaker
pip install -r requirements.txt
python extend_gui.py
```

The GUI has three tabs:

| Tab | What it shows |
|-----|---------------|
| **Dashboard** | Locked GNET, veGNET balance, days remaining, lock end date, Extend button |
| **Settings** | Wallet address, private key (encrypted), auto-extend interval |
| **Log** | Live log output |

After setup the app minimizes to your **system tray** — the scheduler keeps running in the background. Right-click the tray icon for quick actions.

> 💡 On first run, if you previously used the Restaker GUI, your wallet is imported automatically.

### Build EXE

```cmd
pip install pyinstaller
pyinstaller --onefile --noconsole --name GalacticaExtender extend_gui.py
```

---

## ⌨️ CLI — Quick Start

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

Usage:
```cmd
python extend.py --status       # Check your lock status
python extend.py --dry-run      # Preview without sending tx
python extend.py                # Extend once
python extend.py --interval 24  # Run every 24 hours (daemon)
```

### Automate with Task Scheduler

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_scheduler.ps1 -ScriptPath C:\path\to\extend.py
```

---

## 🔗 Links

- **Galactica Network:** [galactica.com](https://galactica.com)
- **veGNET / gUBI:** [app.galactica.com/ve-gnet](https://app.galactica.com/ve-gnet)
- **veGNET Contract:** [`0xdFbE5AC59027C6f38ac3E2eDF6292672A8eCffe4`](https://explorer.galactica.com/address/0xdFbE5AC59027C6f38ac3E2eDF6292672A8eCffe4)
- **Chain:** Galactica Mainnet (ID `613419`)

---

<details>
<summary><h2>📦 Legacy: GNET Auto-Restaker</h2></summary>

> GNET staking ended in February 2026. The restaker no longer works.
> If you had GNET staked, consider locking it as veGNET and using the Lock Extender above.

The restaker automatically claimed pending staking rewards and restaked them to compound your gains.

**GUI:** `python gui/main.py` · **CLI:** `python restake.py` · **Testnet:** `python restake_testnet.py`

| Version | Date | Highlights |
|---------|------|------------|
| 2.2.0 | 2026-02-07 | History viewer, dry-run mode |
| 2.0.0 | 2025-12-09 | GUI App, DPAPI encryption |
| 1.0.0 | 2025-11-04 | Initial CLI release |

</details>

---

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

| Version | Date | Highlights |
|---------|------|------------|
| **1.0.0** | 2026-02-10 | 🔒 veGNET Lock Extender (GUI + CLI) |

---

## 📄 License

MIT — contribute, fork, or adapt as you wish. Pull requests welcome!

<div align="center">

**Made with ❤️ for the Galactica community**

⭐ Star this repo if it helped you!

</div>
