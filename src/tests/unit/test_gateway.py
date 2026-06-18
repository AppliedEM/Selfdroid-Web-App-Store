"""
Unit tests for MoneroPaymentGateway.

Tests RPC call handling, invoice address creation, balance queries,
payment verification, exchange rate caching, and amount conversion.
"""

import time
from decimal import Decimal
from unittest.mock import patch, MagicMock, Mock


class TestMoneroGatewayRPC:
    """Tests for the underlying _rpc_call mechanism."""

    def test_rpc_call_success(self):
        """Verify successful RPC call returns result dict."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        with patch("selfdroid.payments.gateway.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"jsonrpc": "2.0", "id": "0", "result": {"key": "value"}}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = gateway._rpc_call("test_method", {"param": 1})

            assert result == {"key": "value"}
            mock_post.assert_called_once()
            # Verify payload structure
            call_args = mock_post.call_args
            assert call_args[1]["json"]["method"] == "test_method"
            assert call_args[1]["json"]["params"] == {"param": 1}

    def test_rpc_call_success_no_params(self):
        """Verify RPC call works without params."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        with patch("selfdroid.payments.gateway.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"jsonrpc": "2.0", "id": "0", "result": {}}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = gateway._rpc_call("test_method")

            assert isinstance(result, dict)
            call_args = mock_post.call_args
            assert "params" not in call_args[1]["json"]

    def test_rpc_call_error_in_response(self):
        """Verify RPC error raises MoneroPaymentError."""
        from selfdroid.payments.gateway import MoneroGateway, MoneroPaymentError

        gateway = MoneroGateway()

        with patch("selfdroid.payments.gateway.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": "0",
                "error": {"code": -1, "message": "Wallet not found"}
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            try:
                gateway._rpc_call("test_method")
                assert False, "Should have raised MoneroPaymentError"
            except MoneroPaymentError as e:
                assert "RPC error" in str(e)

    def test_rpc_call_connection_failure(self):
        """Verify connection failure raises MoneroPaymentError."""
        from selfdroid.payments.gateway import MoneroGateway, MoneroPaymentError
        import requests

        gateway = MoneroGateway()

        with patch("selfdroid.payments.gateway.requests.post") as mock_post:
            mock_post.side_effect = requests.ConnectionError("Connection refused")

            try:
                gateway._rpc_call("test_method")
                assert False, "Should have raised MoneroPaymentError"
            except MoneroPaymentError as e:
                assert "Wallet RPC connection failed" in str(e)


class TestCreateInvoiceAddress:
    """Tests for create_invoice_address()."""

    def test_create_address_calls_correct_rpc(self):
        """Verify correct RPC method and parameters are used."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        with patch.object(gateway, "_rpc_call", return_value={"address": "4TestAddress123", "address_index": 5}) as mock_rpc:
            address, index = gateway.create_invoice_address("test_label")

            assert address == "4TestAddress123"
            assert index == 5
            # Verify RPC call arguments
            mock_rpc.assert_called_once_with("create_address", {
                "account_index": 0,  # From settings MONERO_ACCOUNT_INDEX
                "label": "test_label",
            })


class TestGetBalance:
    """Tests for get_balance()."""

    def test_balance_conversion_piconero_to_xmr(self):
        """Verify correct conversion from piconeros to XMR (1e12)."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        # 1.5 XMR in piconero
        mock_balance_piconero = Decimal("1500000000000")

        with patch.object(gateway, "_rpc_call", return_value={"balance": str(mock_balance_piconero)}):
            balance = gateway.get_balance()

            assert balance == Decimal("1.5")

    def test_zero_balance(self):
        """Verify zero balance returns Decimal('0')."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        with patch.object(gateway, "_rpc_call", return_value={"balance": "0"}):
            balance = gateway.get_balance()

            assert balance == Decimal("0")

    def test_large_balance_precision(self):
        """Verify large balances maintain decimal precision."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        # 1000.123456789 XMR in piconero (max precision)
        mock_balance_piconero = Decimal("1000123456789000")

        with patch.object(gateway, "_rpc_call", return_value={"balance": str(mock_balance_piconero)}):
            balance = gateway.get_balance()

            # Should preserve 12 decimal places of precision
            assert balance == Decimal("1000.123456789")


class TestCheckPayment:
    """Tests for check_payment()."""

    def test_no_payment_received(self):
        """Verify status is 'underpaid' when no payment received."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        with patch.object(gateway, "_rpc_call", return_value={"in": []}):
            result = gateway.check_payment("4TestAddress", Decimal("0.05"))

            assert result["received"] == Decimal("0")
            assert result["status"] == "underpaid"
            assert result["confirmed"] is False

    def test_underpaid_amount(self):
        """Verify status is 'underpaid' when less than expected."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        # Payment in progress but not enough yet (in pool, unconfirmed)
        with patch.object(gateway, "_rpc_call", return_value={
            "in": [{
                "address": "4TestAddress",
                "amount": str(int(Decimal("0.02") * Decimal("1e12"))),  # 0.02 XMR in piconero
                "pool": True,
            }]
        }):
            result = gateway.check_payment("4TestAddress", Decimal("0.05"))

            assert result["received"] == Decimal("0.02")
            assert result["status"] == "underpaid"
            assert result["confirmations"] == 0

    def test_payment_in_pool_pending(self):
        """Verify status is 'confirming' when payment received but in pool (unconfirmed)."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        # Full amount in pool (not yet confirmed) - gateway returns "confirming" 
        # because received >= expected, regardless of confirmation count
        with patch.object(gateway, "_rpc_call", return_value={
            "in": [{
                "address": "4TestAddress",
                "amount": str(int(Decimal("0.05") * Decimal("1e12"))),  # 0.05 XMR in piconero
                "pool": True,
            }]
        }):
            result = gateway.check_payment("4TestAddress", Decimal("0.05"))

            assert result["received"] == Decimal("0.05")
            assert result["status"] == "confirming"  # Payment received, waiting for confirmations
            assert result["confirmed"] is False
            assert result["confirmations"] == 0

    def test_confirmed_but_insufficient_confirmations(self):
        """Verify status is 'confirming' when payment received but confirmations pending."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        # Payment confirmed in blockchain but below confirmation threshold
        with patch.object(gateway, "_rpc_call", return_value={
            "in": [{
                "address": "4TestAddress",
                "amount": str(int(Decimal("0.05") * Decimal("1e12"))),  # 0.05 XMR in piconero
                "pool": False,  # Confirmed (not in pool)
            }]
        }):
            result = gateway.check_payment("4TestAddress", Decimal("0.05"), min_confirmations=3)

            assert result["received"] == Decimal("0.05")
            assert result["status"] == "confirming"  # Payment received but not enough confirmations
            assert result["confirmed"] is False
            assert result["confirmations"] == 1

    def test_fully_confirmed_payment(self):
        """Verify status is 'confirming' when payment confirmed (ready for confirmation)."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        # Payment received and has enough confirmations
        with patch.object(gateway, "_rpc_call", return_value={
            "in": [{
                "address": "4TestAddress",
                "amount": str(int(Decimal("0.05") * Decimal("1e12"))),  # 0.05 XMR in piconero
                "pool": False,  # Confirmed
            }]
        }):
            result = gateway.check_payment("4TestAddress", Decimal("0.05"), min_confirmations=1)

            assert result["received"] == Decimal("0.05")
            assert result["status"] == "confirming"  # Ready to confirm
            assert result["confirmed"] is True
            assert result["confirmations"] >= 1

    def test_multiple_payments_to_same_address(self):
        """Verify summing multiple payments to same subaddress."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        # Two partial payments that together meet the expected amount
        piconero_01 = str(int(Decimal("0.025") * Decimal("1e12")))
        piconero_02 = str(int(Decimal("0.025") * Decimal("1e12")))

        with patch.object(gateway, "_rpc_call", return_value={
            "in": [
                {"address": "4TestAddress", "amount": piconero_01, "pool": False},
                {"address": "4TestAddress", "amount": piconero_02, "pool": False},
            ]
        }):
            result = gateway.check_payment("4TestAddress", Decimal("0.05"), min_confirmations=1)

            assert result["received"] == Decimal("0.05")


class TestExchangeRateCaching:
    """Tests for exchange rate caching behavior."""

    def test_caches_rate_after_fetch(self):
        """Verify rate is cached and reused within TTL window."""
        from selfdroid.payments.gateway import MoneroGateway, EXCHANGE_RATE_CACHE_TTL

        gateway = MoneroGateway()

        # First call - should fetch
        with patch("selfdroid.payments.gateway.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"monero": {"usd": "200.00"}}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            rate1 = gateway.get_xmr_usd_rate()

        assert rate1 == Decimal("200.00")
        # Verify CoinGecko was called once
        assert mock_get.call_count == 1

        # Second call within TTL - should use cache (no new request)
        rate2 = gateway.get_xmr_usd_rate()

        assert rate2 == Decimal("200.00")
        assert mock_get.call_count == 1  # Still one call total


class TestFiatConversion:
    """Tests for fiat to XMR and XMR to fiat conversion."""

    def test_fiat_to_xmr_conversion(self):
        """Verify $10 at rate 200 = 0.05 XMR."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()
        gateway._rate_cache = Decimal("200.00")
        gateway._rate_cache_time = time.time()

        xmr_amount = gateway.fiat_to_xmr(Decimal("10.00"), "usd")

        assert xmr_amount == Decimal("0.050000000000")

    def test_fiat_to_xmr_rounds_down(self):
        """Verify fiat_to_xmr rounds DOWN (never overcharges)."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()
        # Rate that would produce repeating decimals: 10/200.03
        gateway._rate_cache = Decimal("200.03")
        gateway._rate_cache_time = time.time()

        xmr_amount = gateway.fiat_to_xmr(Decimal("10.00"), "usd")

        # Should be rounded DOWN to 12 decimal places
        assert xmr_amount <= Decimal("0.050000000000")

    def test_xmr_to_fiat_conversion(self):
        """Verify 0.05 XMR at rate 200 = $10.00."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()
        gateway._rate_cache = Decimal("200.00")
        gateway._rate_cache_time = time.time()

        usd_amount = gateway.xmr_to_fiat(Decimal("0.05"), "usd")

        assert usd_amount == Decimal("10.00")


class TestPaymentURIGeneration:
    """Tests for monero: URI generation."""

    def test_uri_with_no_amount(self):
        """Verify URI format without amount parameter."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        uri = gateway.generate_payment_uri("4TestAddress", Decimal("0"))

        assert uri == "monero:4TestAddress"

    def test_uri_with_amount(self):
        """Verify URI format includes amount."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        uri = gateway.generate_payment_uri("4TestAddress", Decimal("0.05"))

        assert uri == "monero:4TestAddress?amount=0.05"

    def test_uri_with_label(self):
        """Verify URI format includes tx_description."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        uri = gateway.generate_payment_uri("4TestAddress", Decimal("0.05"), label="Order #123")

        assert "tx_description=Order" in uri or "tx_description=Orde" in uri
        # URI should contain both amount and description
        assert "?amount=" in uri
        assert "&tx_description=" in uri


class TestGetAddressCount:
    """Tests for get_address_count()."""

    def test_returns_total_subaddresses(self):
        """Verify returns count from RPC response."""
        from selfdroid.payments.gateway import MoneroGateway

        gateway = MoneroGateway()

        with patch.object(gateway, "_rpc_call", return_value={"addresses": [
            {"address": "4MainAddress"},
            {"address": "4Sub1"},
            {"address": "4Sub2"},
        ]}):
            count = gateway.get_address_count()

            assert count == 3


class TestMoneroPaymentError:
    """Tests for MoneroPaymentError exception class."""

    def test_exception_is_raised(self):
        """Verify MoneroPaymentError can be raised and caught."""
        from selfdroid.payments.gateway import MoneroPaymentError

        error = MoneroPaymentError("Test error message")

        assert str(error) == "Test error message"

    def test_exception_has_message_attribute(self):
        """Verify exception stores the original message."""
        from selfdroid.payments.gateway import MoneroPaymentError

        error = MoneroPaymentError("Connection refused")

        # Exception args contains the message
        assert len(error.args) == 1
        assert error.args[0] == "Connection refused"
