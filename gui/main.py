"""
Main entry point for the GUI application.

Orchestrates config, scheduler, tray, and restake logic.
"""

import logging
import sys
import os
import threading
from pathlib import Path

from gui.config_manager import ConfigManager, UserConfig, get_app_dir, get_base_dir
from gui.scheduler import RestakeScheduler
from gui.setup_dialog import SetupDialog
from gui.tray import TrayApp

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
        logging.FileHandler(log_dir / 'gui.log', encoding='utf-8')
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

    def _init_restaker(self) -> None:
        """Initialize the restaker with current config."""
        from restake import GalacticaRestaker

        # Set environment variables for restaker
        os.environ['PRIVATE_KEY'] = self.private_key
        os.environ['WALLET_ADDRESS'] = self.config.wallet_address

        # Choose config based on network - look in base directory
        config_name = 'config.yaml' if self.config.network == 'mainnet' else 'config.testnet.yaml'
        config_file = base_dir / config_name

        # If config doesn't exist in base_dir, create default one in app_dir
        if not config_file.exists():
            config_file = self._create_default_config()

        try:
            self.restaker = GalacticaRestaker(config_path=str(config_file), dry_run=False)
            logger.info(f"Restaker initialized for {self.config.network}")
        except Exception as e:
            logger.error(f"Failed to initialize restaker: {e}")
            raise

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
                    'staking_contract': '0xC0F305b12a73c6c8c6fd0EE0459c93f5C73e1AB3'
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
                    'staking_contract': '0xE2392D3C7fAebeC42940EdB0ea8997874e5B2b3D'
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
                if self.tray and self.config.notifications_enabled:
                    self.tray.show_notification(
                        "✅ Restake Successful",
                        f"+{amount:.4f} GNET restaked"
                    )
                self.tray.update_icon(success=True)
            
            if result:
                self.restaker.save_to_history(result)
            
            return result or {}
        
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

    def _on_settings(self) -> None:
        """Open settings dialog."""
        def on_complete(config: UserConfig, key: str):
            self.config = config
            self.private_key = key
            self.restaker = None  # Force reinit
            
            # Restart scheduler with new interval
            if self.scheduler and self.scheduler.is_running:
                self.scheduler.stop()
                self.scheduler.start(self.config.interval_hours)

        # Run dialog in main thread
        dialog = SetupDialog(self.config_manager, on_complete)
        threading.Thread(target=dialog.show, daemon=True).start()

    def _on_run_now(self) -> None:
        """Trigger immediate restake."""
        threading.Thread(target=self._do_restake, daemon=True).start()

    def _on_toggle(self, start: bool) -> None:
        """Toggle scheduler on/off."""
        if start:
            if not self.restaker:
                self._init_restaker()
            self.scheduler.start(self.config.interval_hours)
        else:
            self.scheduler.stop()

    def _on_exit(self) -> None:
        """Handle application exit."""
        logger.info("Application exiting")
        if self.scheduler:
            self.scheduler.stop()
        sys.exit(0)

    def _get_status(self) -> dict:
        """Get current status for tray menu."""
        if self.scheduler:
            return self.scheduler.get_status()
        return {'running': False}

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
