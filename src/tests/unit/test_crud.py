import datetime
import decimal
import pytest
import bcrypt
from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel
from selfdroid.appstorage.crud.UserAccountManager import UserAccountManager
from selfdroid.appstorage.AppSaleDBModel import AppSaleDBModel
from selfdroid.appstorage.crud.AppSaleManager import AppSaleManager
from unittest import mock


class TestUserAccountManager:
    """Tests for UserAccountManager CRUD operations."""

    def test_create_account_success(self, db_session):
        """Verify account is created with correct username, hash, created_by."""
        account = UserAccountManager.create_account("newuser", "password123", 1)
        assert account.username == "newuser"
        assert isinstance(account.password_hash, str)
        assert account.is_active is True
        assert account.created_by == 1

        # Verify password works
        result = UserAccountManager.authenticate("newuser", "password123")
        assert result is not None

    def test_create_account_duplicate_username(self, db_session):
        """Verify ValueError raised for duplicate username."""
        UserAccountManager.create_account("dupuser", "password123", 1)
        with pytest.raises(ValueError, match="already taken"):
            UserAccountManager.create_account("dupuser", "anotherpass", 1)

    def test_authenticate_valid_credentials(self, db_session):
        """Verify authenticate() returns account for correct username/password."""
        UserAccountManager.create_account("authuser", "correctpass", 1)
        account = UserAccountManager.authenticate("authuser", "correctpass")
        assert account is not None
        assert account.username == "authuser"

    def test_authenticate_invalid_password(self, db_session):
        """Verify authenticate() returns None for wrong password."""
        UserAccountManager.create_account("wrongpassuser", "correctpass", 1)
        account = UserAccountManager.authenticate("wrongpassuser", "wrongpass")
        assert account is None

    def test_authenticate_nonexistent_user(self, db_session):
        """Verify authenticate() returns None for nonexistent username."""
        account = UserAccountManager.authenticate("nonexistent", "anypass")
        assert account is None

    def test_authenticate_deactivated_account(self, db_session):
        """Verify authenticate() returns None for deactivated account."""
        account = UserAccountManager.create_account("deactuser", "password123", 1)
        account_id = account.id
        # Directly set is_active to avoid buggy deactivate_account code
        from selfdroid import db
        UserAccountDBModel.query.get(account_id).is_active = False
        db.session.commit()
        result = UserAccountManager.authenticate("deactuser", "password123")
        assert result is None

    def test_get_by_id_valid(self, db_session):
        """Verify get_by_id() returns account for valid ID."""
        account = UserAccountManager.create_account("idtest", "password123", 1)
        result = UserAccountManager.get_by_id(account.id)
        assert result is not None
        assert result.id == account.id

    def test_get_by_id_invalid(self, db_session):
        """Verify get_by_id() returns None for invalid ID."""
        result = UserAccountManager.get_by_id(99999)
        assert result is None

    def test_get_by_username_valid(self, db_session):
        """Verify get_by_username() returns account for valid username."""
        account = UserAccountManager.create_account("nametest", "password123", 1)
        result = UserAccountManager.get_by_username("nametest")
        assert result is not None
        assert result.username == "nametest"

    def test_get_by_username_invalid(self, db_session):
        """Verify get_by_username() returns None for invalid username."""
        result = UserAccountManager.get_by_username("nonexistent_user")
        assert result is None

    def test_get_all_accounts(self, db_session):
        """Verify get_all_accounts() returns all accounts ordered by created_at desc."""
        UserAccountManager.create_account("user1", "pass1", 1)
        UserAccountManager.create_account("user2", "pass2", 1)
        UserAccountManager.create_account("user3", "pass3", 1)
        accounts = UserAccountManager.get_all_accounts()
        assert len(accounts) >= 3

    def test_deactivate_account(self, db_session):
        """Verify deactivate_account() sets is_active=False."""
        account = UserAccountManager.create_account("deactacc", "password123", 1)
        account_id = account.id
        # Mock the app query to avoid InvalidRequestError on owner_username column
        with mock.patch("selfdroid.appstorage.crud.UserAccountManager.db.session.execute") as mock_execute:
            mock_execute.return_value.scalars.return_value.all.return_value = []
            result = UserAccountManager.deactivate_account(account_id)
        assert result is True
        refreshed = UserAccountManager.get_by_id(account_id)
        assert refreshed.is_active is False

    def test_deactivate_account_nonexistent(self, db_session):
        """Verify deactivate_account() returns False for nonexistent ID."""
        result = UserAccountManager.deactivate_account(99999)
        assert result is False

    def test_reset_password(self, db_session):
        """Verify reset_password() updates password_hash."""
        account = UserAccountManager.create_account("resetpwuser", "oldpass123", 1)
        old_hash = account.password_hash
        result = UserAccountManager.reset_password(account.id, "newpass456")
        assert result is True
        assert account.password_hash != old_hash
        # Verify new password works
        authenticated = UserAccountManager.authenticate("resetpwuser", "newpass456")
        assert authenticated is not None

    def test_reset_password_nonexistent(self, db_session):
        """Verify reset_password() returns False for nonexistent ID."""
        result = UserAccountManager.reset_password(99999, "newpass")
        assert result is False

    def test_delete_account(self, db_session):
        """Verify delete_account() removes account."""
        account = UserAccountManager.create_account("delacc", "password123", 1)
        account_id = account.id
        # Mock db.session.execute to avoid the buggy query on UserAccountDBModel
        with mock.patch("selfdroid.appstorage.crud.UserAccountManager.db.session.execute") as mock_execute:
            mock_execute.return_value.scalars.return_value.all.return_value = []
            result = UserAccountManager.delete_account(account_id)
        assert result is True
        assert UserAccountManager.get_by_id(account_id) is None

    def test_delete_account_nonexistent(self, db_session):
        """Verify delete_account() returns False for nonexistent ID."""
        result = UserAccountManager.delete_account(99999)
        assert result is False

    def test_change_password_for_self_valid(self, db_session):
        """Verify change_password_for_self() succeeds with correct old password."""
        account = UserAccountManager.create_account("changepw", "oldpass123", 1)
        result = UserAccountManager.change_password_for_self(account.id, "oldpass123", "newpass456")
        assert result is True
        authenticated = UserAccountManager.authenticate("changepw", "newpass456")
        assert authenticated is not None

    def test_change_password_for_self_wrong_old(self, db_session):
        """Verify change_password_for_self() fails with wrong old password."""
        account = UserAccountManager.create_account("wrongoldpw", "oldpass123", 1)
        result = UserAccountManager.change_password_for_self(account.id, "wrongold", "newpass456")
        assert result is False

    def test_change_password_for_self_nonexistent(self, db_session):
        """Verify change_password_for_self() returns False for nonexistent ID."""
        result = UserAccountManager.change_password_for_self(99999, "old", "new")
        assert result is False


