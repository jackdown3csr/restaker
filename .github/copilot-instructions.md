# Galactica Auto-Restaking Bot — AI Coding Guide

## Big picture architecture
- Two entry points share the same core logic: CLI in [restake.py](restake.py) and GUI in [gui/main.py](gui/main.py) both drive `GalacticaRestaker`.
- Core restake flow is a **two-transaction sequence**: `createStake(0)` (triggers `updateReward`) then `addRewardToStake()`; implemented in `GalacticaRestaker.execute_restake()` in [restake.py](restake.py).
- History is append-only CSV written by `save_to_history()` in [restake.py](restake.py) and summarized in [dashboard.py](dashboard.py).

## Config + secrets conventions
- YAML configs: mainnet in [config.yaml](config.yaml), testnet in [config.testnet.yaml](config.testnet.yaml). Env vars `RPC_URL` and `STAKING_CONTRACT` override YAML values.
- CLI loads dotenv files in order `.env.local` → `.env` (see `GalacticaRestaker.__init__` in [restake.py](restake.py)); testnet launcher prefers `.env.testnet` first (see [restake_testnet.py](restake_testnet.py)).
- GUI stores user config in `%APPDATA%/GalacticaRestaker/config.json` with DPAPI-encrypted private key (see [gui/config_manager.py](gui/config_manager.py)). Never log or persist plaintext keys.
- GUI creates default YAML configs under the AppData folder when missing (see `_create_default_config()` in [gui/main.py](gui/main.py)).

## Runtime behavior + data flow
- Gas cap and minimum reward threshold live in YAML under `gas.max_gas_price_gwei` and `restaking.min_reward_threshold` and are enforced in `execute_restake()`.
- Logs: CLI writes to `logs/restake.log` (or `logs/restake_testnet.log`); GUI logs to `%APPDATA%/GalacticaRestaker/logs/gui.log`.
- Scheduler: GUI uses APScheduler in [gui/scheduler.py](gui/scheduler.py); `start()` triggers an immediate run via `next_run_time=datetime.now()`.
- Tray UX: system tray controls and notifications in [gui/tray.py](gui/tray.py); settings/first-run wizard in [gui/setup_dialog.py](gui/setup_dialog.py).

## Developer workflows (Windows-centric)
- Install deps: `pip install -r requirements.txt` (see [requirements.txt](requirements.txt)).
- Run GUI: `python gui/main.py` (logs in AppData). Build EXE: `pyinstaller gui/build.spec` (see README).
- Run CLI: `python restake.py --dry-run`, then `python restake.py`.
- Diagnostics: `python test_balance.py` validates RPC + staking contract read calls.
- Scheduling: [scripts/setup_scheduler.ps1](scripts/setup_scheduler.ps1) registers Task Scheduler jobs for CLI runs.

## Project-specific patterns to follow
- Result dict shape from `execute_restake()` is used by GUI/tray; preserve keys like `status`, `amount_restaked`, `gas_cost`, and `timestamp`.
- CSV column names are fixed (see `save_to_history()`); keep schema stable for [dashboard.py](dashboard.py).
- When adding new network support, mirror `config.testnet.yaml` and update `restake_testnet.py` defaults.
