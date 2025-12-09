"""
System tray integration using pystray.

Provides background operation with tray icon and context menu.

SECURITY NOTE:
    This module handles ONLY the UI layer. It never accesses or stores
    private keys directly. All sensitive operations are delegated to
    the restaker module which loads keys from encrypted storage.
"""

import logging
import threading
from datetime import datetime
from typing import Callable, Optional

from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item

logger = logging.getLogger(__name__)


def create_icon_image(color: str = "#00D4AA", size: int = 64) -> Image.Image:
    """Create a simple tray icon image."""
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a filled circle with the brand color
    margin = size // 8
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=color,
        outline=color
    )
    
    # Draw a "G" or simple indicator
    # For simplicity, just a diamond shape in center
    center = size // 2
    diamond_size = size // 4
    draw.polygon([
        (center, center - diamond_size),
        (center + diamond_size, center),
        (center, center + diamond_size),
        (center - diamond_size, center),
    ], fill="white")
    
    return image


class TrayApp:
    """System tray application controller."""

    def __init__(
        self,
        on_settings: Callable[[], None],
        on_run_now: Callable[[], None],
        on_toggle: Callable[[bool], None],
        on_exit: Callable[[], None],
        get_status: Callable[[], dict],
    ):
        """
        Initialize tray application.

        Args:
            on_settings: Callback to open settings dialog.
            on_run_now: Callback to trigger immediate restake.
            on_toggle: Callback when scheduler is toggled (True=start, False=stop).
            on_exit: Callback on application exit.
            get_status: Callback to get current scheduler status.
        """
        self.on_settings = on_settings
        self.on_run_now = on_run_now
        self.on_toggle = on_toggle
        self.on_exit = on_exit
        self.get_status = get_status
        
        self.is_active = True
        self.icon: Optional[pystray.Icon] = None
        self._icon_thread: Optional[threading.Thread] = None

    def _create_menu(self) -> pystray.Menu:
        """Create context menu for tray icon."""
        status = self.get_status()
        is_running = status.get('running', False)
        next_run = status.get('next_run')
        last_result = status.get('last_result')

        # Status text
        if is_running and next_run:
            next_str = next_run.strftime('%H:%M') if isinstance(next_run, datetime) else str(next_run)
            status_text = f"Next run: {next_str}"
        elif is_running:
            status_text = "Running..."
        else:
            status_text = "Stopped"

        # Last result text
        if last_result:
            amount = last_result.get('amount_restaked', 0)
            result_text = f"Last: +{amount:.4f} GNET"
        else:
            result_text = "No runs yet"

        return pystray.Menu(
            Item(status_text, None, enabled=False),
            Item(result_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            Item(
                "⏸️ Pause" if is_running else "▶️ Start",
                self._on_toggle_click
            ),
            Item("🔄 Run Now", self._on_run_now_click),
            pystray.Menu.SEPARATOR,
            Item("⚙️ Settings", self._on_settings_click),
            pystray.Menu.SEPARATOR,
            Item("❌ Exit", self._on_exit_click),
        )

    def _on_toggle_click(self, icon, item) -> None:
        """Handle start/pause toggle."""
        status = self.get_status()
        is_running = status.get('running', False)
        self.on_toggle(not is_running)
        self._update_menu()

    def _on_run_now_click(self, icon, item) -> None:
        """Handle run now click."""
        self.on_run_now()
        self._update_menu()

    def _on_settings_click(self, icon, item) -> None:
        """Handle settings click."""
        self.on_settings()

    def _on_exit_click(self, icon, item) -> None:
        """Handle exit click."""
        self.is_active = False
        self.on_exit()
        if self.icon:
            self.icon.stop()

    def _update_menu(self) -> None:
        """Update the menu (refresh status)."""
        if self.icon:
            self.icon.menu = self._create_menu()

    def update_icon(self, success: bool = True) -> None:
        """Update icon color based on status."""
        color = "#00D4AA" if success else "#FF6B6B"
        if self.icon:
            self.icon.icon = create_icon_image(color)

    def show_notification(self, title: str, message: str) -> None:
        """Show a system notification."""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception as e:
                logger.warning(f"Failed to show notification: {e}")

    def run(self) -> None:
        """Run the tray application (blocking)."""
        self.icon = pystray.Icon(
            name="GalacticaRestaker",
            icon=create_icon_image(),
            title="Galactica Restaker",
            menu=self._create_menu()
        )
        self.icon.run()

    def run_detached(self) -> None:
        """Run the tray application in a background thread."""
        self._icon_thread = threading.Thread(target=self.run, daemon=True)
        self._icon_thread.start()

    def stop(self) -> None:
        """Stop the tray application."""
        self.is_active = False
        if self.icon:
            self.icon.stop()
