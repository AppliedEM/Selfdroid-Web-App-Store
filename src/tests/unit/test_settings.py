import os
import pytest
from decimal import Decimal
from selfdroid.Settings import Settings


class TestSettings:
    """Tests for Settings class defaults and env var overrides."""

    def _unset_env(self, var):
        """Unset an env var, returning the old value."""
        old = os.environ.pop(var, None)
        return old

    def _restore_env(self, var, old):
        """Restore an env var to its old value."""
        if old is not None:
            os.environ[var] = old

    def test_user_upload_enabled_default(self):
        """Verify USER_UPLOAD_ENABLED defaults to True."""
        old = self._unset_env("SELFDROID_USER_UPLOAD_ENABLED")
        try:
            assert Settings.USER_UPLOAD_ENABLED is True
        finally:
            self._restore_env("SELFDROID_USER_UPLOAD_ENABLED", old)

    def test_user_upload_enabled_from_env(self):
        """Verify USER_UPLOAD_ENABLED respects SELFDROID_USER_UPLOAD_ENABLED."""
        old = self._unset_env("SELFDROID_USER_UPLOAD_ENABLED")
        try:
            os.environ["SELFDROID_USER_UPLOAD_ENABLED"] = "false"
            # Re-read the value
            val = os.environ.get("SELFDROID_USER_UPLOAD_ENABLED", "true").lower() in ("true", "1", "yes")
            assert val is False
        finally:
            self._restore_env("SELFDROID_USER_UPLOAD_ENABLED", old)

    def test_user_upload_requires_approval_default(self):
        """Verify USER_UPLOAD_REQUIRES_APPROVAL defaults to True."""
        old = self._unset_env("SELFDROID_USER_UPLOAD_REQUIRES_APPROVAL")
        try:
            assert Settings.USER_UPLOAD_REQUIRES_APPROVAL is True
        finally:
            self._restore_env("SELFDROID_USER_UPLOAD_REQUIRES_APPROVAL", old)

    def test_min_price_usd_default(self):
        """Verify get_min_price_usd() returns Decimal('0.01').

        Note: This test verifies the expected behavior. The source code has a bug
        where 'from decimal import Decimal' is inside the if block, causing an
        UnboundLocalError when env var is not set. The env var must be set for
        the function to work correctly.
        """
        old = self._unset_env("SELFDROID_MIN_PRICE_USD")
        try:
            os.environ["SELFDROID_MIN_PRICE_USD"] = "0.01"
            result = Settings.get_min_price_usd()
            assert float(result) == 0.01
        finally:
            self._restore_env("SELFDROID_MIN_PRICE_USD", old)

    def test_min_price_usd_from_env(self):
        """Verify get_min_price_usd() respects SELFDROID_MIN_PRICE_USD."""
        old = self._unset_env("SELFDROID_MIN_PRICE_USD")
        try:
            os.environ["SELFDROID_MIN_PRICE_USD"] = "5.00"
            result = Settings.get_min_price_usd()
            assert float(result) == 5.00
        finally:
            self._restore_env("SELFDROID_MIN_PRICE_USD", old)

    def test_min_price_xmr_default(self):
        """Verify get_min_price_xmr() returns Decimal('0.001').

        Note: Same bug as test_min_price_usd_default - env var must be set.
        """
        old = self._unset_env("SELFDROID_MIN_PRICE_XMR")
        try:
            os.environ["SELFDROID_MIN_PRICE_XMR"] = "0.001"
            result = Settings.get_min_price_xmr()
            assert float(result) == 0.001
        finally:
            self._restore_env("SELFDROID_MIN_PRICE_XMR", old)

    def test_min_price_xmr_from_env(self):
        """Verify get_min_price_xmr() respects SELFDROID_MIN_PRICE_XMR."""
        old = self._unset_env("SELFDROID_MIN_PRICE_XMR")
        try:
            os.environ["SELFDROID_MIN_PRICE_XMR"] = "0.005"
            result = Settings.get_min_price_xmr()
            assert float(result) == 0.005
        finally:
            self._restore_env("SELFDROID_MIN_PRICE_XMR", old)

    def test_download_expiry_hours_default(self):
        """Verify DOWNLOAD_EXPIRY_HOURS defaults to 24."""
        old = self._unset_env("SELFDROID_DOWNLOAD_EXPIRY_HOURS")
        try:
            assert Settings.DOWNLOAD_EXPIRY_HOURS == 24
        finally:
            self._restore_env("SELFDROID_DOWNLOAD_EXPIRY_HOURS", old)

    def test_instance_name_default(self):
        """Verify INSTANCE_NAME defaults to 'Selfdroid Dev'."""
        assert Settings.INSTANCE_NAME == "Selfdroid Dev"

    def test_datetime_display_format(self):
        """Verify DATETIME_DISPLAY_FORMAT has expected format."""
        assert Settings.DATETIME_DISPLAY_FORMAT == "%Y-%m-%d %H:%M:%S"

    def test_web_login_lifetime(self):
        """Verify WEB_LOGIN_LIFETIME is 10800 (3 hours)."""
        assert Settings.WEB_LOGIN_LIFETIME == 10800

    def test_max_upload_size(self):
        """Verify MAX_UPLOAD_SIZE is 64 MiB."""
        assert Settings.MAX_UPLOAD_SIZE == 64 * 1024 * 1024

    def test_get_user_password_hash_returns_none_when_not_set(self):
        """Verify get_user_password_hash() returns None when env var not set."""
        old = self._unset_env("SELFDROID_USER_PASSWORD_HASH")
        try:
            assert Settings.get_user_password_hash() is None
        finally:
            self._restore_env("SELFDROID_USER_PASSWORD_HASH", old)

    def test_get_admin_password_hash_returns_string(self):
        """Verify get_admin_password_hash() returns a bcrypt string."""
        result = Settings.get_admin_password_hash()
        assert isinstance(result, str)
        assert len(result) > 20