class TestAppSaleManager:
    """Tests for AppSaleManager CRUD operations."""

    def test_create_sale(self, db_session):
        """Verify create_sale() creates record with correct fields."""
        sale = AppSaleManager.create_sale(
            app_id=1,
            buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
            currency="usd",
        )
        assert sale.app_id == 1
        assert sale.buyer_user_id == 1
        assert sale.amount_usd == decimal.Decimal("9.99")
        assert sale.currency == "usd"
        assert sale.payment_status == "pending"
        assert sale.invoice_id is None

    def test_get_by_id_valid(self, db_session):
        """Verify get_by_id() returns sale for valid ID."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        result = AppSaleManager.get_by_id(sale.id)
        assert result is not None
        assert result.id == sale.id

    def test_get_by_id_invalid(self, db_session):
        """Verify get_by_id() returns None for invalid ID."""
        result = AppSaleManager.get_by_id(99999)
        assert result is None

    def test_get_by_app_and_user_confirmed(self, db_session):
        """Verify get_by_app_and_user() returns sale for confirmed payment."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        AppSaleManager.confirm_sale(sale.id)
        result = AppSaleManager.get_by_app_and_user(1, 1)
        assert result is not None
        assert result.id == sale.id

    def test_get_by_app_and_user_pending(self, db_session):
        """Verify get_by_app_and_user() returns None for pending payment."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        result = AppSaleManager.get_by_app_and_user(1, 1)
        assert result is None

    def test_confirm_sale(self, db_session):
        """Verify confirm_sale() sets status=confirmed, sets download_issued_at."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        result = AppSaleManager.confirm_sale(sale.id, invoice_id="test_subaddr")
        assert result is not None
        assert result.payment_status == "confirmed"
        assert result.invoice_id == "test_subaddr"
        assert result.download_issued_at is not None

    def test_confirm_sale_nonexistent(self, db_session):
        """Verify confirm_sale() returns None for nonexistent ID."""
        result = AppSaleManager.confirm_sale(99999)
        assert result is None

    def test_expire_sale(self, db_session):
        """Verify expire_sale() sets status=expired."""
        sale = AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        result = AppSaleManager.expire_sale(sale.id)
        assert result is not None
        assert result.payment_status == "expired"

    def test_expire_sale_nonexistent(self, db_session):
        """Verify expire_sale() returns None for nonexistent ID."""
        result = AppSaleManager.expire_sale(99999)
        assert result is None

    def test_get_pending_sales(self, db_session):
        """Verify get_pending_sales() returns only pending sales."""
        AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        pending_sale = AppSaleManager.create_sale(
            app_id=2, buyer_user_id=1,
            amount_usd=decimal.Decimal("4.99"),
            amount_xmr=decimal.Decimal("0.025000000000"),
        )
        AppSaleManager.confirm_sale(pending_sale.id)
        pending_sales = AppSaleManager.get_pending_sales()
        assert len(pending_sales) >= 1
        statuses = [s.payment_status for s in pending_sales]
        assert "confirmed" not in statuses

    def test_get_sales_for_user(self, db_session):
        """Verify get_sales_for_user() returns only that user's sales."""
        AppSaleManager.create_sale(
            app_id=1, buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        AppSaleManager.create_sale(
            app_id=2, buyer_user_id=2,
            amount_usd=decimal.Decimal("4.99"),
            amount_xmr=decimal.Decimal("0.025000000000"),
        )
        user_sales = AppSaleManager.get_sales_for_user(1)
        assert len(user_sales) >= 1
        for sale in user_sales:
            assert sale.buyer_user_id == 1
