"""
Galactica Auto-Restaking Console Dashboard
Summarize staking performance directly in the terminal.
"""

import sys
from pathlib import Path
import pandas as pd
from colorama import Fore, init

# Initialize colorama for Windows terminals
init(autoreset=True)


class RestakingDashboard:
    """Console-only dashboard for Galactica restaking history"""

    def __init__(self, history_file: str = "data/history.csv") -> None:
        self.history_file = Path(history_file)
        self.df = self._load_history()

        if self.df is None or self.df.empty:
            print(f"{Fore.YELLOW}⚠ No history data found. Run restake.py first to generate data.")
            sys.exit(0)

        print(f"{Fore.GREEN}✓ Loaded {len(self.df)} restaking records")

    def _load_history(self) -> pd.DataFrame | None:
        """Load history from CSV file."""
        try:
            if not self.history_file.exists():
                return None

            df = pd.read_csv(self.history_file)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            return df.sort_values('Timestamp').reset_index(drop=True)
        except Exception as exc:
            print(f"{Fore.RED}✗ Error loading history: {exc}")
            return None

    def _successful_runs(self) -> pd.DataFrame:
        """Return DataFrame containing successful restakes only."""
        return self.df[self.df['Status'] == 'Success'].copy()

    def print_summary_stats(self) -> None:
        """Print headline performance metrics."""
        success_df = self._successful_runs()

        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.CYAN}GALACTICA AUTO-RESTAKING BOT")
        print(f"{Fore.CYAN}{'=' * 70}\n")

        if success_df.empty:
            print(f"{Fore.YELLOW}⚠ No successful restakes yet.\n")
            print(f"{Fore.CYAN}{'=' * 70}\n")
            return

        total_restaked = success_df['Amount Restaked (GNET)'].sum()
        total_gas_cost = success_df['Gas Cost (GNET)'].sum()
        initial_stake = success_df['Stake Before'].iloc[0]
        latest_stake = success_df['Stake After'].iloc[-1]
        total_growth = latest_stake - initial_stake
        net_gain = total_restaked - total_gas_cost

        print(f"{Fore.GREEN}✓ Bot Status: Active")
        print(f"{Fore.WHITE}  Successful restakes: {len(success_df)}")
        print(f"  Current stake:       {latest_stake:,.2f} GNET")
        print(f"  Total compounded:    {total_growth:,.2f} GNET (+{(total_growth/initial_stake*100):.2f}%)")
        print(f"  Net profit:          {net_gain:,.6f} GNET (after gas)")
        print(f"\n{Fore.CYAN}{'=' * 70}\n")

    def print_recent_runs(self, limit: int = 5) -> None:
        """Print the most recent restake attempts."""
        tail_df = self.df.tail(limit).copy()
        tail_df['Timestamp'] = tail_df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M')

        print(f"{Fore.WHITE}🕒 RECENT RUNS (latest {len(tail_df)})")
        print(tail_df[['Timestamp', 'Status', 'Amount Restaked (GNET)', 'Stake After', 'Gas Cost (GNET)']].to_string(index=False))
        print()

    def print_reward_distribution(self) -> None:
        """Show reward totals by day and status for quick trend checks."""
        df = self.df.copy()
        df['Date'] = df['Timestamp'].dt.date
        grouped = df.groupby(['Date', 'Status'], as_index=False)['Amount Restaked (GNET)'].sum()

        print(f"{Fore.WHITE}📅 DAILY REWARD TOTALS")
        if grouped.empty:
            print(f"{Fore.YELLOW}  No reward data to display yet.\n")
            return

        for _, row in grouped.iterrows():
            print(f"  {row['Date']} | {row['Status']:<10} | {row['Amount Restaked (GNET)']:>12,.6f} GNET")
        print()

    def print_interval_metrics(self) -> None:
        """Report average interval between successful runs."""
        success_df = self._successful_runs()
        print(f"{Fore.WHITE}⏱️  INTERVAL METRICS")

        if len(success_df) < 2:
            print(f"  {Fore.YELLOW}Need at least two successful runs to compute intervals.\n")
            return

        success_df = success_df[['Timestamp']].copy()
        success_df['Delta_hours'] = success_df['Timestamp'].diff().dt.total_seconds() / 3600
        intervals = success_df['Delta_hours'].dropna()

        print(f"  Average interval: {intervals.mean():.2f} hours")
        print(f"  Shortest interval: {intervals.min():.2f} hours")
        print(f"  Longest interval: {intervals.max():.2f} hours\n")

    def generate_console_report(self) -> None:
        """Display console summary only."""
        self.print_summary_stats()


def main() -> None:
    try:
        dashboard = RestakingDashboard()
        dashboard.generate_console_report()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠ Interrupted by user")
        sys.exit(0)
    except Exception as exc:
        print(f"\n{Fore.RED}✗ Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
