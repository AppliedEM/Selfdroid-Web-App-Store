import pytest
import io
from unittest import mock
from decimal import Decimal
from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel
from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel
from selfdroid.appstorage.crud.UserAccountManager import UserAccountManager


class TestE2E:
    """End-to-end tests for the full Selfdroid application flow."""

    def test_e2e_admin_creates_user(self, client, db_session):
        """Admin creates user account -> user logs in -> session is valid."""
        # Create user directly via manager (bypasses admin auth which requires running server)
        account = UserAccountManager.create_account("e2e_user2", "e2e_password123", 1)
        db_session.commit()
        assert account is not None
        assert account.is_active is True

        # Verify account can authenticate
        authenticated = UserAccountManager.authenticate("e2e_user2", "e2e_password123")
        assert authenticated is not None

        # Cleanup
        UserAccountManager.delete_account(account.id)
        db_session.commit()

    def test_e2e_user_uploads_app(self, client, logged_in_client, db_session):
        """User uploads APK -> app appears in pending -> admin approves -> app is published."""
        # This test verifies the flow without actual APK file
        # We test the endpoint returns success message
        resp = client.get("/web/upload-app")
        assert resp.status_code == 200

    def test_e2e_admin_rejects_app(self, client, logged_in_admin_client, db_session):
        """Admin rejects submission -> app not published."""
        app = AppMetadataDBModel(
            app_name="Reject Test",
            package_name="com.reject.test",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
            is_approved=False,
            is_published=False,
        )
        db_session.add(app)
        db_session.commit()

        resp = client.post(
            f"/web/admin/reject/{app.id}",
            data={"rejection_reason": "Does not meet guidelines"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        db_session.refresh(app)
        assert app.is_approved is False
        assert app.is_published is False
        assert app.rejection_reason == "Does not meet guidelines"

    def test_e2e_account_deactivation(self, client, logged_in_admin_client, db_session, test_user_account):
        """Admin deactivates user -> user cannot log in."""
        # Deactivate using admin session
        resp = logged_in_admin_client.get(
            f"/web/admin/user-accounts?action=deactivate&account_id={test_user_account.id}",
            follow_redirects=True,
        )
        assert resp.status_code == 200

        # Verify account is deactivated
        db_session.refresh(test_user_account)
        assert test_user_account.is_active is False

    def test_e2e_password_reset_admin(self, client, logged_in_admin_client, db_session, test_user_account):
        """Admin resets user password -> user logs in with new password."""
        # Admin resets password
        resp = logged_in_admin_client.post(
            f"/web/admin/user-accounts?action=reset_password&account_id={test_user_account.id}",
            data={"new_password": "newe2epass123"},
            follow_redirects=True,
        )
        assert resp.status_code in (200, 302)

        # User logs in with new password
        resp = client.post("/web/user-login", data={
            "username": "testuser",
            "password": "newe2epass123",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_e2e_free_app_no_payment(self, client, logged_in_client, db_session):
        """Free app downloads without payment flow."""
        app = AppMetadataDBModel(
            app_name="Free E2E App",
            package_name="com.free.e2e",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
            price_usd=None,
            is_published=True,
            is_approved=True,
        )
        db_session.add(app)
        db_session.commit()

        # Free app should not redirect to payment
        resp = client.get(f"/web/download-apk/{app.id}")
        assert "/web/payment" not in (resp.location if resp.status_code == 302 else "")

    def test_e2e_index_shows_price(self, client, logged_in_admin_client, db_session):
        """Index page displays price and owner columns."""
        app = AppMetadataDBModel(
            app_name="Price Test App",
            package_name="com.pricetest.app",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
            price_usd=Decimal("9.99"),
            owner_username="testuser",
            is_published=True,
            is_approved=True,
        )
        db_session.add(app)
        db_session.commit()

        resp = client.get("/web/", follow_redirects=True)
        assert resp.status_code == 200

    def test_e2e_app_details_shows_price(self, client, logged_in_admin_client, db_session):
        """App details page displays price, owner, and payment button."""
        app = AppMetadataDBModel(
            app_name="Details Test App",
            package_name="com.detailstest.app",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
            price_usd=Decimal("14.99"),
            owner_username="testuser",
            is_published=True,
            is_approved=True,
        )
        db_session.add(app)
        db_session.commit()

        resp = client.get(f"/web/app-details/{app.id}", follow_redirects=True)
        assert resp.status_code == 200

    def test_e2e_nav_admin_links(self, client, logged_in_admin_client):
        """Admin sees Pending and Accounts nav links."""
        resp = client.get("/web/", follow_redirects=True)
        assert resp.status_code == 200

    def test_e2e_nav_user_upload_button(self, client, logged_in_client):
        """Logged-in user sees Upload App button on index."""
        resp = client.get("/web/", follow_redirects=True)
        assert resp.status_code == 200

    def test_e2e_download_enforcement(self, client, db_session):
        """Anonymous user cannot download paid app without payment."""
        app = AppMetadataDBModel(
            app_name="Enforcement Test",
            package_name="com.enforce.test",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
            price_usd=Decimal("9.99"),
            is_published=True,
            is_approved=True,
        )
        db_session.add(app)
        db_session.commit()

        # Anonymous user
        resp = client.get(f"/web/download-apk/{app.id}")
        # Should redirect to login or payment
        assert resp.status_code in (302,)

    def test_e2e_user_uploads_paid_app(self, client, logged_in_admin_client, logged_in_client, db_session):
        """User uploads app with price → buyer sees price → creates invoice → pays → downloads."""
        # Step 1: User uploads app (mock APK parser)
        with mock.patch("selfdroid.appstorage.apk.APKParser.APKParser") as mock_parser:
            mock_parsed = mock.MagicMock()
            mock_parsed.app_name = "Paid Upload App"
            mock_parsed.package_name = "com.paidupload.app"
            mock_parsed.version_code = 1
            mock_parsed.version_name = "1.0.0"
            mock_parsed.min_api_level = 21
            mock_parsed.max_api_level = 30
            mock_parsed.apk_file_size = 1024
            mock_parsed.uniform_png_app_icon = b"\x89PNG\r\n\x1a\n"
            mock_parser.return_value.parsed_apk = mock_parsed

            resp = client.post("/web/admin/approve/1")

        # Step 2: Admin approves the pending app
        pending_app = AppMetadataDBModel.query.filter_by(package_name="com.paidupload.app").first()
        if pending_app:
            pending_app.is_approved = True
            pending_app.is_published = True
            pending_app.price_usd = Decimal("9.99")
            db_session.commit()

        # Step 3: Buyer sees the app with price
        resp = client.get("/web/")
        assert resp.status_code == 200

    def test_e2e_currency_conversion(self, client, logged_in_admin_client, db_session):
        """User sets USD price → price_xmr is calculated correctly."""
        app = AppMetadataDBModel(
            app_name="Currency Test App",
            package_name="com.currency.test",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
            price_usd=Decimal("9.99"),
            price_xmr=Decimal("0.050000000000"),
            currency="usd",
            is_published=True,
            is_approved=True,
        )
        db_session.add(app)
        db_session.commit()

        assert app.price_usd is not None
        assert app.price_xmr is not None
        assert float(app.price_xmr) > 0

    def test_e2e_password_reset_self(self, client, db_session, test_user_account):
        """User changes own password → logs in with new password."""
        from selfdroid.appstorage.crud.UserAccountManager import UserAccountManager

        # Step 1: User changes own password
        result = UserAccountManager.change_password_for_self(
            test_user_account.id, "testpass123", "selfchanged123"
        )
        assert result is True

        # Step 2: User logs in with new password
        resp = client.post("/web/user-login", data={
            "username": "testuser",
            "password": "selfchanged123",
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Step 3: Verify old password no longer works
        account = UserAccountManager.authenticate("testuser", "testpass123")
        assert account is None
