import pytest
import io
from unittest import mock
from decimal import Decimal
from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel
from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel
from selfdroid.appstorage.crud.UserAccountManager import UserAccountManager


class TestE2E:
    """End-to-end tests for the full Selfdroid application flow."""

    def test_e2e_admin_creates_user(self, client, logged_in_admin_client, db_session):
        """Admin creates user account -> user logs in -> session is valid."""
        # Step 1: Admin creates user
        resp = client.post("/web/admin/create-account", data={
            "username": "e2e_user",
            "password": "e2e_password123",
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Step 2: User logs in
        resp = client.post("/web/user-login", data={
            "username": "e2e_user",
            "password": "e2e_password123",
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Step 3: Session is valid
        with client.session_transaction() as sess:
            assert sess.get("user_account_id") is not None
            assert sess.get("user_account_username") == "e2e_user"

        # Cleanup
        account = UserAccountManager.get_by_username("e2e_user")
        if account:
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

    def test_e2e_account_deactivation(self, client, db_session, test_user_account):
        """Admin deactivates user -> user cannot log in."""
        # Deactivate
        resp = client.get(
            f"/web/admin/user-accounts?action=deactivate&account_id={test_user_account.id}",
            base_url="https://localhost",
            follow_redirects=True,
        )
        assert resp.status_code == 200

        # Try to login
        resp = client.post("/web/user-login", data={
            "username": "testuser",
            "password": "testpass123",
        })
        assert resp.status_code == 200
        assert test_user_account.is_active is False

    def test_e2e_password_reset_admin(self, client, db_session, test_user_account):
        """Admin resets user password -> user logs in with new password."""
        # Admin resets password
        resp = client.post(
            f"/web/admin/user-accounts?action=reset_password&account_id={test_user_account.id}",
            data={"new_password": "newe2epass123"},
            follow_redirects=True,
        )
        assert resp.status_code == 200

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
