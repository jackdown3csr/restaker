<div align="center">

# 🔒 Galactica veGNET Lock Extender

**Automatically keep your veGNET lock at maximum — maximize your gUBI rewards**

[![GitHub release](https://img.shields.io/github/v/release/jackdown3csr/restaker?style=for-the-badge&color=blue)](https://github.com/jackdown3csr/restaker/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6.svg?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)

[**📥 Download Latest Release**](https://github.com/jackdown3csr/restaker/releases/latest)

</div>

---

## What Does It Do?

veGNET decays linearly over time. To keep your **maximum gUBI share**, you need to regularly extend your lock to the 730-day maximum. This tool does it automatically.

It calls `increaseUnlockTime()` on the [veGNET contract](https://explorer.galactica.com/address/0xdFbE5AC59027C6f38ac3E2eDF6292672A8eCffe4) to push your unlock date to the maximum (now + 730 days). Gas cost is negligible (~0.00002 GNET per tx).

---

## Quick Start

### Option A: Download EXE (easiest)

[**📥 Download GalacticaExtender.exe**](https://github.com/jackdown3csr/restaker/releases/latest) — no Python needed, just run it.

### Option B: Run from source

```cmd
git clone https://github.com/jackdown3csr/restaker.git
cd restaker
pip install -r requirements.txt
python extend_gui.py
```

On first run you'll enter your wallet address and private key. The key is encrypted with **Windows DPAPI** and never leaves your computer. All code is open source — [audit it yourself](SECURITY.md).

After setup the app minimizes to your **system tray** and extends your lock automatically on a schedule.

---

## Features

| | |
|---|---|
| **Dashboard** | Locked GNET, veGNET balance, days remaining, lock end date, one-click Extend |
| **gUBI tab** | Live rank, SoulScore, monthly reward, pool value, composition — powered by Galactica API |
| **Vesting checker** | Notifies you when a new vesting epoch is available to claim; shows total GNET claimed |
| **Auto-extend** | Configurable interval (1 h – 7 days), runs in the background via system tray |
| **Update checker** | Notifies you when a new version is available on GitHub |
| **Autostart** | Optional "Start on Windows login" via Task Scheduler |
| **Security** | Private key encrypted with DPAPI, never stored in plaintext |

> 💡 If you previously used the Restaker GUI, your wallet is imported automatically on first run.

---

## Links

- [Galactica Network](https://galactica.com)
- [veGNET / gUBI](https://app.galactica.com/ve-gnet)
- [Changelog](CHANGELOG.md) · [Security](SECURITY.md)

---

<details>
<summary>📦 Legacy: GNET Auto-Restaker</summary>

> GNET staking ends at the end of February 2026. After that the restaker will no longer work.
> If you have GNET staked, consider locking it as veGNET and using the Lock Extender above.

Last restaker release: [**GalacticaRestaker.exe v2.2.0**](https://github.com/jackdown3csr/restaker/releases/tag/v2.2.0)

</details>

---

## License

MIT

<div align="center">

**Made with ❤️ for the Galactica community**

</div>
