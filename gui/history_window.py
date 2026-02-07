"""
History window for viewing restake operation log.

Displays CSV history in a sortable table with summary statistics.
"""

import csv
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import List, Optional


class HistoryWindow:
    """Window displaying restake history from CSV file."""

    COLUMNS = [
        ("Timestamp", 150),
        ("Amount (GNET)", 110),
        ("Stake Before", 110),
        ("Stake After", 110),
        ("Gas Cost", 90),
        ("Status", 80),
        ("TX Hash", 140),
    ]

    # Mapping from CSV column names to display column names
    CSV_TO_COL = {
        'Timestamp': 'Timestamp',
        'Amount Restaked (GNET)': 'Amount (GNET)',
        'Stake Before': 'Stake Before',
        'Stake After': 'Stake After',
        'Gas Cost (GNET)': 'Gas Cost',
        'Status': 'Status',
        'TX Hash': 'TX Hash',
    }

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self.root: Optional[tk.Tk] = None

    def show(self) -> None:
        """Show the history window (blocking)."""
        self.root = tk.Tk()
        self.root.title("Galactica Restaker \u2014 History")
        self.root.geometry("860x480")
        self.root.minsize(700, 300)

        # Set window icon
        try:
            from gui.tray import create_icon_image
            from PIL import ImageTk
            icon_image = create_icon_image(size=32)
            self._icon_photo = ImageTk.PhotoImage(icon_image)
            self.root.iconphoto(True, self._icon_photo)
        except Exception:
            pass

        self.root.eval('tk::PlaceWindow . center')
        self._create_widgets()
        self._load_data()
        self.root.mainloop()

    def _create_widgets(self) -> None:
        """Build the window layout."""
        style = ttk.Style()
        style.configure("Treeview", rowheight=26, font=('Segoe UI', 9))
        style.configure("Treeview.Heading", font=('Segoe UI', 9, 'bold'))

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header = ttk.Frame(main_frame)
        header.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(
            header, text="\U0001f4ca Restake History",
            font=('Segoe UI', 13, 'bold')
        ).pack(side=tk.LEFT)

        self.summary_label = ttk.Label(header, text="", font=('Segoe UI', 9))
        self.summary_label.pack(side=tk.RIGHT)

        # Treeview with scrollbar
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(
            tree_frame, columns=col_ids, show='headings', selectmode='browse'
        )

        for col_name, width in self.COLUMNS:
            self.tree.heading(col_name, text=col_name)
            self.tree.column(col_name, width=width, minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom bar
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.file_label = ttk.Label(
            btn_frame, text=str(self.csv_path),
            font=('Segoe UI', 8), foreground='gray'
        )
        self.file_label.pack(side=tk.LEFT)

        ttk.Button(
            btn_frame, text="  Close  ", command=self.root.destroy
        ).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(
            btn_frame, text="  Refresh  ", command=self._load_data
        ).pack(side=tk.RIGHT)

    def _load_data(self) -> None:
        """Load (or reload) CSV data into the table."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.csv_path.exists():
            self.summary_label.config(text="No history file found")
            return

        rows: List[dict] = []
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
        except Exception:
            self.summary_label.config(text="\u26a0 Error reading history file")
            return

        # Insert newest first
        for row in reversed(rows):
            values = self._format_row(row)
            status = row.get('Status', '')
            tag = (
                'success' if status == 'Success'
                else 'failed' if status == 'Failed'
                else 'other'
            )
            self.tree.insert('', tk.END, values=values, tags=(tag,))

        self.tree.tag_configure('success', foreground='#008800')
        self.tree.tag_configure('failed', foreground='#CC0000')
        self.tree.tag_configure('other', foreground='#666666')

        # Summary
        total = len(rows)
        successes = sum(1 for r in rows if r.get('Status') == 'Success')
        total_restaked = 0.0
        total_gas = 0.0
        for r in rows:
            if r.get('Status') == 'Success':
                try:
                    total_restaked += float(r.get('Amount Restaked (GNET)', 0))
                except (ValueError, TypeError):
                    pass
            try:
                total_gas += float(r.get('Gas Cost (GNET)', 0))
            except (ValueError, TypeError):
                pass

        self.summary_label.config(
            text=(
                f"{total} runs  \u00b7  {successes} successful  \u00b7  "
                f"{total_restaked:.4f} GNET restaked  \u00b7  "
                f"{total_gas:.4f} GNET gas"
            )
        )

    def _format_row(self, row: dict) -> list:
        """Format a CSV row dict into display values."""
        values = []
        for csv_col, tree_col in self.CSV_TO_COL.items():
            val = row.get(csv_col, '')
            # Format numbers to 4 decimal places
            if tree_col in ('Amount (GNET)', 'Stake Before', 'Stake After', 'Gas Cost'):
                try:
                    val = f"{float(val):.4f}"
                except (ValueError, TypeError):
                    pass
            # Truncate long tx hashes for readability
            if tree_col == 'TX Hash' and len(str(val)) > 18:
                val = str(val)[:10] + '\u2026' + str(val)[-6:]
            values.append(val)
        return values
