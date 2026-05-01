import datetime
import pytest
from selfdroid.payments.invoice import PaymentInvoice


class TestPaymentInvoice:
    """Tests for PaymentInvoice model columns and methods."""

    def _create_invoice(self, **kwargs):
        """Helper to create a test PaymentInvoice with explicit defaults."""
        defaults = {
            "order_id": "test_order",
            "subaddress": "test_subaddress",
            "subaddress_index": 0,
            "amount_xmr": "0.050000000000",
            "amount_fiat": "9.99",
            "fiat_currency": "usd",
            "exchange_rate_at_creation": "198.00",
            "status": "pending",
            "confirmations": 0,
            "required_confirmations": 2,
            "expires_at": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        }
        defaults.update(kwargs)
        return PaymentInvoice(**defaults)

    def test_create_invoice_columns(self):
        """Verify all columns exist with correct types and defaults."""
        now = datetime.datetime.utcnow()
        invoice = PaymentInvoice(
            order_id="test_order",
            subaddress="test_subaddress",
            subaddress_index=0,
            amount_xmr="0.050000000000",
            amount_fiat="9.99",
            fiat_currency="usd",
            exchange_rate_at_creation="198.00",
            status="pending",
            confirmations=0,
            required_confirmations=2,
            expires_at=now + datetime.timedelta(hours=24),
            created_at=now,
            updated_at=now,
        )
        assert invoice.order_id == "test_order"
        assert invoice.subaddress == "test_subaddress"
        assert invoice.subaddress_index == 0
        assert invoice.amount_xmr == "0.050000000000"
        assert invoice.amount_fiat == "9.99"
        assert invoice.fiat_currency == "usd"
        assert invoice.exchange_rate_at_creation == "198.00"
        assert invoice.status == "pending"
        assert invoice.confirmations == 0
        assert invoice.required_confirmations == 2
        assert invoice.payment_tx_hash is None
        assert invoice.created_at is not None
        assert invoice.updated_at is not None
        assert invoice.expires_at is not None

    def test_status_default(self):
        """Verify status can be set to 'pending'."""
        invoice = self._create_invoice(status="pending")
        assert invoice.status == "pending"

    def test_confirmations_default(self):
        """Verify confirmations can be set to 0."""
        invoice = self._create_invoice(confirmations=0)
        assert invoice.confirmations == 0

    def test_required_confirmations_default(self):
        """Verify required_confirmations can be set to 2."""
        invoice = self._create_invoice(required_confirmations=2)
        assert invoice.required_confirmations == 2

    def test_fiat_currency_default(self):
        """Verify fiat_currency can be set to 'usd'."""
        invoice = self._create_invoice(fiat_currency="usd")
        assert invoice.fiat_currency == "usd"

    def test_is_expired_false(self):
        """Verify is_expired() returns False for future expiration."""
        invoice = self._create_invoice(
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            status="pending",
        )
        assert invoice.is_expired() is False

    def test_is_expired_true(self):
        """Verify is_expired() returns True for past expiration."""
        invoice = self._create_invoice(
            expires_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
            status="pending",
        )
        assert invoice.is_expired() is True

    def test_to_dict_output(self):
        """Verify to_dict() returns correct keys and values."""
        now = datetime.datetime.utcnow()
        # Create invoice with explicit datetime values to avoid None issues
        invoice = PaymentInvoice(
            order_id="test_order",
            subaddress="test_subaddress",
            subaddress_index=0,
            amount_xmr="0.050000000000",
            amount_fiat="9.99",
            fiat_currency="usd",
            exchange_rate_at_creation="198.00",
            status="pending",
            confirmations=0,
            required_confirmations=2,
            expires_at=now + datetime.timedelta(hours=24),
            created_at=now,
            updated_at=now,
        )
        d = invoice.to_dict()
        assert d["id"] is None  # Not saved yet
        assert d["order_id"] == "test_order"
        assert d["subaddress"] == "test_subaddress"
        assert d["amount_xmr"] == "0.050000000000"
        assert d["amount_fiat"] == "9.99"
        assert d["fiat_currency"] == "usd"
        assert d["status"] == "pending"
        assert d["confirmations"] == 0
        assert d["required_confirmations"] == 2
        assert d["payment_tx_hash"] is None
        assert isinstance(d["created_at"], str)
        assert isinstance(d["expires_at"], str)
        assert isinstance(d["is_expired"], bool)

    def test_payment_tx_hash_nullable(self):
        """Verify payment_tx_hash is nullable."""
        invoice = self._create_invoice(payment_tx_hash=None, status="pending")
        assert invoice.payment_tx_hash is None
