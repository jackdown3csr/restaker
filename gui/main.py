"""
Main entry point for the GUI application.

Orchestrates config, scheduler, tray, and restake logic.
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
import os
import threading
from pathlib import Path

from gui.config_manager import ConfigManager, UserConfig, get_app_dir, get_base_dir
from gui.scheduler import RestakeScheduler
from gui.setup_dialog import SetupDialog
from gui.tray import TrayApp
from gui.vesting_checker import VestingChecker

# Add base directory to path for imports (needed for restake.py)
base_dir = get_base_dir()
sys.path.insert(0, str(base_dir))

# Setup logging - use AppData for log files
app_dir = get_app_dir()
log_dir = app_dir / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            log_dir / 'gui.log', encoding='utf-8',
            maxBytes=5 * 1024 * 1024, backupCount=3
        )
    ]
)
logger = logging.getLogger(__name__)


class RestakeApp:
    """Main application controller."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.config: UserConfig = self.config_manager.load()
        self.private_key: str = ""
        self.scheduler: RestakeScheduler = None
        self.tray: TrayApp = None
        self.restaker = None  # Will hold GalacticaRestaker instance
        self.vesting_checker: VestingChecker = None  # Will check for vesting rewards
        self._settings_open = False  # Guard against multiple settings dialogs
        self._history_open = False  # Guard against multiple history windows

    def _init_restaker(self) -> None:
        """Initialize the restaker with current config."""
        from restake import GalacticaRestaker

        # Set environment variables temporarily for restaker init
        os.environ['PRIVATE_KEY'] = self.private_key
        os.environ['WALLET_ADDRESS'] = self.config.wallet_address

        # Choose config based on network - look in base directory
        config_name = 'config.yaml' if self.config.network == 'mainnet' else 'config.testnet.yaml'
        config_file = base_dir / config_name

        # If config doesn't exist in base_dir, create default one in app_dir
        if not config_file.exists():
            config_file = self._create_default_config()

        try:
            self.restaker = GalacticaRestaker(
                config_path=str(config_file), dry_run=self.config.dry_run
            )
            # Apply GUI settings over YAML defaults
            self.restaker.config['restaking']['min_reward_threshold'] = self.config.min_threshold
            self.restaker.config['gas']['max_gas_price_gwei'] = self.config.max_gas_gwei

            logger.info(f"Restaker initialized for {self.config.network}"
                        f"{' (dry-run)' if self.config.dry_run else ''}")

            # Initialize vesting checker for mainnet
            if self.config.network == 'mainnet':
                self.vesting_checker = VestingChecker(
                    rpc_url='https://galactica-mainnet.g.alchemy.com/public',
                    user_address=self.config.wallet_address
                )
                logger.info("Vesting checker initialized")
        except Exception as e:
            logger.error(f"Failed to initialize restaker: {e}")
            raise
        finally:
            # Clean sensitive data from environment immediately
            os.environ.pop('PRIVATE_KEY', None)

    def _create_default_config(self) -> Path:
        """Create a default config file in app directory."""
        import yaml
        
        config_file = app_dir / 'config.yaml'
        
        if self.config.network == 'testnet':
            config_file = app_dir / 'config.testnet.yaml'
            default_config = {
                'network': {
                    'name': 'Cassiopeia Testnet',
                    'rpc_url': 'https://galactica-cassiopeia.g.alchemy.com/public',
                    'chain_id': 843843,
                    'staking_contract': '0xC0F305b12a73c6c8c6fd0EE0459c93f5C73e1AB3',
                    'explorer': 'https://explorer.galactica.com/'
                },
                'restaking': {
                    'min_reward_threshold': self.config.min_threshold
                },
                'gas': {
                    'max_gas_price_gwei': self.config.max_gas_gwei,
                    'gas_limit_multiplier': 1.2
                },
                'logging': {
                    'level': 'INFO',
                    'log_to_file': True,
                    'log_file': str(log_dir / 'restake_testnet.log')
                },
                'export': {
                    'csv_file': str(app_dir / 'data' / 'history_testnet.csv')
                }
            }
        else:
            default_config = {
                'network': {
                    'name': 'Galactica Mainnet',
                    'rpc_url': 'https://galactica-mainnet.g.alchemy.com/public',
                    'chain_id': 613419,
                    'staking_contract': 826030585723602961507836977318968404690514027560,
                    'explorer': 'https://explorer.galactica.com/'
                },
                'restaking': {
                    'min_reward_threshold': self.config.min_threshold
                },
                'gas': {
                    'max_gas_price_gwei': self.config.max_gas_gwei,
                    'gas_limit_multiplier': 1.2
                },
                'logging': {
                    'level': 'INFO',
                    'log_to_file': True,
                    'log_file': str(log_dir / 'restake.log')
                },
                'export': {
                    'csv_file': str(app_dir / 'data' / 'history.csv')
                }
            }
        
        # Ensure data directory exists
        (app_dir / 'data').mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        logger.info(f"Created default config: {config_file}")
        return config_file

    def _do_restake(self) -> dict:
        """Execute restake operation."""
        if not self.restaker:
            self._init_restaker()

        try:
            result = self.restaker.execute_restake()

            if result and result.get('status') == 'Success':
                amount = result.get('amount_restaked', 0)
                if self.tray:
                    self.tray.update_icon(success=True)
                    if self.config.notifications_enabled:
                        self.tray.show_notification(
                            "✅ Restake Successful",
                            f"+{amount:.4f} GNET restaked"
                        )
            elif result and result.get('status') == 'Dry Run':
                amount = result.get('amount_restaked', 0)
                if self.tray and self.config.notifications_enabled:
                    self.tray.show_notification(
                        "🧪 Dry Run Complete",
                        f"Would restake {amount:.4f} GNET"
                    )
            elif result and result.get('status') == 'Failed':
                if self.tray:
                    self.tray.update_icon(success=False)
                    if self.config.notifications_enabled:
                        self.tray.show_notification(
                            "❌ Restake Failed", "Check log for details"
                        )

            # Save all non-None results to history (consistent with CLI)
            if result:
                self.restaker.save_to_history(result)

            # Check for vesting rewards after restake (mainnet only)
            self._check_vesting_rewards()

            # execute_restake returns None for: below threshold, high gas, RPC/contract error
            if result is None:
                return {
                    'status': 'Skipped',
                    'reason': 'Below threshold, gas too high, or RPC error \u2014 see log',
                }

            return result

        except Exception as e:
            logger.error(f"Restake failed: {e}")
            if self.tray:
                self.tray.update_icon(success=False)
                if self.config.notifications_enabled:
                    self.tray.show_notification("❌ Restake Failed", str(e))
            return {'status': 'Failed', 'error': str(e)}

    def _on_restake_error(self, error: Exception) -> None:
        """Handle restake errors."""
        logger.error(f"Scheduler error: {error}")
        if self.tray and self.config.notifications_enabled:
            self.tray.show_notification("❌ Error", str(error))

    def _check_vesting_rewards(self) -> None:
        """Check if new vesting rewards are available and notify user."""
        if not self.vesting_checker:
            return  # Only for mainnet
        
        try:
            has_new, epochs_behind = self.vesting_checker.check_new_rewards()
            
            if has_new and self.tray and self.config.notifications_enabled:
                logger.info(f"New vesting rewards available: {epochs_behind} epoch(s) behind")
                self.tray.show_notification(
                    "🎁 Vesting Rewards",
                    f"{epochs_behind} epoch(s) available to claim"
                )
        except Exception as e:
            logger.warning(f"Vesting check failed: {e}")

    def _on_settings(self) -> None:
        """Open settings dialog."""
        if self._settings_open:
            return  # Prevent multiple dialogs
        self._settings_open = True

        def on_complete(config: UserConfig, key: str):
            self.config = config
            self.private_key = key
            self.restaker = None  # Force reinit

            # Restart scheduler with new interval
            if self.scheduler and self.scheduler.is_running:
                self.scheduler.stop()
                self.scheduler.start(self.config.interval_hours)

        try:
            dialog = SetupDialog(self.config_manager, on_complete)
            dialog.show()
        finally:
            self._settings_open = False

    def _on_run_now(self) -> None:
        """Trigger immediate restake."""
        threading.Thread(target=self._do_restake, daemon=True).start()

    def _on_toggle(self, start: bool) -> None:
        """Toggle scheduler on/off."""
        try:
            if start:
                if not self.restaker:
                    self._init_restaker()
                self.scheduler.start(self.config.interval_hours)
            else:
                self.scheduler.stop()
        except Exception as e:
            logger.error(f"Toggle failed: {e}")
            if self.tray and self.config.notifications_enabled:
                self.tray.show_notification("❌ Error", str(e))

    def _on_exit(self) -> None:
        """Handle application exit."""
        logger.info("Application exiting")
        if self.scheduler:
            self.scheduler.stop()
        # Don't call sys.exit() here - let icon.stop() handle cleanup
        # The app will exit naturally when the tray icon stops

    def _get_status(self) -> dict:
        """Get current status for tray menu."""
        if self.scheduler:
            return self.scheduler.get_status()
        return {'running': False}

    def _get_csv_path(self) -> str:
        """Get path to the history CSV file."""
        if self.restaker:
            return self.restaker.csv_file
        # Fallback: derive from config
        if self.config.network == 'testnet':
            return str(app_dir / 'data' / 'history_testnet.csv')
        return str(app_dir / 'data' / 'history.csv')

    def _show_history(self) -> None:
        """Show restake history window (non-blocking)."""
        if self._history_open:
            return
        self._history_open = True

        def _open():
            from gui.history_window import HistoryWindow
            csv_path = self._get_csv_path()
            try:
                window = HistoryWindow(csv_path)
                window.show()
            except Exception as e:
                logger.error(f"Failed to open history: {e}")
            finally:
                self._history_open = False

        threading.Thread(target=_open, daemon=True).start()

    def run(self) -> None:
        """Run the application."""
        logger.info("Starting Galactica Restaker GUI")

        # Check if first run (no config)
        if not self.config_manager.is_configured():
            logger.info("First run - showing setup dialog")
            
            def on_complete(config: UserConfig, key: str):
                self.config = config
                self.private_key = key

            dialog = SetupDialog(self.config_manager, on_complete)
            if not dialog.show():
                logger.info("Setup cancelled")
                return
        else:
            self.private_key = self.config_manager.get_private_key(self.config)

        # Initialize restaker
        try:
            self._init_restaker()
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return

        # Initialize scheduler
        self.scheduler = RestakeScheduler(
            on_restake=self._do_restake,
            on_error=self._on_restake_error
        )

        # Initialize tray
        self.tray = TrayApp(
            on_settings=self._on_settings,
            on_run_now=self._on_run_now,
            on_toggle=self._on_toggle,
            on_exit=self._on_exit,
            get_status=self._get_status,
            on_history=self._show_history,
        )

        # Start scheduler
        self.scheduler.start(self.config.interval_hours)
        logger.info(f"Scheduler started with {self.config.interval_hours}h interval")

        # Run tray (blocking)
        logger.info("Starting system tray")
        self.tray.run()


def main():
    """Entry point."""
    # Ensure logs directory exists
    logs_dir = Path(__file__).parent.parent / 'logs'
    logs_dir.mkdir(exist_ok=True)

    try:
        app = RestakeApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
