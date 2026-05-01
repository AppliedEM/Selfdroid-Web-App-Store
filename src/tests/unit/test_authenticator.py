import pytest
from unittest import mock
from selfdroid.web.authenticator.WebAuthenticator import WebAuthenticator
from selfdroid.web.authenticator.WebAuthenticatorLoginException import WebAuthenticatorLoginException
from selfdroid.web.authenticator.WebAuthenticatorLogoutException import WebAuthenticatorLogoutException
from selfdroid.Settings import Settings


class TestWebAuthenticator:
    """Tests for WebAuthenticator log_in_as_user_account and log_out."""

    @pytest.fixture
    def authenticator(self):
        return WebAuthenticator()

    @pytest.fixture
    def mock_session(self, authenticator):
        """Create a mock session object."""
        return mock.MagicMock()

    def test_log_in_as_user_account(self, authenticator):
        """Verify log_in_as_user_account() sets session vars correctly."""
        mock_session = mock.MagicMock()
        with mock.patch("flask.session", mock_session):
            with mock.patch.object(authenticator, "has_at_least_user_privileges", return_value=False):
                authenticator.log_in_as_user_account(42, "testuser")
                assert mock_session.__setitem__.call_count >= 4
                calls = {call[0][0]: call[0][1] for call in mock_session.__setitem__.call_args_list}
                assert calls["web_has_user_privileges"] is True
                assert calls["web_has_admin_privileges"] is False
                assert calls["user_account_id"] == 42
                assert calls["user_account_username"] == "testuser"
                assert "web_login_timestamp" in calls

    def test_log_in_as_user_account_already_logged(self, authenticator):
        """Verify log_in_as_user_account() raises exception if already logged in."""
        mock_session = mock.MagicMock()
        with mock.patch("flask.session", mock_session):
            with mock.patch.object(authenticator, "has_at_least_user_privileges", return_value=True):
                with pytest.raises(WebAuthenticatorLoginException, match="already logged in"):
                    authenticator.log_in_as_user_account(42, "testuser")

    def test_log_out_clears_user_account(self, authenticator):
        """Verify log_out() clears user_account_id and user_account_username."""
        mock_session = mock.MagicMock()
        mock_session.__contains__ = mock.MagicMock(side_effect=lambda k: k in ("web_has_user_privileges",))
        with mock.patch("flask.session", mock_session):
            with mock.patch.object(authenticator, "has_at_least_user_privileges", return_value=True):
                authenticator.log_out()
                popped_keys = [call[0][0] for call in mock_session.pop.call_args_list]
                assert "user_account_id" in popped_keys
                assert "user_account_username" in popped_keys
                assert "web_has_user_privileges" in popped_keys
                assert "web_login_timestamp" in popped_keys

    def test_log_out_raises_when_not_logged_in(self, authenticator):
        """Verify log_out() raises exception when not logged in."""
        mock_session = mock.MagicMock()
        with mock.patch("flask.session", mock_session):
            with mock.patch.object(authenticator, "has_at_least_user_privileges", return_value=False):
                with pytest.raises(WebAuthenticatorLogoutException):
                    authenticator.log_out()

    def test_has_at_least_user_privileges_true(self, authenticator):
        """Verify has_at_least_user_privileges returns True when valid."""
        from selfdroid.Helpers import Helpers
        ts = Helpers.get_current_unix_timestamp()
        mock_session = mock.MagicMock()
        mock_session.get = mock.MagicMock(side_effect=lambda k, default=None: {
            "web_has_user_privileges": True,
            "web_login_timestamp": ts,
        }.get(k, default))
        with mock.patch("flask.session", mock_session):
            with mock.patch("selfdroid.Settings.Settings.MINIMUM_WEB_LOGIN_TIMESTAMP", 0):
                assert authenticator.has_at_least_user_privileges() is True

    def test_has_at_least_user_privileges_false_when_not_set(self, authenticator):
        """Verify has_at_least_user_privileges returns False when not set."""
        mock_session = mock.MagicMock()
        mock_session.get = mock.MagicMock(return_value=None)
        with mock.patch("flask.session", mock_session):
            assert authenticator.has_at_least_user_privileges() is False

    def test_has_at_least_user_privileges_expired(self, authenticator):
        """Verify has_at_least_user_privileges returns False when expired."""
        mock_session = mock.MagicMock()
        mock_session.get = mock.MagicMock(side_effect=lambda k, default=None: {
            "web_has_user_privileges": True,
            "web_login_timestamp": 1000,
        }.get(k, default))
        with mock.patch("flask.session", mock_session):
            with mock.patch("selfdroid.Settings.Settings.MINIMUM_WEB_LOGIN_TIMESTAMP", 0):
                with mock.patch("selfdroid.Settings.Settings.WEB_LOGIN_LIFETIME", 100):
                    with mock.patch("selfdroid.Helpers.Helpers.get_current_unix_timestamp", return_value=2000):
                        assert authenticator.has_at_least_user_privileges() is False

    def test_has_admin_privileges_true(self, authenticator):
        """Verify has_admin_privileges returns True when admin."""
        from selfdroid.Helpers import Helpers
        ts = Helpers.get_current_unix_timestamp()
        mock_session = mock.MagicMock()
        mock_session.get = mock.MagicMock(side_effect=lambda k, default=None: {
            "web_has_user_privileges": True,
            "web_has_admin_privileges": True,
            "web_login_timestamp": ts,
        }.get(k, default))
        with mock.patch("flask.session", mock_session):
            with mock.patch("selfdroid.Settings.Settings.MINIMUM_WEB_LOGIN_TIMESTAMP", 0):
                assert authenticator.has_admin_privileges() is True

    def test_has_admin_privileges_false(self, authenticator):
        """Verify has_admin_privileges returns False when not admin."""
        from selfdroid.Helpers import Helpers
        ts = Helpers.get_current_unix_timestamp()
        mock_session = mock.MagicMock()
        mock_session.get = mock.MagicMock(side_effect=lambda k, default=None: {
            "web_has_user_privileges": True,
            "web_has_admin_privileges": False,
            "web_login_timestamp": ts,
        }.get(k, default))
        with mock.patch("flask.session", mock_session):
            with mock.patch("selfdroid.Settings.Settings.MINIMUM_WEB_LOGIN_TIMESTAMP", 0):
                assert authenticator.has_admin_privileges() is False
