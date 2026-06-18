"""
Unit tests for Monero payment settings and configuration.

Tests verify that all settings have valid values and appropriate defaults.
Note: MONERO_NETWORK will be added during testnet buildout phase.
"""

import pytest


class TestPaymentSettingsValues:
    """Verify all settings have sensible default values."""

    def test_rpc_url_is_string(self):
        """MONERO_WALLET_RPC_URL should be a non-empty string."""
        from selfdroid.payments.settings import MONERO_WALLET_RPC_URL

        assert isinstance(MONERO_WALLET_RPC_URL, str)
        assert len(MONERO_WALLET_RPC_URL) > 0
        assert "/json_rpc" in MONERO_WALLET_RPC_URL

    def test_rpc_enabled_by_default(self):
        """MONERO_WALLET_RPC_ENABLED should be True by default."""
        from selfdroid.payments.settings import MONERO_WALLET_RPC_ENABLED

        assert MONERO_WALLET_RPC_ENABLED is True

    def test_account_index_non_negative(self):
        """MONERO_ACCOUNT_INDEX should be non-negative integer."""
        from selfdroid.payments.settings import MONERO_ACCOUNT_INDEX

        assert isinstance(MONERO_ACCOUNT_INDEX, int)
        assert MONERO_ACCOUNT_INDEX >= 0

    def test_subaddress_index_non_negative(self):
        """MONERO_SUBADDRESS_INDEX should be non-negative integer."""
        from selfdroid.payments.settings import MONERO_SUBADDRESS_INDEX

        assert isinstance(MONERO_SUBADDRESS_INDEX, int)
        assert MONERO_SUBADDRESS_INDEX >= 0

    def test_default_confirmations_positive_integer(self):
        """DEFAULT_CONFIRMATIONS should be a positive integer (2)."""
        from selfdroid.payments.settings import DEFAULT_CONFIRMATIONS

        assert isinstance(DEFAULT_CONFIRMATIONS, int)
        assert DEFAULT_CONFIRMATIONS > 0
        assert DEFAULT_CONFIRMATIONS == 2

    def test_invoice_expiry_is_24_hours(self):
        """INVOICE_EXPIRY_SECONDS should be 86400 (24 hours)."""
        from selfdroid.payments.settings import INVOICE_EXPIRY_SECONDS

        assert isinstance(INVOICE_EXPIRY_SECONDS, int)
        assert INVOICE_EXPIRY_SECONDS == 86400


class TestExchangeRateSettings:
    """Verify exchange rate configuration settings."""

    def test_coingecko_api_url(self):
        """COINGECKO_API_URL should point to CoinGecko v3 API."""
        from selfdroid.payments.settings import COINGECKO_API_URL

        assert isinstance(COINGECKO_API_URL, str)
        assert "coingecko.com" in COINGECKO_API_URL.lower()
        assert "v3/simple/price" in COINGECKO_API_URL

    def test_cache_ttl_is_positive(self):
        """EXCHANGE_RATE_CACHE_TTL should be positive (60 seconds)."""
        from selfdroid.payments.settings import EXCHANGE_RATE_CACHE_TTL

        assert isinstance(EXCHANGE_RATE_CACHE_TTL, int)
        assert EXCHANGE_RATE_CACHE_TTL > 0
        assert EXCHANGE_RATE_CACHE_TTL == 60

    def test_supported_currencies_list(self):
        """SUPPORTED_FIAT_CURRENCIES should be a list of valid currencies."""
        from selfdroid.payments.settings import SUPPORTED_FIAT_CURRENCIES

        assert isinstance(SUPPORTED_FIAT_CURRENCIES, list)
        assert len(SUPPORTED_FIAT_CURRENCIES) >= 1
        for currency in SUPPORTED_FIAT_CURRENCIES:
            assert isinstance(currency, str)
            assert len(currency) == 3
            assert currency.islower()

    def test_usd_in_supported_currencies(self):
        """USD should always be supported (primary fiat)."""
        from selfdroid.payments.settings import SUPPORTED_FIAT_CURRENCIES

        assert "usd" in SUPPORTED_FIAT_CURRENCIES


class TestXMRDisplaySettings:
    """Verify Monero display formatting settings."""

    def test_decimal_places_is_12(self):
        """XMR_DECIMAL_PLACES should be 12 (piconero precision)."""
        from selfdroid.payments.settings import XMR_DECIMAL_PLACES

        assert isinstance(XMR_DECIMAL_PLACES, int)
        assert XMR_DECIMAL_PLACES == 12


class TestMinPaymentAmount:
    """Verify minimum payment amount settings."""

    def test_min_amount_positive(self):
        """MIN_PAYMENT_AMOUNT_XMR should be positive (0.001 = 1 millinero)."""
        from selfdroid.payments.settings import MIN_PAYMENT_AMOUNT_XMR

        assert MIN_PAYMENT_AMOUNT_XMR > 0
        assert MIN_PAYMENT_AMOUNT_XMR == 0.001


class TestSettingsImportConsistency:
    """Verify settings can be imported consistently by other modules."""

    def test_gateway_can_import_settings(self):
        """Gateway module should successfully import all needed settings."""
        from selfdroid.payments.gateway import (
            MONERO_WALLET_RPC_URL,
            MONERO_ACCOUNT_INDEX,
            DEFAULT_CONFIRMATIONS,
            COINGECKO_API_URL,
            EXCHANGE_RATE_CACHE_TTL,
            XMR_DECIMAL_PLACES,
        )

        # All imports should succeed without error
        assert MONERO_WALLET_RPC_URL is not None
        assert isinstance(MONERO_ACCOUNT_INDEX, int)
        assert isinstance(DEFAULT_CONFIRMATIONS, int)
        assert COINGECKO_API_URL is not None
        assert isinstance(EXCHANGE_RATE_CACHE_TTL, int)
        assert XMR_DECIMAL_PLACES == 12

    def test_invoice_can_import_settings(self):
        """Invoice module should be able to access expiry settings."""
        from selfdroid.payments.settings import INVOICE_EXPIRY_SECONDS

        # Verify the value is accessible and reasonable (24 hours)
        assert INVOICE_EXPIRY_SECONDS == 86400
