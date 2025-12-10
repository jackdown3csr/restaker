# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
