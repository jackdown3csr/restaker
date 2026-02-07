"""
Setup dialog for initial configuration.

Simple tkinter GUI for first-time setup and settings changes.

SECURITY NOTE:
    Your private key is entered here ONCE and immediately encrypted using
    Windows DPAPI before being saved to disk. The key is NEVER:
    - Stored in plain text anywhere
    - Sent over the network
    - Logged or displayed after entry
    
    The entry field shows bullets (•) by default. You can toggle visibility
    to verify your key before saving, but the actual key is only held in
    memory during this dialog session.
    
    After clicking "Start Restaking", the encrypted key is stored in:
    %APPDATA%/GalacticaRestaker/config.json
    
    You can verify this file contains only encrypted data (base64 blob).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Callable, Optional

from .config_manager import ConfigManager, UserConfig


class SetupDialog:
    """Initial setup and settings dialog."""

    def __init__(self, config_manager: ConfigManager, on_complete: Optional[Callable[[UserConfig, str], None]] = None):
        """
        Initialize setup dialog.

        Args:
            config_manager: ConfigManager instance for loading/saving.
            on_complete: Callback when setup is complete (config, private_key).
        """
        self.config_manager = config_manager
        self.on_complete = on_complete
        self.config = config_manager.load()
        self.private_key = config_manager.get_private_key(self.config)
        
        self.root: Optional[tk.Tk] = None
        self.result = False

    def show(self) -> bool:
        """Show the setup dialog. Returns True if setup completed."""
        self.root = tk.Tk()
        self.root.title("Galactica Restaker - Setup")
        self.root.geometry("450x580")
        self.root.resizable(False, False)
        
        # Set window icon
        try:
            from .tray import create_icon_image
            from PIL import ImageTk
            icon_image = create_icon_image(size=32)
            self._icon_photo = ImageTk.PhotoImage(icon_image)
            self.root.iconphoto(True, self._icon_photo)
        except Exception:
            pass  # Icon is optional
        
        # Center window
        self.root.eval('tk::PlaceWindow . center')

        self._create_widgets()
        self.root.mainloop()
        
        return self.result

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        root = self.root
        
        # Main frame with padding
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Galactica Auto-Restaker",
            font=('Segoe UI', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))

        # Wallet Address
        ttk.Label(main_frame, text="Wallet Address:").pack(anchor=tk.W)
        self.wallet_entry = ttk.Entry(main_frame, width=55)
        self.wallet_entry.insert(0, self.config.wallet_address)
        self.wallet_entry.pack(fill=tk.X, pady=(2, 10))

        # Private Key
        ttk.Label(main_frame, text="Private Key:").pack(anchor=tk.W)
        self.key_entry = ttk.Entry(main_frame, width=55, show="•")
        self.key_entry.insert(0, self.private_key)
        self.key_entry.pack(fill=tk.X, pady=(2, 5))
        
        # Show/hide key toggle
        self.show_key_var = tk.BooleanVar(value=False)
        show_key_cb = ttk.Checkbutton(
            main_frame,
            text="Show key",
            variable=self.show_key_var,
            command=self._toggle_key_visibility
        )
        show_key_cb.pack(anchor=tk.W, pady=(0, 10))

        # Interval selection
        interval_frame = ttk.Frame(main_frame)
        interval_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(interval_frame, text="Restake interval:").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value=str(self.config.interval_hours))
        interval_combo = ttk.Combobox(
            interval_frame,
            textvariable=self.interval_var,
            values=["1", "6", "12", "24"],
            width=5,
            state="readonly"
        )
        interval_combo.pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(interval_frame, text="hours").pack(side=tk.LEFT)

        # Min threshold
        threshold_frame = ttk.Frame(main_frame)
        threshold_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(threshold_frame, text="Min threshold:").pack(side=tk.LEFT)
        self.threshold_var = tk.StringVar(value=str(self.config.min_threshold))
        threshold_entry = ttk.Entry(threshold_frame, textvariable=self.threshold_var, width=8)
        threshold_entry.pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(threshold_frame, text="GNET").pack(side=tk.LEFT)

        # Max gas price
        gas_frame = ttk.Frame(main_frame)
        gas_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(gas_frame, text="Max gas price:").pack(side=tk.LEFT)
        self.max_gas_var = tk.StringVar(value=str(self.config.max_gas_gwei))
        gas_entry = ttk.Entry(gas_frame, textvariable=self.max_gas_var, width=8)
        gas_entry.pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(gas_frame, text="Gwei").pack(side=tk.LEFT)

        # Network selection
        network_frame = ttk.Frame(main_frame)
        network_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(network_frame, text="Network:").pack(side=tk.LEFT)
        self.network_var = tk.StringVar(value=self.config.network)
        network_combo = ttk.Combobox(
            network_frame,
            textvariable=self.network_var,
            values=["mainnet", "testnet"],
            width=10,
            state="readonly"
        )
        network_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Options
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=(0, 15))

        self.autostart_var = tk.BooleanVar(value=self.config.auto_start)
        autostart_cb = ttk.Checkbutton(
            options_frame,
            text="Start with Windows",
            variable=self.autostart_var
        )
        autostart_cb.pack(anchor=tk.W)

        self.notify_var = tk.BooleanVar(value=self.config.notifications_enabled)
        notify_cb = ttk.Checkbutton(
            options_frame,
            text="Show notifications",
            variable=self.notify_var
        )
        notify_cb.pack(anchor=tk.W)

        self.dryrun_var = tk.BooleanVar(value=self.config.dry_run)
        dryrun_cb = ttk.Checkbutton(
            options_frame,
            text="Dry-run mode (simulate only)",
            variable=self.dryrun_var
        )
        dryrun_cb.pack(anchor=tk.W)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 5))

        start_btn = ttk.Button(
            button_frame,
            text="  Start Restaking  ",
            command=self._on_start,
            style='Accent.TButton'
        )
        start_btn.pack(side=tk.RIGHT, padx=(10, 0), ipady=4)

        cancel_btn = ttk.Button(
            button_frame,
            text="  Cancel  ",
            command=self._on_cancel
        )
        cancel_btn.pack(side=tk.RIGHT, ipady=4)

        # Warning label
        warning = ttk.Label(
            main_frame,
            text="⚠️ Your private key is stored encrypted on this computer only.",
            font=('Segoe UI', 8),
            foreground='gray'
        )
        warning.pack(side=tk.BOTTOM, pady=(10, 0))

    def _toggle_key_visibility(self) -> None:
        """Toggle private key visibility."""
        if self.show_key_var.get():
            self.key_entry.config(show="")
        else:
            self.key_entry.config(show="•")

    def _validate(self) -> bool:
        """Validate form inputs."""
        wallet = self.wallet_entry.get().strip()
        key = self.key_entry.get().strip()

        if not wallet:
            messagebox.showerror("Error", "Wallet address is required.")
            return False

        if not wallet.startswith("0x") or len(wallet) != 42:
            messagebox.showerror("Error", "Invalid wallet address format.")
            return False

        if not key:
            messagebox.showerror("Error", "Private key is required.")
            return False

        if not key.startswith("0x"):
            key = "0x" + key

        if len(key) != 66:
            messagebox.showerror("Error", "Invalid private key format.")
            return False

        # Verify private key matches wallet address
        try:
            from eth_account import Account
            derived = Account.from_key(key).address
            if derived.lower() != wallet.lower():
                messagebox.showerror(
                    "Error",
                    f"Private key does not match wallet address.\n"
                    f"Key derives: {derived}\n"
                    f"You entered: {wallet}"
                )
                return False
        except Exception as e:
            messagebox.showerror("Error", f"Invalid private key: {e}")
            return False

        try:
            float(self.threshold_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid threshold value.")
            return False

        try:
            val = float(self.max_gas_var.get())
            if val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid max gas price value.")
            return False

        return True

    def _on_start(self) -> None:
        """Handle start button click."""
        if not self._validate():
            return

        # Update config
        self.config.wallet_address = self.wallet_entry.get().strip()
        self.config.interval_hours = int(self.interval_var.get())
        self.config.min_threshold = float(self.threshold_var.get())
        self.config.max_gas_gwei = float(self.max_gas_var.get())
        self.config.network = self.network_var.get()
        self.config.auto_start = self.autostart_var.get()
        self.config.notifications_enabled = self.notify_var.get()
        self.config.dry_run = self.dryrun_var.get()

        private_key = self.key_entry.get().strip()
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        # Save config
        self.config_manager.save_with_key(self.config, private_key)

        # Handle auto-start
        if self.config.auto_start:
            self._setup_autostart()
        else:
            self._remove_autostart()

        self.result = True
        
        if self.on_complete:
            self.on_complete(self.config, private_key)

        self.root.destroy()

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.result = False
        self.root.destroy()

    def _setup_autostart(self) -> None:
        """Add application to Windows startup."""
        try:
            import winreg
            import sys

            if getattr(sys, 'frozen', False):
                # PyInstaller EXE \u2014 sys.executable is the .exe itself
                cmd = f'"{ sys.executable}"'
            else:
                # Running as script \u2014 need python.exe + script path
                script = str(Path(__file__).resolve().parent / 'main.py')
                cmd = f'"{sys.executable}" "{script}"'

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "GalacticaRestaker", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
        except Exception:
            pass  # Fail silently

    def _remove_autostart(self) -> None:
        """Remove application from Windows startup."""
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, "GalacticaRestaker")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except Exception:
            pass  # Fail silently
