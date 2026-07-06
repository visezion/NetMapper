"""Tests for credential encryption helpers."""

from importlib import reload

from cryptography.fernet import Fernet

from django.test import SimpleTestCase, override_settings

import netmapper.security as security


class CredentialSecurityTest(SimpleTestCase):
    """Validate dedicated and legacy credential-key behavior."""

    @override_settings(
        SECRET_KEY="legacy-secret-key-for-tests-0123456789",
        PLUGINS_CONFIG={"netmapper": {}},
    )
    def test_legacy_secret_key_fallback_keeps_existing_values_readable(self):
        """Legacy SECRET_KEY-derived tokens should still decrypt."""
        security_module = reload(security)
        legacy_token = (
            Fernet(security_module.LEGACY_FERNET_KEY)
            .encrypt(b"legacy-password")
            .decode("utf-8")
        )

        self.assertEqual(
            security_module.decrypt_secret(legacy_token),
            "legacy-password",
        )

    @override_settings(
        SECRET_KEY="legacy-secret-key-for-tests-0123456789",
        PLUGINS_CONFIG={
            "netmapper": {
                "CREDENTIAL_FERNET_KEY": Fernet.generate_key().decode("utf-8")
            }
        },
    )
    def test_dedicated_key_is_used_for_new_encryption(self):
        """Configured plugin key should become the primary writer key."""
        security_module = reload(security)
        token = (
            security_module.get_primary_fernet()
            .encrypt(b"dedicated-password")
            .decode("utf-8")
        )

        self.assertEqual(
            security_module.decrypt_secret(token),
            "dedicated-password",
        )
        self.assertNotEqual(
            security_module.PRIMARY_FERNET_KEY,
            security_module.LEGACY_FERNET_KEY,
        )
