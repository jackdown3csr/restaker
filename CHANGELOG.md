# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-02-10

### Added
- **veGNET Lock Extender** — new tool replacing the staking restaker
  - `extend.py` — CLI: `--status`, `--dry-run`, `--interval N` (daemon mode)
  - `extend_gui.py` — GUI with Dashboard (live stats), Settings, Log tabs
  - System tray icon with APScheduler auto-extend
  - Auto-imports wallet from Restaker v1 config (DPAPI encrypted)
  - Calls `increaseUnlockTime()` to keep veGNET lock at 730-day maximum

### Changed
- README rewritten — Lock Extender is now the main project
- Old staking Restaker moved to "Legacy" section (staking ends Feb 2026)

## [2.2.0] - 2026-02-07

### Added
- **History Window** — new "📊 History" menu item in system tray opens a sortable table
  of all restake operations with color-coded status rows and summary statistics
- **Dry-run mode** toggle in Settings dialog (simulate transactions without sending)
- **Max gas price** setting exposed in Settings dialog
- **Wallet ↔ key validation** in setup dialog — verifies the private key derives the entered address

### Fixed
- **Critical**: `show_notification("🎁 Vesting Rewards available")` was missing the `message` argument — caused crash
- **Critical**: Autostart registry entry wrote bare `python.exe` without script path
- **Critical**: Explorer URL missing trailing slash in default configs
- Scheduler leaked `BackgroundScheduler` instances on stop/restart cycle
- Settings dialog could be opened multiple times simultaneously (now guarded)
- `_on_toggle` exceptions no longer silently crash the tray
- `_do_restake` now returns meaningful status for all result types (Dry Run, Failed, Skipped)
- Private key removed from `os.environ` immediately after restaker init

### Changed
- Log handler switched to `RotatingFileHandler` (5 MB max, 3 backups)
- GUI settings (min threshold, max gas) now override YAML defaults at runtime
- `ConfigManager.load()` filters unknown keys for forward-compatibility
- Version bumped to 2.2.0

## [2.1.1] - 2026-01-19

### Changed
- Shorter vesting notification text

## [2.1.0] - 2026-01-19

### Added
- **Vesting Reward Notifications** - GUI now monitors the RewardDistributor contract for new vesting epochs
  - Automatic check after each restake operation
  - Desktop notification when new vesting rewards are available to claim
  - Includes link to claim rewards at gubi-admin webapp
- New utility scripts for checking vesting status:
  - `check_vesting_rewards.py` - CLI tool to check current vesting epoch
  - `check_gnet_vesting.py` - Retrieves claimable amount via gubi-admin API

## [2.0.2] - 2025-12-10

### Fixed
- Dynamic menu now shows real-time status updates
- Menu correctly shows "Skipped (below threshold)" when rewards are too low
- Added explorer URL to default config (fixes explorer link errors)
- Notifications now work correctly after successful restake
- Clean exit without SystemExit exception in logs

## [2.0.1] - 2025-12-10

### Fixed
- Exit button in system tray now properly closes the application
- Staking contract address format corrected for proper blockchain communication
- Handle RPC errors gracefully when fetching pending rewards

## [2.0.0] - 2025-12-09

### Added
- **GUI Application** - New system tray application for simplified user experience
  - One-time setup dialog for wallet configuration
  - System tray icon with right-click menu
  - Built-in scheduler (no Task Scheduler needed)
  - Desktop notifications on restake events
  - Start/Pause/Run Now controls
- **Windows DPAPI Encryption** - Private keys are now encrypted using Windows Data Protection API
  - Keys are tied to your Windows user account
  - Same security used by Chrome, Edge for credentials
  - Cannot be decrypted by other users
- **SECURITY.md** - Comprehensive security documentation
- **PyInstaller build spec** - Build standalone .exe without Python
- **Testnet support** in GUI (network selector)

### Fixed
- Default config now includes all required sections (logging, network name)
- Setup dialog window height prevents button label clipping
- Improved tray icon design (galaxy spiral)

### Changed
- Restructured project with `gui/` module
- Updated requirements.txt with GUI dependencies

### Security
- Private keys never stored in plain text (GUI version)
- All encryption happens locally, no network transmission of keys

## [1.1.0] - 2025-11-05

### Added
- **Cassiopeia Testnet Support**
  - New `restake_testnet.py` launcher
  - Separate `config.testnet.yaml` configuration
  - `.env.testnet` for testnet-specific credentials
  - Separate logs and history files for testnet

### Changed
- Refactored environment loading to support multiple dotenv files
- Scripts now accept `--config` and `--env-file` CLI arguments

## [1.0.0] - 2025-11-04

### Added
- Initial release
- Core restaking functionality with web3.py
- Two-step restake workflow: `createStake(0)` → `addRewardToStake()`
- CSV history tracking (`data/history.csv`)
- Console dashboard for viewing stats
- Dry-run mode for transaction preview
- `setup.py` interactive configuration wizard
- Windows Task Scheduler PowerShell helper script
- Colorized terminal output

### Security
- Private keys stored in local `.env.local` (git-ignored)
- All transactions signed locally
- No cloud dependencies

---

## Migration Guide

### Upgrading from v1.x to v2.0

**Option A: Use the new GUI (recommended)**
1. Run `python gui/main.py`
2. Enter your wallet address and private key in the setup dialog
3. Your key will be encrypted and stored securely
4. Remove or keep your `.env.local` - the GUI uses its own encrypted storage

**Option B: Continue using CLI**
- No changes needed - CLI still works exactly as before
- Your `.env.local` configuration remains valid

### Data Compatibility
- History CSV format unchanged - all your previous restake records preserved
- Log format unchanged
- Config YAML format unchanged
