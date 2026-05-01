import datetime
import decimal
import pytest
from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel
from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel
from selfdroid.appstorage.AppSaleDBModel import AppSaleDBModel
from selfdroid.payments.invoice import PaymentInvoice


class TestUserAccountDBModel:
    """Tests for UserAccountDBModel columns, defaults, and constraints."""

    def test_create_user_account_columns(self, db_session):
        """Verify all columns exist with correct types, nullable, defaults."""
        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("utf-8")
        account = UserAccountDBModel(
            username="testuser",
            password_hash=password_hash,
            created_by=1,
        )
        db_session.add(account)
        db_session.commit()

        assert account.id is not None
        assert account.username == "testuser"
        assert isinstance(account.password_hash, str)
        assert account.is_active is True
        assert isinstance(account.created_at, datetime.datetime)
        assert account.created_by == 1

    def test_username_unique_constraint(self, db_session):
        """Verify duplicate username raises integrity error."""
        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("utf-8")
        account1 = UserAccountDBModel(username="duptest", password_hash=password_hash, created_by=1)
        account2 = UserAccountDBModel(username="duptest", password_hash=password_hash, created_by=1)
        db_session.add(account1)
        db_session.commit()

        db_session.add(account2)
        with pytest.raises(Exception):
            try:
                db_session.commit()
            except Exception:
                db_session.rollback()
                raise

    def test_password_hash_storage(self, db_session):
        """Verify password_hash is stored as string (bcrypt)."""
        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("utf-8")
        account = UserAccountDBModel(username="hashtest", password_hash=password_hash, created_by=1)
        db_session.add(account)
        db_session.commit()

        assert isinstance(account.password_hash, str)
        assert len(account.password_hash) > 0
        assert "$2b$" in account.password_hash or "$2a$" in account.password_hash

    def test_is_active_default(self, db_session):
        """Verify is_active defaults to True."""
        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("utf-8")
        account = UserAccountDBModel(username="defaulttest", password_hash=password_hash, created_by=1)
        db_session.add(account)
        db_session.commit()

        assert account.is_active is True

    def test_created_at_default(self, db_session):
        """Verify created_at defaults to NOW."""
        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("utf-8")
        before = datetime.datetime.utcnow()
        account = UserAccountDBModel(username="timetest", password_hash=password_hash, created_by=1)
        db_session.add(account)
        db_session.commit()
        after = datetime.datetime.utcnow()

        assert before <= account.created_at <= after

    def test_created_by_fk(self, db_session):
        """Verify created_by references user_account.id."""
        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("utf-8")
        account = UserAccountDBModel(username="fktest", password_hash=password_hash, created_by=42)
        db_session.add(account)
        db_session.commit()

        assert account.created_by == 42
        assert account.created_by is not None


