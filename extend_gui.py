"""
Galactica Lock Extender — tkinter GUI with dashboard + settings tabs.

Features:
    - Dashboard tab: live lock stats, veGNET balance, extend button
    - Settings tab: wallet, private key, interval
    - Log tab: live log output
    - System tray icon with APScheduler auto-extend

Usage:
    python extend_gui.py              # launch GUI + tray
    python extend_gui.py --no-tray    # run once in console
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
def _resource_path(relative: str) -> Path:
    """Resolve path to bundled resource (PyInstaller or dev)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / relative

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "GalacticaExtender"
APP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = APP_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
CONFIG_FILE = APP_DIR / "config.json"
LOGO_PATH = _resource_path("LOGO_PNG.png")
VERSION = "1.0.7"
GUBI_API = "https://admin-panel.galactica.com/api"
GITHUB_REPO = "jackdown3csr/restaker"

# ── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-20s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            LOG_DIR / "extender.log", encoding="utf-8",
            maxBytes=5 * 1024 * 1024, backupCount=3,
        ),
    ],
)
logger = logging.getLogger("extend_gui")

# ── DPAPI helpers ──────────────────────────────────────────────────
try:
    import win32crypt
    HAS_DPAPI = True
except ImportError:
    HAS_DPAPI = False


def _encrypt_key(plaintext: str) -> str:
    if HAS_DPAPI:
        blob = win32crypt.CryptProtectData(
            plaintext.encode("utf-8"), "GalacticaExtender", None, None, None, 0
        )
        import base64
        return base64.b64encode(blob).decode()
    return plaintext


def _decrypt_key(blob_b64: str) -> str:
    if not blob_b64:
        return ""
    if HAS_DPAPI:
        import base64
        blob = base64.b64decode(blob_b64)
        _, data = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
        return data.decode("utf-8")
    return blob_b64


# ── Config ─────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _try_import_v1_config() -> dict:
    """Import wallet + key from the restaker v1 config."""
    v1 = Path(os.environ.get("APPDATA", "")) / "GalacticaRestaker" / "config.json"
    if v1.exists():
        try:
            data = json.loads(v1.read_text(encoding="utf-8"))
            return {
                "wallet_address": data.get("wallet_address", ""),
                "private_key_enc": data.get("private_key_encrypted", ""),
            }
        except Exception:
            pass
    return {}


# ═══════════════════════════════════════════════════════════════════
#  Main GUI Window (tkinter with tabs — default OS theme)
# ═══════════════════════════════════════════════════════════════════

