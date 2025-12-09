"""Testnet launcher for the Galactica auto-restaking bot."""

import argparse
import sys
from typing import List

from colorama import Fore

from restake import GalacticaRestaker

DEFAULT_ENV_FILES: List[str] = [
    '.env.testnet',
    '.env.local',
    '.env',
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Galactica Auto-Restaking Bot (Cassiopeia Testnet)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate restake without sending transactions',
    )
    parser.add_argument(
        '--config',
        default='config.testnet.yaml',
        help='Path to testnet configuration YAML (default: config.testnet.yaml)',
    )
    parser.add_argument(
        '--env-file',
        dest='env_files',
        action='append',
        help='Additional dotenv file(s) to load. Defaults to .env.testnet → .env.local → .env.',
    )
    args = parser.parse_args()

    env_files = args.env_files if args.env_files else DEFAULT_ENV_FILES

    try:
        restaker = GalacticaRestaker(
            config_path=args.config,
            dry_run=args.dry_run,
            env_files=env_files,
        )
        restaker.run()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠ Interrupted by user")
        sys.exit(0)
    except Exception as exc:
        print(f"\n{Fore.RED}✗ Fatal error: {exc}")
        sys.exit(1)


if __name__ == '__main__':
    main()
