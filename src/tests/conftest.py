import os
import sys
import pytest
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Ensure app_data directory exists for SQLite DB
app_data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "app_data")
os.makedirs(app_data_dir, exist_ok=True)

# Set env vars to avoid bcrypt hashing in default admin password during tests
os.environ.setdefault("SELFDROID_USER_PASSWORD_HASH", "")

import flask
from selfdroid import db
from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel
from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel
from selfdroid.appstorage.AppSaleDBModel import AppSaleDBModel
from selfdroid.payments.invoice import PaymentInvoice


@pytest.fixture(scope="session")
def app_config():
    """Session-scoped Flask app config for unit tests that don't need the full app."""
    return {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + os.path.join(app_data_dir, "test_database.sqlite"),
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-for-unit-tests-only",
        "WTF_CSRF_ENABLED": False,
        "SESSION_COOKIE_SECURE": False,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
    }


@pytest.fixture(scope="session")
def app(app_config):
    """Session-scoped Flask app for all tests."""
    import selfdroid
    # Override the app config
    selfdroid.app.config.update(app_config)
    selfdroid.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app_data_dir, "test_database.sqlite")

    with selfdroid.app.app_context():
        db.create_all()
        db.session.commit()
        yield selfdroid.app

    with selfdroid.app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI runner."""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def db_session(app):
    """Function-scoped database session with clean state."""
    with app.app_context():
        # Clear all data (handle missing PaymentInvoice table gracefully)
        try:
            db.session.query(PaymentInvoice).delete()
        except Exception:
            pass
        db.session.query(AppSaleDBModel).delete()
        db.session.query(AppMetadataDBModel).delete()
        db.session.query(UserAccountDBModel).delete()
        db.session.commit()
        db.session.flush()
        yield db.session
        # Cleanup after test
        try:
            db.session.query(PaymentInvoice).delete()
        except Exception:
            pass
        db.session.query(AppSaleDBModel).delete()
        db.session.query(AppMetadataDBModel).delete()
        db.session.query(UserAccountDBModel).delete()
        db.session.commit()


@pytest.fixture
def admin_user_account(db_session):
    """Create an admin user account for testing."""
    import bcrypt
    from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel
    password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8")
    account = UserAccountDBModel(
        username="admin",
        password_hash=password_hash,
        is_active=True,
        created_by=1,
    )
    db_session.add(account)
    db_session.commit()
    return account


@pytest.fixture
def test_user_account(db_session):
    """Create a test user account."""
    import bcrypt
    from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel
    password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("utf-8")
    account = UserAccountDBModel(
        username="testuser",
        password_hash=password_hash,
        is_active=True,
        created_by=1,
    )
    db_session.add(account)
    db_session.commit()
    return account


@pytest.fixture
def logged_in_client(client, test_user_account):
    """Flask test client with a logged-in user session."""
    with client.session_transaction() as sess:
        sess["web_has_user_privileges"] = True
        sess["web_has_admin_privileges"] = False
        from selfdroid.Helpers import Helpers
        sess["web_login_timestamp"] = Helpers.get_current_unix_timestamp()
        sess["user_account_id"] = test_user_account.id
        sess["user_account_username"] = test_user_account.username
    return client


@pytest.fixture
def logged_in_admin_client(client, admin_user_account):
    """Flask test client with a logged-in admin session."""
    with client.session_transaction() as sess:
        sess["web_has_user_privileges"] = True
        sess["web_has_admin_privileges"] = True
        from selfdroid.Helpers import Helpers
        sess["web_login_timestamp"] = Helpers.get_current_unix_timestamp()
        sess["user_account_id"] = admin_user_account.id
        sess["user_account_username"] = admin_user_account.username
    return client


@pytest.fixture
def test_app_metadata(db_session):
    """Create a test app metadata entry."""
    from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel
    app_meta = AppMetadataDBModel(
        app_name="Test App",
        package_name="com.test.app",
        version_code=1,
        version_name="1.0.0",
        min_api_level=21,
        max_api_level=None,
        apk_file_size=1024,
        price_usd=Decimal("9.99"),
        currency="usd",
        is_published=False,
        is_approved=False,
    )
    db_session.add(app_meta)
    db_session.commit()
    return app_meta
