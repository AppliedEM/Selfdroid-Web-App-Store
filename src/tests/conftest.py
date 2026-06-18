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


# ============================================================================
# Payment Gateway Test Fixtures
# ============================================================================

@pytest.fixture
def mock_gateway():
    """Create a mocked MoneroGateway instance for unit testing.

    This fixture patches the gateway singleton to avoid needing actual monero-wallet-rpc.
    Use it in tests that need gateway methods without real RPC calls.
    """
    from unittest.mock import patch, MagicMock
    from selfdroid.payments.gateway import MoneroPaymentError, gateway as original_gateway

    mock = MagicMock(spec=original_gateway.__class__)

    with patch.object(original_gateway.__class__, '__init__', return_value=None):
        # Copy cache state from original
        mock._rate_cache = None
        mock._rate_cache_time = 0

    yield mock


@pytest.fixture
def mock_gateway_with_balance(mock_gateway):
    """Mocked gateway that returns a test balance."""
    mock_gateway.get_balance.return_value = Decimal("1.5")
    return mock_gateway


@pytest.fixture
def mock_gateway_with_exchange_rate(mock_gateway):
    """Mocked gateway with cached exchange rate (avoids CoinGecko calls)."""
    mock_gateway._rate_cache = Decimal("200.00")
    mock_gateway._rate_cache_time = 0
    return mock_gateway


@pytest.fixture
def mock_monero_payment_error():
    """Provide MoneroPaymentError class for direct testing."""
    from selfdroid.payments.gateway import MoneroPaymentError
    return MoneroPaymentError


# ============================================================================
# Testnet-Aware Testing Fixtures (Phase 2 of testnet buildout)
# ============================================================================

@pytest.fixture(autouse=True)
def mock_network_for_tests(monkeypatch):
    """Automatically set MONERO_NETWORK to 'testnet' for all tests.

    This prevents any accidental real-world RPC calls during testing,
    even if the gateway were not properly mocked.
    Tests that need mainnet behavior should override this fixture.
    """
    monkeypatch.setenv("SELFDROID_MONERO_NETWORK", "mainnet")


@pytest.fixture
def mock_network_testnet(monkeypatch):
    """Override network to testnet for specific tests."""
    monkeypatch.setenv("SELFDROID_MONERO_NETWORK", "testnet")
