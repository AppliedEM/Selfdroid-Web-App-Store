import datetime
import decimal
import pytest
from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel
from selfdroid.appstorage.AppMetadata import AppMetadata


class TestAppMetadata:
    """Tests for AppMetadata wrapper class - is_free and to_api_dict."""

    def _create_db_model(self, price_usd=None, price_xmr=None):
        """Helper to create a test AppMetadataDBModel."""
        return AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.app",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            max_api_level=30,
            apk_file_size=10240,
            price_usd=price_usd,
            price_xmr=price_xmr,
            currency="usd",
            is_published=True,
            is_approved=True,
            added_datetime=datetime.datetime.utcnow(),
            last_updated_datetime=datetime.datetime.utcnow(),
        )

    def test_is_free_true_when_null(self):
        """Verify is_free returns True when price_usd is NULL."""
        db_model = self._create_db_model(price_usd=None)
        meta = AppMetadata(db_model)
        assert meta.is_free is True

    def test_is_free_true_when_zero(self):
        """Verify is_free returns True when price_usd is 0."""
        db_model = self._create_db_model(price_usd=decimal.Decimal("0"))
        meta = AppMetadata(db_model)
        assert meta.is_free is True

    def test_is_free_false_when_positive(self):
        """Verify is_free returns False when price_usd > 0."""
        db_model = self._create_db_model(price_usd=decimal.Decimal("9.99"))
        meta = AppMetadata(db_model)
        assert meta.is_free is False

    def test_to_api_dict_includes_new_fields(self):
        """Verify to_api_dict() includes all new pricing/ownership fields."""
        db_model = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.app",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            max_api_level=30,
            apk_file_size=10240,
            uploaded_by=5,
            owner_username="testuser",
            price_usd=decimal.Decimal("9.99"),
            price_xmr=decimal.Decimal("0.050000000000"),
            currency="usd",
            is_published=True,
            is_approved=True,
            added_datetime=datetime.datetime.utcnow(),
            last_updated_datetime=datetime.datetime.utcnow(),
        )
        meta = AppMetadata(db_model)
        d = meta.to_api_dict()

        assert "uploaded_by" in d
        assert "owner_username" in d
        assert "owner_user_id" in d
        assert "price_usd" in d
        assert "price_xmr" in d
        assert "currency" in d
        assert "is_published" in d
        assert "is_approved" in d
        assert "is_free" in d
        assert d["uploaded_by"] == 5
        assert d["owner_username"] == "testuser"
        assert d["price_usd"] == 9.99
        assert d["currency"] == "usd"
        assert d["is_published"] is True
        assert d["is_approved"] is True

    def test_to_api_dict_price_usd_none(self):
        """Verify price_usd is None in API dict when not set."""
        db_model = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.app2",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=10240,
            price_usd=None,
            added_datetime=datetime.datetime.utcnow(),
            last_updated_datetime=datetime.datetime.utcnow(),
        )
        meta = AppMetadata(db_model)
        d = meta.to_api_dict()
        assert d["price_usd"] is None

    def test_to_api_dict_owner_username(self):
        """Verify owner_username is included in API dict."""
        db_model = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.app3",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=10240,
            owner_username="owneruser",
            added_datetime=datetime.datetime.utcnow(),
            last_updated_datetime=datetime.datetime.utcnow(),
        )
        meta = AppMetadata(db_model)
        d = meta.to_api_dict()
        assert d["owner_username"] == "owneruser"

    def test_to_api_dict_is_published(self):
        """Verify is_published is included in API dict."""
        db_model = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.app4",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=10240,
            is_published=False,
            added_datetime=datetime.datetime.utcnow(),
            last_updated_datetime=datetime.datetime.utcnow(),
        )
        meta = AppMetadata(db_model)
        d = meta.to_api_dict()
        assert d["is_published"] is False

    def test_to_api_dict_is_approved(self):
        """Verify is_approved is included in API dict."""
        db_model = AppMetadataDBModel(
            app_name="Test App",
            package_name="com.test.app5",
            version_code=1,
            version_name="1.0.0",
            min_api_level=21,
            apk_file_size=10240,
            is_approved=True,
            added_datetime=datetime.datetime.utcnow(),
            last_updated_datetime=datetime.datetime.utcnow(),
        )
        meta = AppMetadata(db_model)
        d = meta.to_api_dict()
        assert d["is_approved"] is True
