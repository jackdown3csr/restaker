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
    """
    Create a Galactica-style spiral/galaxy tray icon.
    
    The icon features a stylized spiral galaxy shape with the brand color,
    representing the Galactica network.
    """
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    center = size // 2
    
    # Draw outer glow circle
    margin = size // 10
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=color
    )
    
    # Draw inner dark circle for contrast
    inner_margin = size // 5
    draw.ellipse(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
        fill="#1a1a2e"
    )
    
    # Draw spiral arms (simplified as curved lines)
    import math
    for arm in range(3):
        angle_offset = arm * (2 * math.pi / 3)
        points = []
        for i in range(20):
            t = i / 19.0
            angle = angle_offset + t * 2.5
            radius = (size // 6) + t * (size // 4)
            x = center + radius * math.cos(angle)
            y = center + radius * math.sin(angle)
            points.append((x, y))
        
        # Draw spiral arm as thick line segments
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]], fill=color, width=max(2, size // 20))
    
    # Draw bright center
    center_size = size // 8
    draw.ellipse(
        [center - center_size, center - center_size, 
         center + center_size, center + center_size],
        fill="white"
    )
    
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
        return pystray.Menu(
            Item(lambda text: self._get_status_text(), None, enabled=False),
            Item(lambda text: self._get_result_text(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            Item(
                lambda text: "⏸️ Pause" if self.get_status().get('running', False) else "▶️ Start",
                self._on_toggle_click
            ),
            Item("🔄 Run Now", self._on_run_now_click),
            pystray.Menu.SEPARATOR,
            Item("⚙️ Settings", self._on_settings_click),
            pystray.Menu.SEPARATOR,
            Item("❌ Exit", self._on_exit_click),
        )

    def _get_status_text(self) -> str:
        """Get status text for menu."""
        status = self.get_status()
        is_running = status.get('running', False)
        next_run = status.get('next_run')
        
        if is_running and next_run:
            next_str = next_run.strftime('%H:%M') if isinstance(next_run, datetime) else str(next_run)
            return f"Next run: {next_str}"
        elif is_running:
            return "Running..."
        else:
            return "Stopped"

    def _get_result_text(self) -> str:
        """Get last result text for menu."""
        status = self.get_status()
        last_result = status.get('last_result')
        
        if last_result:
            result_status = last_result.get('status', '')
            if result_status == 'Success':
                amount = last_result.get('amount_restaked', 0)
                return f"Last: +{amount:.4f} GNET"
            elif result_status == 'Skipped':
                return "Last: Skipped (below threshold)"
            elif result_status == 'Failed':
                return "Last: Failed"
            else:
                return "Last: Unknown"
        return "No runs yet"

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
        if self.icon:
            self.icon.stop()
        self.on_exit()

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
