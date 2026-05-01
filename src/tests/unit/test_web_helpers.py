import pytest
from unittest import mock
from selfdroid.web.WebHelpers import WebHelpers


class TestWebHelpers:
    """Tests for WebHelpers.generate_web_template_context."""

    def _make_mock_session(self, data):
        """Create a mock flask.session object."""
        mock_sess = mock.MagicMock()
        mock_sess.get = mock.MagicMock(side_effect=lambda k, default=None: data.get(k, default))
        return mock_sess

    def test_context_includes_user_account_id(self):
        """Verify template context includes user_account_id when logged in."""
        from selfdroid.Helpers import Helpers
        ts = Helpers.get_current_unix_timestamp()
        mock_sess = self._make_mock_session({
            "web_has_user_privileges": True,
            "web_login_timestamp": ts,
            "user_account_id": 42,
        })
        with mock.patch("flask.session", mock_sess):
            with mock.patch("selfdroid.Settings.Settings.MINIMUM_WEB_LOGIN_TIMESTAMP", 0):
                with mock.patch("selfdroid.Settings.Settings.WEB_LOGIN_LIFETIME", 999999):
                    ctx = WebHelpers.generate_web_template_context()
                    assert ctx["user_account_id"] == 42

    def test_context_includes_user_account_username(self):
        """Verify template context includes user_account_username when logged in."""
        from selfdroid.Helpers import Helpers
        ts = Helpers.get_current_unix_timestamp()
        mock_sess = self._make_mock_session({
            "web_has_user_privileges": True,
            "web_login_timestamp": ts,
            "user_account_id": 42,
            "user_account_username": "testuser",
        })
        with mock.patch("flask.session", mock_sess):
            with mock.patch("selfdroid.Settings.Settings.MINIMUM_WEB_LOGIN_TIMESTAMP", 0):
                with mock.patch("selfdroid.Settings.Settings.WEB_LOGIN_LIFETIME", 999999):
                    ctx = WebHelpers.generate_web_template_context()
                    assert ctx["user_account_username"] == "testuser"

    def test_context_excludes_user_account_when_anonymous(self):
        """Verify user_account_id is None when not logged in."""
        mock_sess = self._make_mock_session({})
        with mock.patch("flask.session", mock_sess):
            ctx = WebHelpers.generate_web_template_context()
            assert "user_account_id" not in ctx
            assert "user_account_username" not in ctx
            assert "logout_form" not in ctx

    def test_context_includes_has_privileges(self):
        """Verify context includes privilege flags."""
        mock_sess = self._make_mock_session({})
        with mock.patch("flask.session", mock_sess):
            ctx = WebHelpers.generate_web_template_context()
            assert "has_at_least_user_privileges" in ctx
            assert "has_admin_privileges" in ctx
            assert ctx["has_at_least_user_privileges"] is False
            assert ctx["has_admin_privileges"] is False

    def test_context_includes_constants_and_settings(self):
        """Verify context includes Constants and Settings."""
        mock_sess = self._make_mock_session({})
        with mock.patch("flask.session", mock_sess):
            ctx = WebHelpers.generate_web_template_context()
            assert "Constants" in ctx
            assert "Settings" in ctx
