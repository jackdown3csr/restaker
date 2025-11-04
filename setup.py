"""Interactive setup wizard for configuring the restaking bot."""

import os
import sys
from pathlib import Path
import yaml
from colorama import Fore, init

init(autoreset=True)


class RestakeSetup:
    """Interactive setup wizard for the Galactica restaking bot."""

    def __init__(self) -> None:
        self.env_file = ".env.local"
        self.config_file = "config.yaml"
        self.env_vars: dict[str, str] = {}
        self.config: dict = {}

    def header(self) -> None:
        """Print a friendly wizard header."""
        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.CYAN}GALACTICA AUTO-RESTAKING BOT • SETUP WIZARD")
        print(f"{Fore.CYAN}{'=' * 70}\n")

    def load_existing(self) -> None:
        """Load values from existing config/env files if present."""
        if Path(self.env_file).exists():
            try:
                with open(self.env_file) as handle:
                    for line in handle:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key, val = line.split('=', 1)
                            self.env_vars[key] = val
                print(f"{Fore.GREEN}✓ Loaded existing .env.local\n")
            except Exception as exc:  # pragma: no cover - interactive output
                print(f"{Fore.YELLOW}⚠ Could not load .env.local: {exc}\n")

        if Path(self.config_file).exists():
            try:
                with open(self.config_file) as handle:
                    self.config = yaml.safe_load(handle)
                print(f"{Fore.GREEN}✓ Loaded existing config.yaml\n")
            except Exception as exc:  # pragma: no cover - interactive output
                print(f"{Fore.YELLOW}⚠ Could not load config.yaml: {exc}\n")

    def ensure_defaults(self) -> None:
        """Populate default configuration values if missing."""
        network_section = self.config.setdefault('network', {})
        network_section.setdefault('name', 'Galactica Mainnet')
        network_section.setdefault('chain_id', 613419)
        network_section.setdefault('rpc_url', 'https://galactica-mainnet.g.alchemy.com/public')
        network_section.setdefault('explorer', 'https://explorer.galactica.com/')
        network_section.setdefault('staking_contract', '0x90B07E15Cfb173726de904ca548dd96f73c12428')

        self.config.setdefault('restaking', {})
        self.config['restaking'].setdefault('min_reward_threshold', 0.1)

        self.config.setdefault('gas', {})
        self.config['gas'].setdefault('max_gas_price_gwei', 50)

        export_section = self.config.setdefault('export', {})
        export_section.setdefault('csv_file', 'data/history.csv')

    def setup_wallet(self) -> bool:
        """Collect wallet address and private key (stored locally)."""
        print(f"{Fore.WHITE}🔐 WALLET CONFIGURATION\n")

        print(f"{Fore.CYAN}Enter your wallet address (press Enter to keep current value):")
        if 'WALLET_ADDRESS' in self.env_vars:
            current = self.env_vars['WALLET_ADDRESS']
            print(f"  Current: {current[:10]}...{current[-8:]}")
        address = input(f"{Fore.WHITE}  → ").strip()
        if address:
            if not address.startswith('0x'):
                address = '0x' + address
            self.env_vars['WALLET_ADDRESS'] = address
            print(f"{Fore.GREEN}✓ Wallet address saved\n")
        elif 'WALLET_ADDRESS' not in self.env_vars:
            print(f"{Fore.RED}✗ Wallet address is required\n")
            return False

        print(f"{Fore.CYAN}Enter your private key (press Enter to keep current value):")
        print(f"{Fore.YELLOW}⚠ Stored only in .env.local (git-ignored)\n")
        private_key = input(f"{Fore.WHITE}  → ").strip()
        if private_key:
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key
            self.env_vars['PRIVATE_KEY'] = private_key
            print(f"{Fore.GREEN}✓ Private key stored locally\n")
        elif 'PRIVATE_KEY' not in self.env_vars:
            print(f"{Fore.RED}✗ Private key is required\n")
            return False

        return True

    def confirm_network(self) -> bool:
        """Print network details so the user knows what will be used."""
        print(f"{Fore.WHITE}🌐 NETWORK CONFIGURATION\n")
        network = self.config.get('network', {})
        print(f"{Fore.CYAN}Network: {network.get('name', 'Galactica Mainnet')}")
        print(f"  Chain ID: {network.get('chain_id', 613419)}")
        print(f"  RPC URL: {network.get('rpc_url', 'https://galactica-mainnet.g.alchemy.com/public')}\n")
        staking_contract = network.get('staking_contract', '0x90B07E15Cfb173726de904ca548dd96f73c12428')
        print(f"  Staking contract: {staking_contract}\n")
        print(f"{Fore.GREEN}✓ Network settings verified\n")
        return True

    def configure_minimum_threshold(self) -> bool:
        """Allow the user to adjust the minimum reward threshold."""
        print(f"{Fore.WHITE}💰 MINIMUM REWARD THRESHOLD\n")
        current = self.config['restaking']['min_reward_threshold']
        print(f"{Fore.CYAN}Restake only when pending rewards exceed this amount.")
        print(f"Current: {current} GNET (recommended: 0.1 – 1.0)\n")

        user_input = input(f"{Fore.WHITE}Enter new threshold (blank to keep {current}): ").strip()
        if user_input:
            try:
                value = float(user_input)
                if value < 0:
                    raise ValueError("Threshold must be non-negative")
                self.config['restaking']['min_reward_threshold'] = value
                print(f"{Fore.GREEN}✓ Threshold set to {value} GNET\n")
            except ValueError:
                print(f"{Fore.RED}✗ Invalid number supplied\n")
                return False
        else:
            print(f"{Fore.GREEN}✓ Keeping {current} GNET\n")

        return True

    def configure_gas_cap(self) -> bool:
        """Let the user override the maximum allowable gas price."""
        print(f"{Fore.WHITE}⛽ GAS PRICE CAP\n")
        current = self.config['gas']['max_gas_price_gwei']
        print(f"{Fore.CYAN}Skip restakes when network gas price exceeds this value.")
        print(f"Current: {current} Gwei\n")

        user_input = input(f"{Fore.WHITE}Enter new gas cap (blank to keep {current}): ").strip()
        if user_input:
            try:
                value = float(user_input)
                if value <= 0:
                    raise ValueError("Gas cap must be positive")
                self.config['gas']['max_gas_price_gwei'] = value
                print(f"{Fore.GREEN}✓ Gas cap set to {value} Gwei\n")
            except ValueError:
                print(f"{Fore.RED}✗ Invalid number supplied\n")
                return False
        else:
            print(f"{Fore.GREEN}✓ Keeping {current} Gwei\n")

        return True

    def confirm_history_location(self) -> bool:
        """Allow user to confirm or change the CSV history path."""
        print(f"{Fore.WHITE}📊 HISTORY STORAGE\n")
        current = self.config['export']['csv_file']
        print(f"{Fore.CYAN}Restake history is appended to a CSV file after each run.")
        print(f"Current location: {current}\n")

        new_path = input(f"{Fore.WHITE}Enter new path (blank to keep current): ").strip()
        if new_path:
            self.config['export']['csv_file'] = new_path
            print(f"{Fore.GREEN}✓ CSV file path set to {new_path}\n")
        else:
            print(f"{Fore.GREEN}✓ Keeping {current}\n")

        return True

    def save_configuration(self) -> bool:
        """Persist environment variables and configuration to disk."""
        try:
            with open(self.env_file, 'w') as handle:
                handle.write("# Galactica Auto-Restaking Bot - Environment Variables\n")
                handle.write("# DO NOT COMMIT THIS FILE - It contains your private key!\n\n")
                for key, value in self.env_vars.items():
                    handle.write(f"{key}={value}\n")
            try:
                os.chmod(self.env_file, 0o600)
            except OSError:
                # Windows does not fully support chmod; warn but continue
                print(f"{Fore.YELLOW}⚠ Unable to restrict permissions on {self.env_file} (Windows limitation)\n")
            print(f"{Fore.GREEN}✓ Saved {self.env_file}\n")
        except Exception as exc:
            print(f"{Fore.RED}✗ Error saving {self.env_file}: {exc}\n")
            return False

        try:
            with open(self.config_file, 'w') as handle:
                yaml.dump(self.config, handle, default_flow_style=False, sort_keys=False)
            print(f"{Fore.GREEN}✓ Saved {self.config_file}\n")
        except Exception as exc:
            print(f"{Fore.RED}✗ Error saving {self.config_file}: {exc}\n")
            return False

        # Ensure the history directory exists for convenience
        csv_path = Path(self.config['export']['csv_file'])
        if csv_path.parent and not csv_path.parent.exists():
            csv_path.parent.mkdir(parents=True, exist_ok=True)

        return True

    def show_task_scheduler_instructions(self) -> None:
        """Print a short guide for scheduling the script on Windows."""
        print(f"{Fore.WHITE}📅 WINDOWS TASK SCHEDULER\n")
        project_root = Path(__file__).resolve().parent
        restake_path = project_root / 'restake.py'
        print(f"{Fore.CYAN}Configure Windows Task Scheduler to call: python {restake_path}\n")
        print(f"{Fore.WHITE}Suggested steps:")
        print(f"  1. Open Task Scheduler (Win + R → taskschd.msc)")
        print(f"  2. Create Basic Task → name it 'Galactica Auto-Restake'")
        print(f"  3. Choose trigger frequency (hourly/daily, etc.)")
        print(f"  4. Action → Start a program")
        print(f"  5. Program/script: <path to python.exe>")
        print(f"  6. Arguments: {restake_path}")
        print(f"  7. Start in: {project_root}")
        print(f"  8. Enable 'Run with highest privileges'\n")
        threshold = self.config['restaking']['min_reward_threshold']
        gas_cap = self.config['gas']['max_gas_price_gwei']
        print(f"{Fore.GREEN}✓ The bot will restake when rewards exceed {threshold} GNET")
        print(f"{Fore.GREEN}✓ Transactions are skipped if gas price > {gas_cap} Gwei")
        print(f"{Fore.GREEN}✓ Activity logs are stored in logs/restake.log\n")

    def run(self) -> bool:
        """Launch the interactive wizard."""
        self.header()
        self.load_existing()
        self.ensure_defaults()

        steps = [
            ("Wallet", self.setup_wallet),
            ("Network", self.confirm_network),
            ("Reward Threshold", self.configure_minimum_threshold),
            ("Gas Cap", self.configure_gas_cap),
            ("CSV Location", self.confirm_history_location),
        ]

        for name, func in steps:
            if not func():
                print(f"{Fore.RED}✗ Setup cancelled at step: {name}\n")
                return False

        if not self.save_configuration():
            return False

        self.show_task_scheduler_instructions()

        print(f"{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.GREEN}✓ Setup complete!")
        print(f"{Fore.CYAN}{'=' * 70}\n")
        print(f"{Fore.WHITE}Next steps:")
        print(f"  1. Test the bot: python restake.py --dry-run")
        print(f"  2. View history: python dashboard.py")
        print(f"  3. Schedule recurring runs using Task Scheduler\n")

        return True


def main():
    try:
        setup = RestakeSetup()
        success = setup.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠ Setup cancelled by user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}✗ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
