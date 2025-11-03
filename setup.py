"""
Interactive setup script for Galactica Auto-Restaking Bot
Configure environment, wallet, and scheduling preferences.
"""

import os
import sys
from pathlib import Path
import yaml
from colorama import Fore, Style, init

init(autoreset=True)


class RestakeSetup:
    """Interactive setup wizard for restaking bot"""

    def __init__(self):
        self.env_file = ".env.local"
        self.config_file = "config.yaml"
        self.env_vars = {}
        self.config = {}

    def header(self):
        """Print setup header"""
        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.CYAN}GALACTICA AUTO-RESTAKING BOT - SETUP WIZARD")
        print(f"{Fore.CYAN}{'=' * 70}\n")

    def load_existing(self):
        """Load existing configuration if available"""
        if Path(self.env_file).exists():
            try:
                with open(self.env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key, val = line.split('=', 1)
                            self.env_vars[key] = val
                print(f"{Fore.GREEN}✓ Loaded existing .env.local\n")
            except Exception as e:
                print(f"{Fore.YELLOW}⚠ Could not load .env.local: {e}\n")

        if Path(self.config_file).exists():
            try:
                with open(self.config_file) as f:
                    self.config = yaml.safe_load(f)
                print(f"{Fore.GREEN}✓ Loaded existing config.yaml\n")
            except Exception as e:
                print(f"{Fore.YELLOW}⚠ Could not load config.yaml: {e}\n")

    def ensure_defaults(self):
        """Ensure required config sections exist with defaults"""
        self.config.setdefault('restaking', {})
        self.config['restaking'].setdefault('min_reward_threshold', 0.1)

        self.config.setdefault('gas', {})
        self.config['gas'].setdefault('max_gas_price_gwei', 50)

        self.config.setdefault('export', {})
        self.config['export'].setdefault('csv_file', 'data/history.csv')

    def setup_wallet(self):
        """Configure wallet credentials"""
        print(f"{Fore.WHITE}🔐 WALLET CONFIGURATION\n")

        print(f"{Fore.CYAN}Enter your wallet address (or press Enter to keep existing):")
        if 'WALLET_ADDRESS' in self.env_vars:
            print(f"  Current: {self.env_vars['WALLET_ADDRESS'][:10]}...{self.env_vars['WALLET_ADDRESS'][-8:]}")
        addr = input(f"{Fore.WHITE}  → ").strip()
        if addr:
            if not addr.startswith('0x'):
                addr = '0x' + addr
            self.env_vars['WALLET_ADDRESS'] = addr
            print(f"{Fore.GREEN}✓ Wallet set\n")
        elif 'WALLET_ADDRESS' not in self.env_vars:
            print(f"{Fore.RED}✗ Wallet address required!\n")
            return False

        print(f"{Fore.CYAN}Enter your private key (or press Enter to keep existing):")
        print(f"{Fore.YELLOW}⚠ NEVER share this! It stays in .env.local (git-ignored)\n")
        pk_input = input(f"{Fore.WHITE}  → ").strip()
        if pk_input:
            if not pk_input.startswith('0x'):
                pk_input = '0x' + pk_input
            self.env_vars['PRIVATE_KEY'] = pk_input
            print(f"{Fore.GREEN}✓ Private key set (hidden for security)\n")
        elif 'PRIVATE_KEY' not in self.env_vars:
            print(f"{Fore.RED}✗ Private key required!\n")
            return False

        return True

    def setup_network(self):
        """Confirm network settings"""
        print(f"{Fore.WHITE}🌐 NETWORK CONFIGURATION\n")
        print(f"{Fore.CYAN}Network: Galactica Mainnet (Chain ID: 613419)")
        print(f"RPC: https://galactica-mainnet.g.alchemy.com/public\n")
        print(f"{Fore.GREEN}✓ Network auto-configured\n")
        return True

    def setup_export_format(self):
        """Configure export format"""
        print(f"{Fore.WHITE}📊 DATA EXPORT\n")
        print(f"{Fore.CYAN}Save history to CSV only (lightweight & portable)\n")

        if 'export' not in self.config:
            self.config['export'] = {}
        self.config['export']['format'] = 'csv'
        print(f"{Fore.GREEN}✓ Export format set to CSV\n")

        return True

    def setup_task_scheduler(self):
        """Configure minimum reward threshold"""
        print(f"{Fore.WHITE}💰 MINIMUM REWARD THRESHOLD\n")
        print(f"{Fore.CYAN}Restake only if pending rewards exceed this amount")
        print(f"(Prevents tiny restakes that waste gas)\n")

        current = self.config.get('restaking', {}).get('min_reward_threshold', 0.1)
        print(f"Current threshold: {current} GNET")
        print(f"{Fore.YELLOW}Recommended: 0.1-1.0 GNET\n")

        threshold = input(f"{Fore.WHITE}Enter minimum GNET (or press Enter for {current}): ").strip()
        if threshold:
            try:
                threshold = float(threshold)
                if threshold < 0:
                    print(f"{Fore.RED}✗ Must be >= 0\n")
                    return False
                if 'restaking' not in self.config:
                    self.config['restaking'] = {}
                self.config['restaking']['min_reward_threshold'] = threshold
                print(f"{Fore.GREEN}✓ Threshold set to {threshold} GNET\n")
            except ValueError:
                print(f"{Fore.RED}✗ Invalid number\n")
                return False
        else:
            print(f"{Fore.GREEN}✓ Using {current} GNET\n")

        return True

    def setup_minimum_threshold(self):
        """Configure minimum reward threshold"""
        print(f"{Fore.WHITE}💰 MINIMUM REWARD THRESHOLD\n")
        print(f"{Fore.CYAN}Restake only if pending rewards exceed this amount")
        print(f"(Prevents tiny restakes that waste gas)\n")

        current = self.config.get('restaking', {}).get('min_reward_threshold', 0.1)
        print(f"Current threshold: {current} GNET")
        print(f"{Fore.YELLOW}Recommended: 0.1-1.0 GNET\n")

        threshold = input(f"{Fore.WHITE}Enter minimum GNET (or press Enter for {current}): ").strip()
        if threshold:
            try:
                threshold = float(threshold)
                if threshold < 0:
                    print(f"{Fore.RED}✗ Must be >= 0\n")
                    return False
                if 'restaking' not in self.config:
                    self.config['restaking'] = {}
                self.config['restaking']['min_reward_threshold'] = threshold
                print(f"{Fore.GREEN}✓ Threshold set to {threshold} GNET\n")
            except ValueError:
                print(f"{Fore.RED}✗ Invalid number\n")
                return False
        else:
            print(f"{Fore.GREEN}✓ Using {current} GNET\n")

        return True

    def setup_export_format(self):
        """Configure export format"""
        print(f"{Fore.WHITE}📊 DATA EXPORT\n")
        print(f"{Fore.CYAN}Save history to CSV only (lightweight & portable)\n")

        if 'export' not in self.config:
            self.config['export'] = {}
        self.config['export']['format'] = 'csv'
        print(f"{Fore.GREEN}✓ Export format set to CSV\n")

        return True

    def save_configuration(self):
        """Save .env.local and config.yaml"""
        # Save .env.local
        try:
            with open(self.env_file, 'w') as f:
                f.write("# Galactica Auto-Restaking Bot - Environment Variables\n")
                f.write("# DO NOT COMMIT THIS FILE - It contains your private key!\n\n")
                for key, val in self.env_vars.items():
                    f.write(f"{key}={val}\n")
            os.chmod(self.env_file, 0o600)  # Restrict file permissions
            print(f"{Fore.GREEN}✓ Saved {self.env_file}\n")
        except Exception as e:
            print(f"{Fore.RED}✗ Error saving {self.env_file}: {e}\n")
            return False

        # Save config.yaml
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            print(f"{Fore.GREEN}✓ Saved {self.config_file}\n")
        except Exception as e:
            print(f"{Fore.RED}✗ Error saving {self.config_file}: {e}\n")
            return False

        return True

    def setup_task_scheduler(self):
        """Explain Windows Task Scheduler setup"""
        print(f"{Fore.WHITE}📅 WINDOWS TASK SCHEDULER\n")
        print(f"{Fore.CYAN}Your bot will run automatically on this schedule:\n")
        print(f"{Fore.WHITE}Setup instructions:")
        print(f"  1. Open Task Scheduler (Win+R → taskschd.msc)")
        print(f"  2. Click 'Create Basic Task'")
        print(f"  3. Name: 'Galactica Auto-Restake'")
        print(f"  4. Trigger: Choose your frequency (daily, hourly, etc.)")
        print(f"  5. Action: Start a program")
        print(f"  6. Program: <path to your python.exe>")
        print(f"  7. Arguments: C:\\path\\to\\restaker\\restake.py")
        print(f"  8. Check 'Run with highest privileges'\n")
        threshold = self.config.get('restaking', {}).get('min_reward_threshold', 0.1)
        gas_cap = self.config.get('gas', {}).get('max_gas_price_gwei', 50)
        print(f"{Fore.GREEN}✓ The bot will:")
        print(f"  • Run on your scheduled frequency")
        print(f"  • Automatically restake if rewards > {threshold} GNET")
        print(f"  • Skip if gas price exceeds {gas_cap} Gwei")
        print(f"  • Log all activity to logs/restake.log\n")

    def run(self):
        """Run the full setup wizard"""
        self.header()
        self.load_existing()
        self.ensure_defaults()

        steps = [
            ("Wallet", self.setup_wallet),
            ("Network", self.setup_network),
            ("Minimum Threshold", self.setup_minimum_threshold),
            ("Export Format", self.setup_export_format),
        ]

        for name, func in steps:
            if not func():
                print(f"{Fore.RED}✗ Setup cancelled at: {name}\n")
                return False

        if not self.save_configuration():
            return False

        self.setup_task_scheduler()

        print(f"{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.GREEN}✓ Setup complete!")
        print(f"{Fore.CYAN}{'=' * 70}\n")
        print(f"{Fore.WHITE}Next steps:")
        print(f"  1. Test the bot: python restake.py --dry-run")
        print(f"  2. View history: python dashboard.py")
        print(f"  3. Schedule in Windows Task Scheduler\n")

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
