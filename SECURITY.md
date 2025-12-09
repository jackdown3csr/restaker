# Security

This document explains how Galactica Restaker handles your private key.

## TL;DR

✅ Your private key **never leaves your computer**  
✅ Private key is **encrypted with Windows DPAPI** (same security as Chrome passwords)  
✅ No network requests contain your key - only signed transactions  
✅ All code is open source - audit it yourself  

---

## How Your Private Key is Protected

### GUI Application (v2.0+)

When you enter your private key in the setup dialog:

1. **Entry** - Key is typed into a masked field (shows `•••••`)
2. **Encryption** - Before saving, key is encrypted using [Windows DPAPI](https://docs.microsoft.com/en-us/windows/win32/api/dpapi/)
3. **Storage** - Encrypted blob saved to `%APPDATA%\GalacticaRestaker\config.json`
4. **Usage** - Decrypted only in-memory when signing transactions
5. **Memory** - Cleared after transaction is signed

### What is Windows DPAPI?

Windows Data Protection API (DPAPI) is:
- Built into Windows since Windows 2000
- Uses your Windows login credentials as the master key
- The same technology Chrome, Edge, Firefox use for saved passwords
- **Cannot be decrypted by other users**, even administrators
- Encryption is tied to your specific Windows user account

### CLI Version (v1.x)

The CLI version stores your key in `.env.local`:
- File is in `.gitignore` (never committed)
- Uses filesystem permissions (only your user can read)
- Consider using environment variables for additional security

---

## What I DON'T Do

❌ Send your private key over the network  
❌ Store keys in plain text (GUI version)  
❌ Log or print private keys  
❌ Use third-party key storage services  
❌ Phone home or collect telemetry  

---

## Verify Yourself

All code is open source. The relevant files are:

| File | Purpose | Lines |
|------|---------|-------|
| `gui/config_manager.py` | Key encryption/decryption | ~100 |
| `gui/setup_dialog.py` | Key entry UI | ~150 |
| `restake.py` | Transaction signing | ~200 |

Key encryption happens in `config_manager.py`:

```python
def _encrypt_key(self, private_key: str) -> str:
    key_bytes = private_key.encode('utf-8')
    if HAS_DPAPI:
        # Windows DPAPI - encrypted to current user only
        encrypted = win32crypt.CryptProtectData(key_bytes)
        return base64.b64encode(encrypted).decode('ascii')
```

Transaction signing uses web3.py's standard `sign_transaction()`:

```python
signed = self.web3.eth.account.sign_transaction(tx, self.private_key)
self.web3.eth.send_raw_transaction(signed.raw_transaction)
```

---

## Best Practices

1. **Use your Cypherbook wallet** - this must be the same wallet you use in [Galactica Cypherbook](https://app.galactica.com) where your stake lives
2. **Keep minimal extra funds** - only what you need for gas fees
3. **Review transactions** - check the logs in `logs/restake.log`
4. **Update regularly** - pull latest version for security fixes

---

## Reporting Security Issues

If you find a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email the maintainer directly (see GitHub profile)
3. Allow reasonable time for a fix before disclosure

---

## Config File Location

| Version | Location |
|---------|----------|
| GUI (v2.0+) | `%APPDATA%\GalacticaRestaker\config.json` |
| CLI (v1.x) | `.env.local` in project directory |

To delete your stored key:
- **GUI**: Delete `%APPDATA%\GalacticaRestaker\` folder
- **CLI**: Delete `.env.local` file

---

## FAQ

**Q: Can I move the config to another PC?**  
A: No. DPAPI encryption is tied to your Windows user account. You'll need to re-enter your key on the new machine.

**Q: What if I forget my Windows password?**  
A: If you reset your Windows password (not change it normally), DPAPI-encrypted data may become unrecoverable. Keep a backup of your private key separately.

**Q: Is base64 secure?**  
A: No. On non-Windows systems, we fall back to base64 which is NOT encryption. Use environment variables instead, or run on Windows for DPAPI protection.
