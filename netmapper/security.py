"""Credential encryption helpers."""

import base64

from cryptography.fernet import Fernet, InvalidToken

from django.conf import settings


PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("netmapper", {}) or {}


def _coerce_fernet_key(raw_key):
    """Return a valid Fernet key or ``None`` when the value is unusable."""
    if not raw_key:
        return None

    if isinstance(raw_key, str):
        raw_key = raw_key.strip().encode("utf-8")

    try:
        Fernet(raw_key)
    except (TypeError, ValueError):
        return None
    return raw_key


def _derive_legacy_fernet_key():
    """Preserve legacy SECRET_KEY-derived encryption for backward compatibility."""
    secret_key = settings.SECRET_KEY.encode("utf-8")
    return base64.urlsafe_b64encode(secret_key.ljust(32)[:32])


PRIMARY_FERNET_KEY = (
    _coerce_fernet_key(PLUGIN_SETTINGS.get("CREDENTIAL_FERNET_KEY"))
    or _derive_legacy_fernet_key()
)
LEGACY_FERNET_KEY = _derive_legacy_fernet_key()


def get_primary_fernet():
    """Return the writer Fernet instance."""
    return Fernet(PRIMARY_FERNET_KEY)


def decrypt_secret(secret_value):
    """Decrypt with the configured key first, then the legacy fallback."""
    if not secret_value:
        return None

    encoded_value = (
        secret_value.encode("utf-8")
        if isinstance(secret_value, str)
        else secret_value
    )

    for key in dict.fromkeys([PRIMARY_FERNET_KEY, LEGACY_FERNET_KEY]):
        try:
            return Fernet(key).decrypt(encoded_value).decode("utf-8")
        except InvalidToken:
            continue

    return secret_value


def is_encrypted(secret_value):
    """Return True when the value can be decrypted by any accepted key."""
    if not secret_value:
        return False

    encoded_value = (
        secret_value.encode("utf-8")
        if isinstance(secret_value, str)
        else secret_value
    )
    for key in dict.fromkeys([PRIMARY_FERNET_KEY, LEGACY_FERNET_KEY]):
        try:
            Fernet(key).decrypt(encoded_value)
            return True
        except InvalidToken:
            continue
    return False
