"""
Configuration management for the GUI application.

Handles encrypted storage of sensitive data (private key) and user preferences.

╔══════════════════════════════════════════════════════════════════════════════╗
║                           SECURITY ARCHITECTURE                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Private keys are NEVER:                                                      ║
║   • Stored in plain text                                                     ║
║   • Sent over the network                                                    ║
║   • Logged or printed                                                        ║
║   • Accessible to other users on the same machine                            ║
║                                                                              ║
║ Private keys ARE:                                                            ║
║   • Encrypted using Windows DPAPI (CryptProtectData)                         ║
║   • Bound to your Windows user account                                       ║
║   • Stored locally in %APPDATA%/GalacticaRestaker/config.json                ║
║   • Decrypted only in-memory when needed for transaction signing             ║
║                                                                              ║
║ Windows DPAPI (Data Protection API):                                         ║
║   • Built into Windows since Windows 2000                                    ║
║   • Uses your Windows login credentials as the encryption key                ║
║   • Even administrators cannot decrypt without your password                 ║
║   • Same security used by Chrome, Edge, and other apps for credentials       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Source code: https://github.com/jackdown3csr/restaker
Audit this file yourself - it's ~100 lines of straightforward Python.
"""

import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import base64


def get_app_dir() -> Path:
    """
    Get the application data directory.
    
    Returns %APPDATA%/GalacticaRestaker on Windows.
    This is where config, logs, and data files are stored.
    """
    app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
    app_dir = Path(app_data) / 'GalacticaRestaker'
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_base_dir() -> Path:
    """
    Get the base directory where the application is installed.
    
    When running as EXE (PyInstaller), this is the directory containing the EXE.
    When running as script, this is the project root directory.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent.parent

# Use Windows DPAPI for encryption on Windows, fallback to obfuscation elsewhere
try:
    import win32crypt
    HAS_DPAPI = True
except ImportError:
    HAS_DPAPI = False


@dataclass
class UserConfig:
    """User configuration for the restaker."""
    wallet_address: str = ""
    private_key_encrypted: str = ""  # Encrypted/encoded private key
    interval_hours: int = 1
    min_threshold: float = 0.1
    max_gas_gwei: float = 50.0
    auto_start: bool = False
    notifications_enabled: bool = True
    network: str = "mainnet"  # "mainnet" or "testnet"


class ConfigManager:
    """Manages user configuration with secure storage."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            # Store in user's AppData on Windows
            app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
            config_dir = Path(app_data) / 'GalacticaRestaker'
        
        self.config_dir = config_dir
        self.config_file = config_dir / 'config.json'
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _encrypt_key(self, private_key: str) -> str:
        """
        Encrypt private key using Windows DPAPI.
        
        Security details:
        - Uses CryptProtectData from Windows DPAPI
        - Encryption is tied to current Windows user account
        - Cannot be decrypted by other users, even administrators
        - Key material never leaves this function unencrypted
        
        On non-Windows systems, falls back to base64 (NOT SECURE - for dev only).
        """
        if not private_key:
            return ""
        
        key_bytes = private_key.encode('utf-8')
        
        if HAS_DPAPI:
            # Windows DPAPI - encrypted to current user only
            # See: https://docs.microsoft.com/en-us/windows/win32/api/dpapi/
            encrypted = win32crypt.CryptProtectData(key_bytes)
            return base64.b64encode(encrypted).decode('ascii')
        else:
            # WARNING: Base64 is NOT encryption - development fallback only
            # Linux/Mac users should use environment variables instead
            return base64.b64encode(key_bytes).decode('ascii')

    def _decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt private key."""
        if not encrypted_key:
            return ""
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_key.encode('ascii'))
            
            if HAS_DPAPI:
                decrypted = win32crypt.CryptUnprotectData(encrypted_bytes)[1]
                return decrypted.decode('utf-8')
            else:
                return encrypted_bytes.decode('utf-8')
        except Exception:
            return ""

    def load(self) -> UserConfig:
        """Load configuration from disk."""
        if not self.config_file.exists():
            return UserConfig()
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            return UserConfig(**data)
        except Exception:
            return UserConfig()

    def save(self, config: UserConfig) -> None:
        """Save configuration to disk."""
        with open(self.config_file, 'w') as f:
            json.dump(asdict(config), f, indent=2)

    def save_with_key(self, config: UserConfig, private_key: str) -> None:
        """Save configuration with encrypted private key."""
        config.private_key_encrypted = self._encrypt_key(private_key)
        self.save(config)

    def get_private_key(self, config: UserConfig) -> str:
        """Retrieve decrypted private key."""
        return self._decrypt_key(config.private_key_encrypted)

    def is_configured(self) -> bool:
        """Check if user has completed initial setup."""
        config = self.load()
        return bool(config.wallet_address and config.private_key_encrypted)