class ExtenderGUI:
    """Tkinter window with Dashboard + Settings + Log tabs."""

    def __init__(self, cfg: dict):
        import tkinter as tk
        from tkinter import ttk

        self.cfg = cfg
        self.private_key = _decrypt_key(cfg.get("private_key_enc", ""))
        self.interval_days = cfg.get("interval_days", cfg.get("interval_hours", 24) // 24 or 1)
        self.vesting_enabled = cfg.get("vesting_check_enabled", False)
        self.vesting_interval_days = cfg.get("vesting_interval_days", cfg.get("vesting_interval_hours", 24) // 24 or 1)
        self._last_vesting_notified_epoch = cfg.get("vesting_last_notified_epoch", 0)
        self.scheduler = None
        self.tray = None
        self.last_result: dict | None = None
        self._status_cache: dict | None = None
        self.vesting_checker = None

        # ── Root window ────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("veGNET Lock Extender")
        self.root.geometry("560x640")
        self.root.minsize(520, 560)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Set window icon from logo
        try:
            from PIL import Image, ImageTk
            if LOGO_PATH.exists():
                img = Image.open(LOGO_PATH).resize((64, 64), Image.LANCZOS)
            else:
                from PIL import ImageDraw
                img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.ellipse([2, 2, 30, 30], fill="#00D4AA")
            self._icon_photo = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, self._icon_photo)
        except Exception:
            pass

        # Center window
        self.root.eval('tk::PlaceWindow . center')

        # ── Styles ─────────────────────────────────────────────
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Value.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("CardTitle.TLabel", font=("Segoe UI", 9), foreground="gray")
        style.configure("Unit.TLabel", font=("Segoe UI", 8), foreground="gray")
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"), foreground="#008866")
        style.configure("Error.TLabel", font=("Segoe UI", 10), foreground="red")
        style.configure("Muted.TLabel", font=("Segoe UI", 8), foreground="gray")
        style.configure("Update.TLabel", font=("Segoe UI", 9), foreground="#0066cc")

        # ── Header ─────────────────────────────────────────────
        header = ttk.Frame(self.root, padding="15 8 15 4")
        header.pack(fill="x")
        ttk.Label(header, text="veGNET Lock Extender", style="Title.TLabel").pack(side="left")

        self.status_label = ttk.Label(header, text="", style="Muted.TLabel")
        self.status_label.pack(side="right")

        # ── Update banner (hidden by default) ──────────────────
        self._update_frame = ttk.Frame(self.root, padding="15 2 15 2")
        # not packed yet — shown only when a new version is found
        self._update_label = ttk.Label(
            self._update_frame,
            text="",
            style="Update.TLabel",
            cursor="hand2",
        )
        self._update_label.pack(side="left")
        self._update_label.bind("<Button-1>", self._on_update_click)
        self._update_url: str = ""

        # ── Footer (pack first so it's never clipped) ─────────
        footer = ttk.Frame(self.root, padding="15 4 15 6")
        footer.pack(fill="x", side="bottom")
        self.footer_label = ttk.Label(footer, text="", style="Muted.TLabel")
        self.footer_label.pack(side="left")
        ttk.Label(footer, text=f"v{VERSION}", style="Muted.TLabel").pack(side="right")

        # ── Notebook (tabs) ────────────────────────────────────
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(5, 6))

        self._build_dashboard_tab()
        self._build_gubi_tab()
        self._build_settings_tab()
        self._build_log_tab()

        # ── Initial load ───────────────────────────────────────
        self._refresh_stats()
        self._refresh_gubi()
        threading.Thread(target=self._check_for_update, daemon=True).start()
        self._tick_countdown()

    # ── Dashboard Tab ──────────────────────────────────────────

    def _build_dashboard_tab(self):
        import tkinter as tk
        from tkinter import ttk

        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="  Dashboard  ")

        # Top row — metric cards
        cards_frame = ttk.Frame(tab)
        cards_frame.pack(fill="x", pady=(0, 10))
        cards_frame.columnconfigure((0, 1, 2), weight=1)

        self.card_locked = self._make_card(cards_frame, "Locked", "—", "GNET")
        self.card_locked.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.card_vegnet = self._make_card(cards_frame, "veGNET Balance", "—", "veGNET")
        self.card_vegnet.grid(row=0, column=1, sticky="nsew", padx=5)

        self.card_days = self._make_card(cards_frame, "Days Remaining", "—", "days")
        self.card_days.grid(row=0, column=2, sticky="nsew", padx=(5, 0))

        # Info section
        info_frame = ttk.LabelFrame(tab, text="Lock Details", padding=10)
        info_frame.pack(fill="x", pady=(0, 10))

        self._info_rows = {}
        for label in ["Lock Ends", "Max Possible End", "Extendable By", "veGNET Decay/Day", "Last Action"]:
            row = ttk.Frame(info_frame)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=label + ":", width=20, anchor="w").pack(side="left")
            val_lbl = ttk.Label(row, text="—")
            val_lbl.pack(side="left")
            self._info_rows[label] = val_lbl

        # Vesting section
        vest_frame = ttk.LabelFrame(tab, text="Vesting Rewards", padding=10)
        vest_frame.pack(fill="x", pady=(0, 10))
        self._vesting_rows = {}
        for label in ["Vesting Status", "Epochs Behind", "Total Claimed", "Last Check", "Last Notified"]:
            row = ttk.Frame(vest_frame)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=label + ":", width=20, anchor="w").pack(side="left")
            val_lbl = ttk.Label(row, text="—")
            val_lbl.pack(side="left")
            self._vesting_rows[label] = val_lbl

        vest_hint = ttk.Label(
            vest_frame,
            text="Tip: Epochs behind = current epoch − your last claimed epoch",
            style="Muted.TLabel",
        )
        vest_hint.pack(anchor="w", pady=(6, 0))

        vest_btn = ttk.Button(
            vest_frame,
            text="  Check Vesting Now  ",
            command=self._on_check_vesting_now,
        )
        vest_btn.pack(anchor="w", pady=(6, 0))

        # Buttons row
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", pady=(5, 5))

        self.btn_extend = ttk.Button(
            btn_frame, text="  Extend to Max  ",
            command=self._on_extend_click,
        )
        self.btn_extend.pack(side="left", padx=(0, 10), ipady=3)

        self.btn_refresh = ttk.Button(
            btn_frame, text="  Refresh  ", command=self._refresh_stats,
        )
        self.btn_refresh.pack(side="left", ipady=3)

        # Result banner
        self.result_label = ttk.Label(tab, text="", style="Status.TLabel")
        self.result_label.pack(fill="x", pady=(5, 0))

    def _make_card(self, parent, title, value, unit):
        """Create a metric card frame. Returns the frame; stores labels as attributes."""
        from tkinter import ttk
        frame = ttk.LabelFrame(parent, text="")
        inner = ttk.Frame(frame, padding=8)
        inner.pack(fill="both", expand=True)

        ttk.Label(inner, text=title.upper(), style="CardTitle.TLabel").pack(anchor="w")
        val_lbl = ttk.Label(inner, text=value, style="Value.TLabel")
        val_lbl.pack(anchor="w")
        unit_lbl = ttk.Label(inner, text=unit, style="Unit.TLabel")
        unit_lbl.pack(anchor="w")

        frame._val_lbl = val_lbl
        frame._unit_lbl = unit_lbl
        return frame

    # ── Settings Tab ───────────────────────────────────────────

    def _build_settings_tab(self):
        import tkinter as tk
        from tkinter import ttk, messagebox

        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Settings  ")

        ttk.Label(tab, text="Wallet Address:").pack(anchor="w")
        self.wallet_var = tk.StringVar(value=self.cfg.get("wallet_address", ""))
        ttk.Entry(tab, textvariable=self.wallet_var, width=55).pack(fill="x", pady=(2, 10))

        ttk.Label(tab, text="Private Key:").pack(anchor="w")
        self.key_var = tk.StringVar()
        self.key_entry = ttk.Entry(tab, textvariable=self.key_var, width=55, show="•")
        self.key_entry.pack(fill="x", pady=(2, 3))

        key_opts = ttk.Frame(tab)
        key_opts.pack(fill="x", pady=(0, 10))
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(key_opts, text="Show key", variable=self.show_key_var,
                        command=lambda: self.key_entry.config(show="" if self.show_key_var.get() else "•")
                        ).pack(side="left")
        ttk.Label(key_opts, text="  Encrypted with Windows DPAPI — leave empty to keep current",
                  style="Muted.TLabel").pack(side="left")

        auto_frame = ttk.LabelFrame(tab, text="Auto-Extend", padding=10)
        auto_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(auto_frame, text="Interval:").pack(side="left")
        self.interval_var = tk.StringVar(value=str(self.interval_days))
        ttk.Combobox(auto_frame, textvariable=self.interval_var,
                     values=["1", "2", "3", "7"],
                     width=5, state="readonly").pack(side="left", padx=(10, 5))
        ttk.Label(auto_frame, text="days").pack(side="left")

        vesting_frame = ttk.LabelFrame(tab, text="Vesting Rewards", padding=10)
        vesting_frame.pack(fill="x", pady=(0, 10))
        self.vesting_var = tk.BooleanVar(value=self.cfg.get("vesting_check_enabled", False))
        tk.Checkbutton(
            vesting_frame,
            text="Notify when vesting rewards are available",
            variable=self.vesting_var,
            wraplength=420,
        ).pack(anchor="w")
        vesting_interval = ttk.Frame(vesting_frame)
        vesting_interval.pack(fill="x", pady=(6, 0))
        ttk.Label(vesting_interval, text="Check every:").pack(side="left")
        self.vesting_interval_var = tk.StringVar(
            value=str(self.vesting_interval_days)
        )
        ttk.Combobox(
            vesting_interval,
            textvariable=self.vesting_interval_var,
            values=["1", "2", "3", "7"],
            width=5,
            state="readonly",
        ).pack(side="left", padx=(10, 5))
        ttk.Label(vesting_interval, text="days").pack(side="left")

        startup_frame = ttk.LabelFrame(tab, text="Windows Startup", padding=10)
        startup_frame.pack(fill="x", pady=(0, 10))
        self.autostart_var = tk.BooleanVar(value=self.cfg.get("autostart", False))
        ttk.Checkbutton(
            startup_frame,
            text="Start automatically when I log in",
            variable=self.autostart_var,
        ).pack(anchor="w")

        # Buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", pady=(15, 5))

        ttk.Button(btn_frame, text="  Save Settings  ", command=lambda: on_save()).pack(
            side="right", padx=(10, 0), ipady=3)
        ttk.Button(btn_frame, text="  Cancel  ", command=lambda: self.notebook.select(0)).pack(
            side="right", ipady=3)

        # Warning label
        ttk.Label(
            tab,
            text="⚠ Your private key is stored encrypted on this computer only.",
            style="Muted.TLabel",
        ).pack(side="bottom", anchor="w", pady=(10, 0))

        # Config path info
        ttk.Label(tab, text=f"Config: {CONFIG_FILE}", style="Muted.TLabel").pack(
            side="bottom", anchor="w", pady=(10, 0))

        def on_save():
            addr = self.wallet_var.get().strip()
            new_key = self.key_var.get().strip()
            interval_days = int(self.interval_var.get())
            vesting_interval_days = int(self.vesting_interval_var.get())

            if not addr:
                messagebox.showerror("Error", "Wallet address is required.")
                return
            if not addr.startswith("0x") or len(addr) != 42:
                messagebox.showerror("Error", "Invalid wallet address format.")
                return

            self.cfg["wallet_address"] = addr
            self.cfg["interval_days"] = interval_days
            self.cfg.pop("interval_hours", None)
            self.cfg["vesting_check_enabled"] = bool(self.vesting_var.get())
            self.cfg["vesting_interval_days"] = vesting_interval_days
            self.cfg.pop("vesting_interval_hours", None)
            self.cfg["autostart"] = bool(self.autostart_var.get())

            if new_key:
                self.cfg["private_key_enc"] = _encrypt_key(new_key)
                self.private_key = new_key

            self.interval_days = interval_days
            self.vesting_enabled = bool(self.vesting_var.get())
            self.vesting_interval_days = vesting_interval_days

            # Apply autostart setting
            if self.autostart_var.get():
                self._setup_autostart()
            else:
                self._remove_autostart()

            save_config(self.cfg)
            logger.info("Config saved")
            self.key_var.set("")
            messagebox.showinfo("Saved", "Settings saved successfully.\nRestart for scheduler changes.")

    # ── gUBI Tab ───────────────────────────────────────────────

    def _build_gubi_tab(self):
        import tkinter as tk
        from tkinter import ttk

        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="  gUBI  ")

        # Top cards row
        cards = ttk.Frame(tab)
        cards.pack(fill="x", pady=(0, 10))
        cards.columnconfigure((0, 1, 2), weight=1)

        self.gubi_card_rank = self._make_card(cards, "Rank", "—", "")
        self.gubi_card_rank.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.gubi_card_score = self._make_card(cards, "SoulScore", "—", "points")
        self.gubi_card_score.grid(row=0, column=1, sticky="nsew", padx=5)

        self.gubi_card_monthly = self._make_card(cards, "Monthly Reward", "—", "gUBI")
        self.gubi_card_monthly.grid(row=0, column=2, sticky="nsew", padx=(5, 0))

        # Details section
        detail_frame = ttk.LabelFrame(tab, text="Your gUBI", padding=10)
        detail_frame.pack(fill="x", pady=(0, 10))
        self._gubi_rows = {}
        for label in ["Share", "Pending Reward", "Available to Claim", "Total Earnings", "veGNET Balance"]:
            row = ttk.Frame(detail_frame)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=label + ":", width=22, anchor="w").pack(side="left")
            val_lbl = ttk.Label(row, text="—")
            val_lbl.pack(side="left")
            self._gubi_rows[label] = val_lbl

        # Pool section
        pool_frame = ttk.LabelFrame(tab, text="gUBI Pool", padding=10)
        pool_frame.pack(fill="x", pady=(0, 10))
        self._gubi_pool_rows = {}
        for label in ["Pool Value", "gUBI Price", "Composition", "Total Users", "Monthly Emission"]:
            row = ttk.Frame(pool_frame)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=label + ":", width=22, anchor="w").pack(side="left")
            val_lbl = ttk.Label(row, text="—")
            val_lbl.pack(side="left")
            self._gubi_pool_rows[label] = val_lbl

        # Refresh button
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", pady=(5, 5))
        self.gubi_btn_refresh = ttk.Button(
            btn_frame, text="  Refresh gUBI  ", command=self._refresh_gubi,
        )
        self.gubi_btn_refresh.pack(side="left", ipady=3)

        self.gubi_status = ttk.Label(tab, text="", style="Muted.TLabel")
        self.gubi_status.pack(anchor="w")

    def _refresh_gubi(self):
        """Fetch gUBI data from API in background thread."""
        threading.Thread(target=self._fetch_gubi_bg, daemon=True).start()

    def _fetch_gubi_bg(self):
        """Background fetch of gUBI user + stats + pool data."""
        import urllib.request
        headers = {
            "Accept": "application/json",
            "User-Agent": "GalacticaExtender/" + VERSION,
        }
        wallet = self.cfg.get("wallet_address", "")
        if not wallet:
            self.root.after(0, lambda: self.gubi_status.configure(text="No wallet configured"))
            return

        try:
            # Fetch user data
            user_url = f"{GUBI_API}/user/{wallet}?chainId=613419"
            req = urllib.request.Request(user_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                user_data = json.loads(resp.read())

            # Fetch stats
            stats_url = f"{GUBI_API}/stats?chainId=613419"
            req = urllib.request.Request(stats_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                stats_data = json.loads(resp.read())

            # Fetch pool
            pool_url = f"{GUBI_API}/pool?chainId=613419"
            req = urllib.request.Request(pool_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                pool_data = json.loads(resp.read())

            self.root.after(0, lambda: self._update_gubi_ui(user_data, stats_data, pool_data))
        except Exception as e:
            logger.debug(f"gUBI fetch failed: {e}")
            self.root.after(0, lambda: self.gubi_status.configure(
                text=f"Failed to load gUBI data: {e}"))

    def _update_gubi_ui(self, user: dict, stats: dict, pool: dict):
        """Update gUBI tab with fetched data."""
        total_users = stats.get("totalUsers", "?")
        rank = user.get("rank", "?")
        self.gubi_card_rank._val_lbl.configure(text=f"#{rank}")
        self.gubi_card_rank._unit_lbl.configure(text=f"/ {total_users}")

        self.gubi_card_score._val_lbl.configure(
            text=f"{user.get('soulScore', 0):,}")

        monthly = user.get("monthlyReward", "0")
        self.gubi_card_monthly._val_lbl.configure(text=str(monthly))

        share = user.get("share", 0)
        self._gubi_rows["Share"].configure(text=f"{share * 100:.2f}%")

        pending = user.get("pendingReward", "0")
        self._gubi_rows["Pending Reward"].configure(text=f"{pending} gUBI")

        available = user.get("availableReward", "0")
        self._gubi_rows["Available to Claim"].configure(text=f"{available} gUBI")

        earnings = user.get("totalEarnings", "0")
        self._gubi_rows["Total Earnings"].configure(text=f"{earnings} gUBI")

        # Parse veGNET from JSON string
        vegnet_raw = user.get("veGNET", "{}")
        try:
            vegnet_dict = json.loads(vegnet_raw) if isinstance(vegnet_raw, str) else vegnet_raw
            vegnet_val = sum(float(v) for v in vegnet_dict.values())
            self._gubi_rows["veGNET Balance"].configure(text=f"{vegnet_val:,.2f} veGNET")
        except Exception:
            self._gubi_rows["veGNET Balance"].configure(text=str(vegnet_raw))

        # Pool info
        pool_usd = pool.get("totalWorthUSD", 0)
        self._gubi_pool_rows["Pool Value"].configure(text=f"${pool_usd:.4f} USD")

        gubi_price = pool.get("gubiPrice", "0")
        self._gubi_pool_rows["gUBI Price"].configure(text=f"{float(gubi_price):.12f} USDC")

        comp = pool.get("composition", [])
        if comp:
            parts = []
            for c in comp:
                bal = int(c.get("balance", 0)) / 10**18
                parts.append(f"{bal:,.2f} {c.get('symbol', '?')}")
            self._gubi_pool_rows["Composition"].configure(text="  |  ".join(parts))

        self._gubi_pool_rows["Total Users"].configure(text=str(total_users))

        emission = stats.get("totalMonthlyEmission", "?")
        self._gubi_pool_rows["Monthly Emission"].configure(text=f"{emission} gUBI/month")

        self.gubi_status.configure(
            text=f"Last updated: {datetime.now():%H:%M:%S}")

    # ── Log Tab ────────────────────────────────────────────────

    def _build_log_tab(self):
        import tkinter as tk
        from tkinter import ttk

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Log  ")

        self.log_text = tk.Text(
            tab, font=("Consolas", 9), wrap="word", state="disabled",
        )
        scrollbar = ttk.Scrollbar(tab, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Add a logging handler that writes to the text widget
        self._log_handler = _TkLogHandler(self.log_text, self.root)
        self._log_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s"))
        logging.getLogger().addHandler(self._log_handler)

    # ── Countdown ticker ───────────────────────────────────────

    def _tick_countdown(self):
        """Update the footer with time until next extend, repeats every 30s."""
        try:
            if self.scheduler:
                job = self.scheduler.get_job("extend_job")
                if job and job.next_run_time:
                    now = datetime.now(job.next_run_time.tzinfo)
                    delta = job.next_run_time - now
                    secs = max(int(delta.total_seconds()), 0)
                    d, remainder = divmod(secs, 86400)
                    h, m = divmod(remainder // 60, 60)
                    if d > 0:
                        txt = f"Next extend in {d}d {h}h"
                    elif h > 0:
                        txt = f"Next extend in {h}h {m:02d}m"
                    else:
                        txt = f"Next extend in {m}m"
                    self.footer_label.configure(text=txt)
        except Exception:
            pass
        self.root.after(30_000, self._tick_countdown)

    # ── Update checker ─────────────────────────────────────────

    def _check_for_update(self):
        """Check GitHub for a newer release (runs in background thread)."""
        try:
            import urllib.request, json as _json
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())
            remote_tag = data.get("tag_name", "")  # e.g. "v1.0.3"
            remote_ver = remote_tag.lstrip("v")
            if self._is_newer(remote_ver, VERSION):
                html_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest")
                self.root.after(0, self._show_update_banner, remote_tag, html_url)
            else:
                logger.debug(f"Up to date (local={VERSION}, remote={remote_ver})")
        except Exception as e:
            logger.debug(f"Update check failed: {e}")

    @staticmethod
    def _is_newer(remote: str, local: str) -> bool:
        """Compare semver strings, return True if remote > local."""
        try:
            r = tuple(int(x) for x in remote.split("."))
            l = tuple(int(x) for x in local.split("."))
            return r > l
        except Exception:
            return False

    def _show_update_banner(self, tag: str, url: str):
        self._update_url = url
        self._update_label.configure(text=f"⬆ New version {tag} available — click to download")
        self._update_frame.pack(fill="x", before=self.notebook)

    def _on_update_click(self, _event=None):
        if self._update_url:
            import webbrowser
            webbrowser.open(self._update_url)

    # ── Refresh stats ──────────────────────────────────────────

    def _refresh_stats(self):
        self.status_label.configure(text="Loading…")
        threading.Thread(target=self._fetch_stats_bg, daemon=True).start()

    def _fetch_stats_bg(self):
        try:
            ext = self._build_extender()
            status = ext.get_status()
            status["vesting"] = {
                "enabled": bool(self.vesting_enabled),
                "has_new": False,
                "epochs_behind": 0,
                "total_claimed": 0.0,
                "last_notified": int(self.cfg.get("vesting_last_notified_epoch", 0) or 0),
                "last_check": self.cfg.get("vesting_last_check", "—"),
                "error": "",
            }

            if self.vesting_enabled and self.cfg.get("wallet_address"):
                try:
                    if not self.vesting_checker:
                        from gui.vesting_checker import VestingChecker
                        self.vesting_checker = VestingChecker(
                            rpc_url="https://galactica-mainnet.g.alchemy.com/public",
                            user_address=self.cfg.get("wallet_address", ""),
                        )
                    has_new, epochs_behind, total_claimed = self.vesting_checker.check_new_rewards()
                    status["vesting"]["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    status["vesting"].update(
                        {
                            "has_new": bool(has_new),
                            "epochs_behind": int(epochs_behind),
                            "total_claimed": float(total_claimed),
                        }
                    )
                except Exception as e:
                    status["vesting"]["error"] = str(e)
            self._status_cache = status
            self.root.after(0, lambda: self._update_ui(status))
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            self.root.after(0, lambda: self._show_error(str(e)))

    def _update_ui(self, s: dict):
        self.card_locked._val_lbl.configure(text=f"{s['locked_gnet']:,.2f}")
        self.card_vegnet._val_lbl.configure(text=f"{s['vegnet_balance']:,.2f}")
        self.card_days._val_lbl.configure(text=f"{s['days_remaining']:.0f}")

        self._info_rows["Lock Ends"].configure(text=f"{s['lock_end']:%Y-%m-%d %H:%M} UTC")
        self._info_rows["Max Possible End"].configure(text=f"{s['max_new_end']:%Y-%m-%d %H:%M} UTC")

        if s["can_extend"]:
            self._info_rows["Extendable By"].configure(
                text=f"+{s['extend_days']:.0f} days  ✓", foreground="#008866")
            self.btn_extend.configure(state="normal")
        else:
            days_until = s.get("days_until_extendable", 0)
            if days_until > 0:
                self._info_rows["Extendable By"].configure(
                    text=f"At week-max — extendable in {days_until:.0f} d",
                    foreground="gray")
            else:
                self._info_rows["Extendable By"].configure(
                    text="Already at maximum", foreground="gray")
            self.btn_extend.configure(state="disabled")

        decay = s["locked_gnet"] / s["maxtime_days"] if s["maxtime_days"] else 0
        self._info_rows["veGNET Decay/Day"].configure(text=f"−{decay:,.2f} veGNET")

        if self.last_result:
            r = self.last_result
            if r["status"] == "success":
                self._info_rows["Last Action"].configure(
                    text=f"Extended — {r.get('new_end', ''):%Y-%m-%d}", foreground="#008866")
            elif r["status"] == "already_max":
                self._info_rows["Last Action"].configure(text="Already at max", foreground="gray")
            elif r["status"] == "error":
                self._info_rows["Last Action"].configure(
                    text=f"Error: {r.get('error', '')[:40]}", foreground="red")

        vest = s.get("vesting", {})
        if not vest.get("enabled"):
            self._vesting_rows["Vesting Status"].configure(text="Disabled", foreground="gray")
            self._vesting_rows["Epochs Behind"].configure(text="—", foreground="gray")
            self._vesting_rows["Total Claimed"].configure(text="—", foreground="gray")
            self._vesting_rows["Last Check"].configure(text="—", foreground="gray")
            self._vesting_rows["Last Notified"].configure(text="—", foreground="gray")
        elif vest.get("error"):
            self._vesting_rows["Vesting Status"].configure(text="Error", foreground="red")
            self._vesting_rows["Epochs Behind"].configure(text="—", foreground="red")
            self._vesting_rows["Total Claimed"].configure(text="—", foreground="red")
            self._vesting_rows["Last Check"].configure(text="—", foreground="red")
            self._vesting_rows["Last Notified"].configure(
                text=str(vest.get("last_notified", 0)), foreground="red"
            )
        else:
            if vest.get("has_new"):
                self._vesting_rows["Vesting Status"].configure(
                    text="Available", foreground="#008866"
                )
            else:
                self._vesting_rows["Vesting Status"].configure(text="None", foreground="gray")
            self._vesting_rows["Epochs Behind"].configure(
                text=str(vest.get("epochs_behind", 0)), foreground="gray"
            )
            tc = vest.get("total_claimed", 0.0)
            self._vesting_rows["Total Claimed"].configure(
                text=f"{tc:,.4f} GNET" if tc else "—", foreground="gray"
            )
            self._vesting_rows["Last Check"].configure(
                text=str(vest.get("last_check", "—")), foreground="gray"
            )
            self._vesting_rows["Last Notified"].configure(
                text=str(vest.get("last_notified", 0)), foreground="gray"
            )

        self.status_label.configure(text=f"Connected — chain 613419")
        self.footer_label.configure(text=f"Wallet: {self.cfg.get('wallet_address', '?')}")

    def _show_error(self, msg: str):
        self.status_label.configure(text="Connection error")
        self.result_label.configure(text=msg, style="Error.TLabel")

    # ── Extend action ──────────────────────────────────────────

    def _on_extend_click(self):
        self.btn_extend.configure(state="disabled")
        self.result_label.configure(text="Sending transaction…", style="Status.TLabel")
        threading.Thread(target=self._do_extend_bg, daemon=True).start()

    def _do_extend_bg(self):
        try:
            ext = self._build_extender()
            result = ext.execute_extend()
            self.last_result = result
            self.root.after(0, lambda: self._show_extend_result(result))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))
        finally:
            self.root.after(0, lambda: self.btn_extend.configure(state="normal"))

    def _show_extend_result(self, r: dict):
        status = r["status"]
        if status == "success":
            self.result_label.configure(
                text=f"✓ Extended to {r['new_end']:%Y-%m-%d} — gas {r['gas_cost_gnet']:.6f} GNET",
                style="Status.TLabel")
        elif status == "already_max":
            days_until = r.get("days_until_extendable", 0)
            if days_until > 0:
                msg = (f"At week-boundary max — ends {r['lock_end']:%Y-%m-%d} "
                       f"(extendable in ~{days_until:.0f} d)")
            else:
                msg = f"Already at maximum — ends {r['lock_end']:%Y-%m-%d}"
            self.result_label.configure(text=msg, style="Muted.TLabel")
        elif status == "dry_run":
            self.result_label.configure(text="[DRY RUN] Would extend", style="Muted.TLabel")
        elif status == "gas_high":
            self.result_label.configure(
                text=f"Gas too high: {r.get('gas_gwei', 0):.1f} Gwei",
                style="Error.TLabel")
        elif status == "no_lock":
            self.result_label.configure(text="No active lock found", style="Error.TLabel")
        else:
            self.result_label.configure(
                text=f"Error: {r.get('error', 'Unknown')}", style="Error.TLabel")
        self._refresh_stats()

    # ── Build extender ─────────────────────────────────────────

    def _build_extender(self):
        os.environ["PRIVATE_KEY"] = self.private_key
        os.environ["WALLET_ADDRESS"] = self.cfg["wallet_address"]
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from extend import GalacticaExtender
            return GalacticaExtender(dry_run=False)
        finally:
            os.environ.pop("PRIVATE_KEY", None)

    # ── Tray icon ──────────────────────────────────────────────

    def start_tray(self):
        """Start system tray icon + scheduler in background."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from PIL import Image, ImageDraw
            import pystray
            from pystray import MenuItem as Item
        except ImportError as e:
            logger.warning(f"Tray dependencies missing ({e}) — running without tray")
            return

        # Create tray icon from logo
        if LOGO_PATH.exists():
            img = Image.open(LOGO_PATH).resize((64, 64), Image.LANCZOS)
        else:
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([4, 4, 60, 60], fill="#00D4AA")

        # Scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self._scheduled_extend,
            trigger=IntervalTrigger(days=self.interval_days),
            id="extend_job",
            replace_existing=True,
        )
        if self.vesting_enabled:
            self.scheduler.add_job(
                self._scheduled_vesting_check,
                trigger=IntervalTrigger(days=self.vesting_interval_days),
                id="vesting_job",
                replace_existing=True,
                next_run_time=datetime.now(),
            )
        self.scheduler.add_job(
            self._check_for_update,
            trigger=IntervalTrigger(hours=6),
            id="update_check_job",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(
            f"Scheduler started — extend every {self.interval_days}d, "
            f"vesting check every {self.vesting_interval_days}d"
        )

        def on_show(icon, item):
            self.root.after(0, self.root.deiconify)

        def on_extend_now(icon, item):
            threading.Thread(target=self._scheduled_extend, daemon=True).start()

        def on_quit(icon, item):
            if self.scheduler:
                self.scheduler.shutdown(wait=False)
            icon.stop()
            self.root.after(0, self.root.destroy)

        menu = pystray.Menu(
            Item("Show Window", on_show, default=True),
            Item("Extend Now", on_extend_now),
            pystray.Menu.SEPARATOR,
            Item(f"Auto: every {self.interval_days}d", None, enabled=False),
            pystray.Menu.SEPARATOR,
            Item("Quit", on_quit),
        )

        self.tray = pystray.Icon("GalacticaExtender", img, "veGNET Lock Extender", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _scheduled_extend(self):
        """Called by scheduler — extend and update UI."""
        try:
            ext = self._build_extender()
            result = ext.execute_extend()
            self.last_result = result

            status = result["status"]
            if status == "success":
                self._tray_notify("Lock Extended ✓",
                                  f"Extended to {result['new_end']:%Y-%m-%d}")
            elif status == "already_max":
                self._tray_notify("Already at Max",
                                  f"Lock ends {result['lock_end']:%Y-%m-%d}")
            elif status == "error":
                self._tray_notify("Extend Failed", result.get("error", "")[:60])

            self.root.after(0, self._refresh_stats)
        except Exception as e:
            logger.error(f"Scheduled extend failed: {e}")

    def _scheduled_vesting_check(self):
        """Check for new vesting rewards and notify if available."""
        if not self.vesting_enabled:
            return
        try:
            if not self.vesting_checker:
                from gui.vesting_checker import VestingChecker
                self.vesting_checker = VestingChecker(
                    rpc_url="https://galactica-mainnet.g.alchemy.com/public",
                    user_address=self.cfg.get("wallet_address", ""),
                )

            has_new, epochs_behind, _total = self.vesting_checker.check_new_rewards()
            if not has_new:
                return

            current_epoch = self.vesting_checker.contract.functions.currentEpoch().call()
            last_notified = int(self.cfg.get("vesting_last_notified_epoch", 0) or 0)
            if current_epoch <= last_notified:
                return

            self._tray_notify(
                "Vesting Rewards Available",
                f"You are {epochs_behind} epoch(s) behind",
            )
            self.cfg["vesting_last_notified_epoch"] = int(current_epoch)
            self.cfg["vesting_last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_config(self.cfg)
        except Exception as e:
            logger.warning(f"Vesting check failed: {e}")

    def _on_check_vesting_now(self):
        threading.Thread(target=self._check_vesting_now_bg, daemon=True).start()

    def _check_vesting_now_bg(self):
        try:
            self._scheduled_vesting_check()
            self.root.after(0, self._refresh_stats)
        except Exception as e:
            logger.warning(f"Manual vesting check failed: {e}")

    # ── Autostart helpers (Task Scheduler — bypasses SmartScreen) ─

    _TASK_NAME = "GalacticaExtender"

    def _setup_autostart(self):
        """Create a Task Scheduler task that runs the app at user logon.

        Uses XML import which works without admin privileges (unlike
        ``schtasks /Create /SC ONLOGON``).
        """
        try:
            import subprocess, tempfile, getpass

            if getattr(sys, "frozen", False):
                exe_path = str(Path(sys.executable).resolve())
            else:
                exe_path = (
                    f'{Path(sys.executable).resolve()}" '
                    f'"{Path(__file__).resolve()}'
                )
                # wrap properly for XML
                exe_path = str(Path(sys.executable).resolve())
                args_tag = f"<Arguments>\"{Path(__file__).resolve()}\"</Arguments>"

            # Remove old registry-based autostart if present
            self._remove_registry_autostart()

            # Build XML
            domain = os.environ.get("USERDOMAIN", "")
            user = getpass.getuser()
            user_id = f"{domain}\\{user}" if domain else user

            if getattr(sys, "frozen", False):
                action_xml = f"<Command>{exe_path}</Command>"
            else:
                action_xml = (
                    f"<Command>{Path(sys.executable).resolve()}</Command>\n"
                    f"          <Arguments>\"{Path(__file__).resolve()}\"</Arguments>"
                )

            xml = (
                '<?xml version="1.0" encoding="UTF-16"?>\n'
                '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
                "  <Triggers>\n"
                "    <LogonTrigger>\n"
                "      <Enabled>true</Enabled>\n"
                f"      <UserId>{user_id}</UserId>\n"
                "    </LogonTrigger>\n"
                "  </Triggers>\n"
                "  <Actions>\n"
                "    <Exec>\n"
                f"      {action_xml}\n"
                "    </Exec>\n"
                "  </Actions>\n"
                "  <Settings>\n"
                "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n"
                "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n"
                "    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>\n"
                "  </Settings>\n"
                "</Task>\n"
            )

            xml_path = Path(tempfile.gettempdir()) / "ge_task.xml"
            xml_path.write_text(xml, encoding="utf-16")

            # Delete existing task first (ignore errors)
            subprocess.run(
                ["schtasks", "/Delete", "/TN", self._TASK_NAME, "/F"],
                capture_output=True,
            )
            result = subprocess.run(
                ["schtasks", "/Create", "/TN", self._TASK_NAME,
                 "/XML", str(xml_path), "/F"],
                capture_output=True, text=True,
            )
            xml_path.unlink(missing_ok=True)

            if result.returncode == 0:
                logger.info("Autostart enabled (Task Scheduler)")
            else:
                logger.warning(f"schtasks create failed: {result.stderr.strip()}")
        except Exception as e:
            logger.warning(f"Failed to set autostart: {e}")

    def _remove_autostart(self):
        """Remove the Task Scheduler task."""
        try:
            import subprocess
            subprocess.run(
                ["schtasks", "/Delete", "/TN", self._TASK_NAME, "/F"],
                capture_output=True,
            )
            # Also clean up old registry key if it exists
            self._remove_registry_autostart()
            logger.info("Autostart disabled")
        except Exception as e:
            logger.warning(f"Failed to remove autostart: {e}")

    @staticmethod
    def _remove_registry_autostart():
        """Clean up legacy registry Run key from v1.0.2."""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                winreg.DeleteValue(key, "GalacticaExtender")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except Exception:
            pass

    def _tray_notify(self, title: str, msg: str):
        # Prefer winotify (supports app icon); fall back to pystray bubble
        notified = False
        try:
            from winotify import Notification
            ico_path = self._get_ico_path()
            toast = Notification(
                app_id="veGNET Lock Extender",
                title=title,
                msg=msg,
                icon=str(ico_path) if ico_path else "",
            )
            toast.show()
            notified = True
        except Exception:
            pass
        if not notified and self.tray:
            try:
                self.tray.notify(msg, title)
            except Exception:
                pass
        logger.info(f"[{title}] {msg}")

    @staticmethod
    def _get_ico_path() -> Path | None:
        """Convert LOGO_PNG.png → .ico in AppData (cached)."""
        ico = APP_DIR / "icon.ico"
        if ico.exists():
            return ico
        if not LOGO_PATH.exists():
            return None
        try:
            from PIL import Image
            img = Image.open(LOGO_PATH)
            img.save(str(ico), format="ICO",
                     sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            return ico
        except Exception:
            return None

    # ── Window close → minimize to tray ────────────────────────

    def _on_close(self):
        if self.tray:
            self.root.withdraw()  # hide to tray
        else:
            if self.scheduler:
                self.scheduler.shutdown(wait=False)
            self.root.destroy()

    def run(self):
        self.root.mainloop()


# ── Tk logging handler ─────────────────────────────────────────────

class _TkLogHandler(logging.Handler):
    """Logging handler that appends to a tk.Text widget."""

    def __init__(self, text_widget, root):
        super().__init__()
        self._text = text_widget
        self._root = root

    def emit(self, record):
        msg = self.format(record) + "\n"
        try:
            self._root.after(0, self._append, msg)
        except Exception:
            pass

    def _append(self, msg):
        self._text.configure(state="normal")
        self._text.insert("end", msg)
        self._text.see("end")
        self._text.configure(state="disabled")


# ═══════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Galactica Lock Extender GUI")
    parser.add_argument("--no-tray", action="store_true", help="Run once without GUI")
    args = parser.parse_args()

    cfg = load_config()

    # Import from restaker v1 if needed
    if not cfg.get("wallet_address"):
        v1 = _try_import_v1_config()
        if v1.get("wallet_address"):
            cfg.update(v1)
            save_config(cfg)
            logger.info(f"Imported wallet from restaker config: {cfg['wallet_address'][:10]}…")

    if args.no_tray:
        # Console one-shot mode
        if not cfg.get("wallet_address") or not cfg.get("private_key_enc"):
            print("No config found. Run without --no-tray to use the setup GUI.")
            return
        pk = _decrypt_key(cfg.get("private_key_enc", ""))
        os.environ["PRIVATE_KEY"] = pk
        os.environ["WALLET_ADDRESS"] = cfg["wallet_address"]
        try:
            from extend import GalacticaExtender
            ext = GalacticaExtender(dry_run=False)
            ext.print_status()
            result = ext.execute_extend()
            logger.info(f"Result: {result['status']}")
        finally:
            os.environ.pop("PRIVATE_KEY", None)
        return

    # If no config, show first-run setup inside the main GUI
    # (Settings tab will be used for initial setup too)
    if not cfg.get("wallet_address"):
        cfg["wallet_address"] = ""
    if not cfg.get("interval_days") and not cfg.get("interval_hours"):
        cfg["interval_days"] = 1
    if "vesting_check_enabled" not in cfg:
        cfg["vesting_check_enabled"] = False
    if not cfg.get("vesting_interval_days") and not cfg.get("vesting_interval_hours"):
        cfg["vesting_interval_days"] = 1
    if "vesting_last_notified_epoch" not in cfg:
        cfg["vesting_last_notified_epoch"] = 0
    if "vesting_last_check" not in cfg:
        cfg["vesting_last_check"] = "—"

    app = ExtenderGUI(cfg)

    # Start tray + scheduler only if we have a key
    if cfg.get("private_key_enc"):
        app.start_tray()

    app.run()


if __name__ == "__main__":
    main()
