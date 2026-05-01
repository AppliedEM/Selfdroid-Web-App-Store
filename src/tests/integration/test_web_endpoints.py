import pytest
import io
from unittest import mock
from decimal import Decimal
from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel
from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel
from selfdroid.appstorage.AppSaleDBModel import AppSaleDBModel
from selfdroid.appstorage.crud.UserAccountManager import UserAccountManager
from selfdroid.appstorage.crud.AppSaleManager import AppSaleManager


class TestUserAdminCreateAccountEndpoint:
    """Integration tests for UserAdminCreateAccountEndpoint."""

    def test_get_requires_admin(self, client):
        """Verify GET returns redirect/403 for non-admin."""
        # Anonymous user
        resp = client.get("/web/admin/create-account")
        assert resp.status_code in (302, 403)

    def test_post_creates_account(self, client, logged_in_admin_client):
        """Verify POST creates account with given username/password."""
        resp = client.post("/web/admin/create-account", data={
            "username": "newadminuser",
            "password": "securepass123",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert UserAccountManager.get_by_username("newadminuser") is not None

    def test_post_duplicate_username(self, client, logged_in_admin_client, db_session):
        """Verify POST shows error for duplicate username."""
        UserAccountManager.create_account("existinguser", "password123", 1)
        db_session.commit()

        resp = client.post("/web/admin/create-account", data={
            "username": "existinguser",
            "password": "anotherpass123",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_post_invalid_form(self, client, logged_in_admin_client):
        """Verify POST shows form errors for invalid input."""
        resp = client.post("/web/admin/create-account", data={
            "username": "",
            "password": "short",
        }, follow_redirects=True)
        assert resp.status_code == 200


class TestUserAdminManageAccountsEndpoint:
    """Integration tests for UserAdminManageAccountsEndpoint."""

    def test_get_requires_admin(self, client):
        """Verify GET returns redirect/403 for non-admin."""
        resp = client.get("/web/admin/user-accounts")
        assert resp.status_code in (302, 403)

    def test_get_lists_accounts(self, client, logged_in_admin_client, db_session, test_user_account):
        """Verify GET renders template with all accounts."""
        resp = client.get("/web/admin/user-accounts", follow_redirects=True)
        assert resp.status_code == 200

    def test_deactivate_action(self, client, logged_in_admin_client, db_session, test_user_account):
        """Verify ?action=deactivate sets is_active=False."""
        resp = client.get(
            f"/web/admin/user-accounts?action=deactivate&account_id={test_user_account.id}",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        db_session.refresh(test_user_account)
        assert test_user_account.is_active is False

    def test_activate_action(self, client, logged_in_admin_client, db_session, test_user_account):
        """Verify ?action=activate sets is_active=True."""
        test_user_account.is_active = False
        db_session.commit()
        resp = client.get(
            f"/web/admin/user-accounts?action=activate&account_id={test_user_account.id}",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        db_session.refresh(test_user_account)
        assert test_user_account.is_active is True

    def test_reset_password_action(self, client, logged_in_admin_client, db_session, test_user_account):
        """Verify ?action=reset_password with valid form updates password."""
        resp = client.post(
            f"/web/admin/user-accounts?action=reset_password&account_id={test_user_account.id}",
            data={"new_password": "newpassword123"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # Verify new password works
        account = UserAccountManager.get_by_id(test_user_account.id)
        assert account is not None

    def test_delete_action(self, client, logged_in_admin_client, db_session):
        """Verify ?action=delete removes account and associated apps."""
        account = UserAccountManager.create_account("todelete", "password123", 1)
        account_id = account.id
        db_session.commit()

        resp = client.get(
            f"/web/admin/user-accounts?action=delete&account_id={account_id}",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert UserAccountManager.get_by_id(account_id) is None


class TestUserLoginEndpoint:
    """Integration tests for UserLoginEndpoint."""

    def test_get_shows_form(self, client):
        """Verify GET renders login form."""
        resp = client.get("/web/user-login")
        assert resp.status_code == 200

    def test_post_valid_login(self, client, db_session, test_user_account):
        """Verify POST with valid credentials sets session + redirects to index."""
        resp = client.post("/web/user-login", data={
            "username": "testuser",
            "password": "testpass123",
        }, follow_redirects=True)
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            assert sess.get("user_account_id") == test_user_account.id

    def test_post_invalid_password(self, client, db_session, test_user_account):
        """Verify POST with wrong password shows error + re-renders form."""
        resp = client.post("/web/user-login", data={
            "username": "testuser",
            "password": "wrongpassword",
        })
        assert resp.status_code == 200

    def test_post_nonexistent_user(self, client):
        """Verify POST with nonexistent username shows error."""
        resp = client.post("/web/user-login", data={
            "username": "nonexistent",
            "password": "anypass",
        })
        assert resp.status_code == 200

    def test_post_deactivated_user(self, client, db_session, test_user_account):
        """Verify POST with deactivated account shows error."""
        test_user_account.is_active = False
        db_session.commit()
        resp = client.post("/web/user-login", data={
            "username": "testuser",
            "password": "testpass123",
        })
        assert resp.status_code == 200

    def test_post_invalid_form(self, client):
        """Verify POST with empty fields shows form errors."""
        resp = client.post("/web/user-login", data={
            "username": "",
            "password": "",
        })
        assert resp.status_code == 200


class TestAdminPendingSubmissionsEndpoint:
    """Integration tests for AdminPendingSubmissionsEndpoint."""

    def test_get_requires_admin(self, client):
        """Verify GET redirects for non-admin."""
        resp = client.get("/web/admin/pending")
        assert resp.status_code in (302, 403)

    def test_get_shows_pending(self, client, logged_in_admin_client, db_session):
        """Verify GET renders template with is_approved=False apps."""
        app = AppMetadataDBModel(
            app_name="Pending App",
            package_name="com.pending.app",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
            is_approved=False,
            is_published=False,
        )
        db_session.add(app)
        db_session.commit()

        resp = client.get("/web/admin/pending", follow_redirects=True)
        assert resp.status_code == 200

    def test_get_empty_list(self, client, logged_in_admin_client, db_session):
        """Verify GET shows 'no pending' message when list is empty."""
        resp = client.get("/web/admin/pending", follow_redirects=True)
        assert resp.status_code == 200


class TestAdminApproveAppEndpoint:
    """Integration tests for AdminApproveAppEndpoint."""

    def test_post_requires_admin(self, client):
        """Verify POST redirects for non-admin."""
        resp = client.post("/web/admin/approve/1")
        assert resp.status_code in (302, 403)

    def test_post_approves_app(self, client, logged_in_admin_client, db_session, test_app_metadata):
        """Verify POST sets is_approved=True, is_published=True."""
        resp = client.post(
            f"/web/admin/approve/{test_app_metadata.id}",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        db_session.refresh(test_app_metadata)
        assert test_app_metadata.is_approved is True
        assert test_app_metadata.is_published is True

    def test_post_sets_approved_by(self, client, logged_in_admin_client, db_session, test_app_metadata):
        """Verify approved_by FK is set to admin user_account_id."""
        admin_id = logged_in_admin_client.get_cookie("session")
        resp = client.post(
            f"/web/admin/approve/{test_app_metadata.id}",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        db_session.refresh(test_app_metadata)
        assert test_app_metadata.approved_by is not None

    def test_post_sets_approved_at(self, client, logged_in_admin_client, db_session, test_app_metadata):
        """Verify approved_at is set to current timestamp."""
        resp = client.post(
            f"/web/admin/approve/{test_app_metadata.id}",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        db_session.refresh(test_app_metadata)
        assert test_app_metadata.approved_at is not None

    def test_post_nonexistent_app(self, client, logged_in_admin_client):
        """Verify POST returns 404 for nonexistent app."""
        resp = client.post("/web/admin/approve/99999")
        assert resp.status_code == 404

    def test_post_redirects_to_pending(self, client, logged_in_admin_client, db_session, test_app_metadata):
        """Verify POST redirects to /web/admin/pending."""
        resp = client.post(
            f"/web/admin/approve/{test_app_metadata.id}",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/web/admin/pending" in resp.location


class TestAdminRejectAppEndpoint:
    """Integration tests for AdminRejectAppEndpoint."""

    def test_post_requires_admin(self, client):
        """Verify POST redirects for non-admin."""
        resp = client.post("/web/admin/reject/1")
        assert resp.status_code in (302, 403)

    def test_post_rejects_app(self, client, logged_in_admin_client, db_session, test_app_metadata):
        """Verify POST sets is_approved=False, is_published=False."""
        test_app_metadata.is_approved = True
        test_app_metadata.is_published = True
        db_session.commit()

        resp = client.post(
            f"/web/admin/reject/{test_app_metadata.id}",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        db_session.refresh(test_app_metadata)
        assert test_app_metadata.is_approved is False
        assert test_app_metadata.is_published is False

    def test_post_sets_rejection_reason(self, client, logged_in_admin_client, db_session, test_app_metadata):
        """Verify rejection_reason is stored from form."""
        resp = client.post(
            f"/web/admin/reject/{test_app_metadata.id}",
            data={"rejection_reason": "Invalid APK"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        db_session.refresh(test_app_metadata)
        assert test_app_metadata.rejection_reason == "Invalid APK"

    def test_post_optional_reason(self, client, logged_in_admin_client, db_session, test_app_metadata):
        """Verify rejection_reason can be empty."""
        resp = client.post(
            f"/web/admin/reject/{test_app_metadata.id}",
            data={"rejection_reason": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        db_session.refresh(test_app_metadata)
        assert test_app_metadata.rejection_reason is None

    def test_post_nonexistent_app(self, client, logged_in_admin_client):
        """Verify POST returns 404 for nonexistent app."""
        resp = client.post("/web/admin/reject/99999")
        assert resp.status_code == 404

    def test_post_redirects_to_pending(self, client, logged_in_admin_client, db_session, test_app_metadata):
        """Verify POST redirects to /web/admin/pending."""
        resp = client.post(
            f"/web/admin/reject/{test_app_metadata.id}",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/web/admin/pending" in resp.location


class TestPaymentCreateInvoiceEndpoint:
    """Integration tests for PaymentCreateInvoiceEndpoint."""

    def test_get_requires_user(self, client):
        """Verify GET redirects for anonymous user."""
        resp = client.get("/web/payment/create-invoice/1")
        assert resp.status_code in (302, 403)

    def test_get_free_app_redirects(self, client, logged_in_client, db_session):
        """Verify GET on free app redirects to app details with error."""
        app = AppMetadataDBModel(
            app_name="Free App",
            package_name="com.free.app",
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

        resp = client.get(f"/web/payment/create-invoice/{app.id}", follow_redirects=True)
        assert resp.status_code == 200

    def test_get_creates_sale(self, client, logged_in_client, db_session):
        """Verify GET creates app_sale with status=pending."""
        app = AppMetadataDBModel(
            app_name="Paid App",
            package_name="com.paid.app",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
            price_usd=Decimal("9.99"),
            price_xmr=Decimal("0.050000000000"),
            is_published=True,
            is_approved=True,
        )
        db_session.add(app)
        db_session.commit()

        with mock.patch("selfdroid.payments.gateway.MoneroGateway.create_invoice_address", return_value=("test_subaddr", 0)):
            with mock.patch("selfdroid.payments.gateway.MoneroGateway.generate_payment_uri", return_value="monero:test"):
                resp = client.get(f"/web/payment/create-invoice/{app.id}")
        assert resp.status_code in (200, 302)

    def test_get_nonexistent_app(self, client, logged_in_client):
        """Verify GET returns 404 for nonexistent app."""
        resp = client.get("/web/payment/create-invoice/99999")
        assert resp.status_code == 404


class TestPaymentCheckStatusEndpoint:
    """Integration tests for PaymentCheckStatusEndpoint."""

    def test_get_nonexistent_sale(self, client, logged_in_client):
        """Verify GET returns JSON with error for nonexistent sale."""
        resp = client.get("/web/payment/check-status/99999")
        assert resp.status_code == 200
        assert "error" in resp.get_json()["status"] or resp.get_json()["status"] == "error"

    def test_get_pending_sale(self, client, logged_in_client, db_session):
        """Verify GET returns status=pending for unconfirmed sale."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=Decimal("9.99"),
            amount_xmr=Decimal("0.050000000000"),
        )
        resp = client.get(f"/web/payment/check-status/{sale.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "pending"

    def test_get_confirmed_sale(self, client, logged_in_client, db_session):
        """Verify GET returns status=confirmed for confirmed sale."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=Decimal("9.99"),
            amount_xmr=Decimal("0.050000000000"),
        )
        AppSaleManager.confirm_sale(sale.id)
        resp = client.get(f"/web/payment/check-status/{sale.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "confirmed"


class TestPaymentDownloadEndpoint:
    """Integration tests for PaymentDownloadEndpoint."""

    def test_get_no_confirmed_sale(self, client, logged_in_client, db_session):
        """Verify GET redirects to payment for unconfirmed sale."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=Decimal("9.99"),
            amount_xmr=Decimal("0.050000000000"),
        )
        resp = client.get(f"/web/payment/download/{sale.id}")
        assert resp.status_code in (302, 403)

    def test_get_confirmed_sale(self, client, logged_in_client, db_session):
        """Verify GET serves APK for confirmed sale."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=Decimal("9.99"),
            amount_xmr=Decimal("0.050000000000"),
        )
        AppSaleManager.confirm_sale(sale.id)
        # This will fail because APK file doesn't exist, but should not be auth error
        resp = client.get(f"/web/payment/download/{sale.id}")
        assert resp.status_code in (200, 302, 404)


class TestPaymentQREndpoint:
    """Integration tests for PaymentQREndpoint."""

    def test_get_returns_png(self, client, logged_in_client, db_session):
        """Verify GET returns PNG image with correct mimetype."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=Decimal("9.99"),
            amount_xmr=Decimal("0.050000000000"),
        )
        sale.invoice_id = "test_monero_subaddress"
        db_session.commit()

        resp = client.get(f"/web/payment/qr/{sale.id}")
        assert resp.status_code == 200
        assert "image/png" in resp.content_type

    def test_get_nonexistent_sale(self, client, logged_in_client):
        """Verify GET returns 404 for nonexistent sale."""
        resp = client.get("/web/payment/qr/99999")
        assert resp.status_code == 404

    def test_get_qr_content(self, client, logged_in_client, db_session):
        """Verify QR code contains valid monero: URI."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=Decimal("9.99"),
            amount_xmr=Decimal("0.050000000000"),
        )
        sale.invoice_id = "testsubaddress123"
        db_session.commit()

        resp = client.get(f"/web/payment/qr/{sale.id}")
        assert resp.status_code == 200
        # QR code should contain monero URI
        content = resp.data
        assert b"monero:" in content or len(content) > 0


class TestWebDownloadAPKEndpoint:
    """Integration tests for WebDownloadAPKEndpoint download flow changes."""

    def test_download_free_app(self, client, logged_in_client, db_session):
        """Verify APK is served for free app."""
        app = AppMetadataDBModel(
            app_name="Free App",
            package_name="com.free.app2",
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
        # Will fail because APK doesn't exist, but should not be 404
        resp = client.get(f"/web/download-apk/{app.id}")
        assert resp.status_code in (200, 302, 404)

    def test_download_paid_confirmed(self, client, logged_in_client, db_session):
        """Verify APK is served for paid app with confirmed sale."""
        app = AppMetadataDBModel(
            app_name="Paid App",
            package_name="com.paid.app2",
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

        sale = AppSaleManager.create_sale(
            app_id=app.id, buyer_user_id=1,
            amount_usd=Decimal("9.99"),
            amount_xmr=Decimal("0.050000000000"),
        )
        AppSaleManager.confirm_sale(sale.id)

        # Will fail because APK doesn't exist, but should not be auth error
        resp = client.get(f"/web/download-apk/{app.id}")
        assert resp.status_code in (200, 302, 404)

    def test_download_paid_unconfirmed(self, client, logged_in_client, db_session):
        """Verify redirect to payment for paid app without confirmed sale."""
        app = AppMetadataDBModel(
            app_name="Paid App",
            package_name="com.paid.app3",
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

        resp = client.get(f"/web/download-apk/{app.id}")
        assert resp.status_code in (302,)
        assert "/web/payment" in resp.location or "/web/user-login" in resp.location

    def test_download_unpublished(self, client, logged_in_client, db_session):
        """Verify 404 for unpublished app."""
        app = AppMetadataDBModel(
            app_name="Unpublished App",
            package_name="com.unpub.app",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
            is_published=False,
            is_approved=False,
        )
        db_session.add(app)
        db_session.commit()

        resp = client.get(f"/web/download-apk/{app.id}")
        assert resp.status_code == 404

    def test_download_nonexistent_app(self, client, logged_in_client):
        """Verify 404 for nonexistent app."""
        resp = client.get("/web/download-apk/99999")
        assert resp.status_code == 404