class TestAppSaleDBModel:
    """Tests for AppSaleDBModel columns, defaults, and methods."""

    def test_create_app_sale_columns(self, db_session):
        """Verify all columns exist with correct types, nullable, defaults."""
        sale = AppSaleDBModel(
            app_id=1,
            buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
            currency="usd",
        )
        db_session.add(sale)
        db_session.commit()

        assert sale.id is not None
        assert sale.app_id == 1
        assert sale.buyer_user_id == 1
        assert sale.amount_usd == decimal.Decimal("9.99")
        assert sale.amount_xmr == decimal.Decimal("0.050000000000")
        assert sale.currency == "usd"
        assert sale.payment_status == "pending"
        assert sale.invoice_id is None
        assert sale.download_issued_at is None
        assert isinstance(sale.created_at, datetime.datetime)

    def test_payment_status_default(self, db_session):
        """Verify payment_status defaults to 'pending'."""
        sale = AppSaleDBModel(
            app_id=1,
            buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        db_session.add(sale)
        db_session.commit()

        assert sale.payment_status == "pending"

    def test_currency_default(self, db_session):
        """Verify currency defaults to 'usd'."""
        sale = AppSaleDBModel(
            app_id=1,
            buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        db_session.add(sale)
        db_session.commit()

        assert sale.currency == "usd"

    def test_is_expired_pending(self, db_session):
        """Verify is_expired() returns False for pending sales."""
        sale = AppSaleDBModel(
            app_id=1,
            buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        db_session.add(sale)
        db_session.commit()

        assert sale.is_expired() is False

    def test_is_expired_after_download_issued(self, db_session):
        """Verify is_expired() returns True after 24h from download_issued_at."""
        old_time = datetime.datetime.utcnow() - datetime.timedelta(hours=25)
        sale = AppSaleDBModel(
            app_id=1,
            buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
            download_issued_at=old_time,
        )
        db_session.add(sale)
        db_session.commit()

        assert sale.is_expired() is True

    def test_to_dict_output(self, db_session):
        """Verify to_dict() returns correct keys and values."""
        sale = AppSaleDBModel(
            app_id=1,
            buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
            currency="usd",
            payment_status="pending",
            invoice_id="test_subaddress",
        )
        db_session.add(sale)
        db_session.commit()

        d = sale.to_dict()
        assert d["id"] == sale.id
        assert d["app_id"] == 1
        assert d["buyer_user_id"] == 1
        assert d["amount_usd"] == "9.99"
        assert d["currency"] == "usd"
        assert d["payment_status"] == "pending"
        assert d["invoice_id"] == "test_subaddress"
        assert d["download_issued_at"] is None
        assert isinstance(d["created_at"], str)
        assert d["is_expired"] is False

    def test_app_id_fk(self, db_session):
        """Verify app_id references app_metadata.id."""
        sale = AppSaleDBModel(
            app_id=42,
            buyer_user_id=1,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        db_session.add(sale)
        db_session.commit()

        assert sale.app_id == 42

    def test_buyer_user_id_fk(self, db_session):
        """Verify buyer_user_id references user_account.id."""
        sale = AppSaleDBModel(
            app_id=1,
            buyer_user_id=99,
            amount_usd=decimal.Decimal("9.99"),
            amount_xmr=decimal.Decimal("0.050000000000"),
        )
        db_session.add(sale)
        db_session.commit()

        assert sale.buyer_user_id == 99


class TestAppMetadataDBModel:
    """Tests for AppMetadataDBModel new columns from user upload buildout."""

    def test_new_columns_exist(self, db_session):
        """Verify all 10 new columns exist on app_metadata table."""
        from decimal import Decimal
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.app",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
            uploaded_by=1,
            owner_username="testuser",
            price_usd=Decimal("9.99"),
            price_xmr=Decimal("0.050000000000"),
            currency="usd",
            is_published=False,
            is_approved=False,
        )
        db_session.add(app)
        db_session.commit()

        assert app.uploaded_by == 1
        assert app.owner_username == "testuser"
        assert app.price_usd is not None
        assert app.price_xmr is not None
        assert app.currency == "usd"
        assert app.is_published is False
        assert app.is_approved is False
        assert app.approved_by is None
        assert app.approved_at is None
        assert app.rejection_reason is None

    def test_uploaded_by_nullable(self, db_session):
        """Verify uploaded_by defaults to NULL."""
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.noupload",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
        )
        db_session.add(app)
        db_session.commit()

        assert app.uploaded_by is None

    def test_owner_username_nullable(self, db_session):
        """Verify owner_username defaults to NULL."""
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.nouser",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
        )
        db_session.add(app)
        db_session.commit()

        assert app.owner_username is None

    def test_price_usd_nullable(self, db_session):
        """Verify price_usd defaults to NULL."""
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.noprice",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
        )
        db_session.add(app)
        db_session.commit()

        assert app.price_usd is None

    def test_price_xmr_nullable(self, db_session):
        """Verify price_xmr defaults to NULL."""
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.nonoxmr",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
        )
        db_session.add(app)
        db_session.commit()

        assert app.price_xmr is None

    def test_currency_default_usd(self, db_session):
        """Verify currency defaults to 'usd'."""
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.cur",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
        )
        db_session.add(app)
        db_session.commit()

        assert app.currency == "usd"

    def test_is_published_default_false(self, db_session):
        """Verify is_published defaults to False."""
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.pub",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
        )
        db_session.add(app)
        db_session.commit()

        assert app.is_published is False

    def test_is_approved_default_false(self, db_session):
        """Verify is_approved defaults to False."""
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.approved",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
        )
        db_session.add(app)
        db_session.commit()

        assert app.is_approved is False

    def test_approved_by_nullable(self, db_session):
        """Verify approved_by defaults to NULL."""
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.appby",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
        )
        db_session.add(app)
        db_session.commit()

        assert app.approved_by is None

    def test_approved_at_nullable(self, db_session):
        """Verify approved_at defaults to NULL."""
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.appat",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
        )
        db_session.add(app)
        db_session.commit()

        assert app.approved_at is None

    def test_rejection_reason_nullable(self, db_session):
        """Verify rejection_reason defaults to NULL."""
        app = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.reject",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=1024,
        )
        db_session.add(app)
        db_session.commit()

        assert app.rejection_reason is None
