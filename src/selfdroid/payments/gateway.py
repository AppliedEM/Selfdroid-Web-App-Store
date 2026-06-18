"""
Core Monero payment gateway.

Handles:
- Creating invoices (generates unique subaddress per invoice)
- Checking payment status for an invoice
- Converting fiat amounts to XMR via CoinGecko
"""

import time
import logging
import requests
from decimal import Decimal, ROUND_DOWN
from selfdroid.payments.settings import (
    MONERO_WALLET_RPC_URL,
    MONERO_ACCOUNT_INDEX,
    DEFAULT_CONFIRMATIONS,
    COINGECKO_API_URL,
    EXCHANGE_RATE_CACHE_TTL,
    XMR_DECIMAL_PLACES,
    MONERO_NETWORK,
)

logger = logging.getLogger(__name__)


class MoneroPaymentError(Exception):
    """Base exception for payment errors."""
    pass


class MoneroGateway:
    def __init__(self):
        self._rate_cache = None
        self._rate_cache_time = 0
        logger.info("MoneroGateway initialized (network=%s)", MONERO_NETWORK)

    def _rpc_call(self, method, params=None):
        """Make a JSON-RPC call to monero-wallet-rpc."""
        payload = {
            "jsonrpc": "2.0",
            "id": "0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        try:
            response = requests.post(MONERO_WALLET_RPC_URL, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise MoneroPaymentError(f"RPC error: {data['error']}")

            return data.get("result", {})
        except requests.RequestException as e:
            raise MoneroPaymentError(f"Wallet RPC connection failed: {e}")

    def create_invoice_address(self, label: str) -> tuple:
        """
        Generate a new subaddress for an invoice.

        Returns:
            (subaddress, subaddress_index)
        """
        result = self._rpc_call("create_address", {
            "account_index": MONERO_ACCOUNT_INDEX,
            "label": label,
        })
        return result["address"], result["address_index"]

    def get_balance(self) -> Decimal:
        """Get the unlocked balance of the wallet in XMR."""
        result = self._rpc_call("get_balance", {"account_index": MONERO_ACCOUNT_INDEX})
        # Balance is returned in piconeros (1 XMR = 1e12 piconeros)
        return Decimal(str(result["balance"])) / Decimal("1000000000000")

    def get_address_count(self) -> int:
        """Get the total number of subaddresses in the account."""
        result = self._rpc_call("get_address", {
            "account_index": MONERO_ACCOUNT_INDEX,
        })
        return len(result["addresses"])

    def check_payment(self, address: str, expected_amount_xmr: Decimal,
                      min_confirmations: int = None) -> dict:
        """
        Check if a specific subaddress has received the expected payment.

        Returns:
            {
                "received": Decimal,        # Amount received in XMR
                "confirmed": bool,          # Whether confirmations >= threshold
                "confirmations": int,       # Current confirmation count
                "required": int,            # Required confirmation threshold
                "status": str,              # "pending", "confirming", "underpaid", "expired"
            }
        """
        if min_confirmations is None:
            min_confirmations = DEFAULT_CONFIRMATIONS

        result = self._rpc_call("get_transfers", {
            "account_index": MONERO_ACCOUNT_INDEX,
            "filter_by_dest": True,
        })

        received = Decimal("0")
        confirmed_count = 0

        for tx in result.get("in", []):
            dest_addr = tx.get("address", "")
            if dest_addr == address:
                amount = Decimal(str(tx["amount"])) / Decimal("1000000000000")
                received += amount
                if not tx.get("pool", True):
                    confirmed_count += 1

        confirmed = received >= expected_amount_xmr and confirmed_count >= min_confirmations

        if received >= expected_amount_xmr:
            status = "confirming"
        else:
            status = "underpaid"

        return {
            "received": received,
            "confirmed": confirmed,
            "confirmations": confirmed_count,
            "required": min_confirmations,
            "status": status,
        }

    def get_xmr_usd_rate(self) -> Decimal:
        """
        Fetch the current XMR/USD exchange rate from CoinGecko.
        Cached for EXCHANGE_RATE_CACHE_TTL seconds.
        """
        now = time.time()
        if self._rate_cache and (now - self._rate_cache_time) < EXCHANGE_RATE_CACHE_TTL:
            return self._rate_cache

        try:
            response = requests.get(COINGECKO_API_URL, params={
                "ids": "monero",
                "vs_currencies": "usd",
            }, timeout=10)
            response.raise_for_status()
            data = response.json()
            rate = Decimal(str(data["monero"]["usd"]))
            self._rate_cache = rate
            self._rate_cache_time = now
            return rate
        except (requests.RequestException, KeyError) as e:
            if self._rate_cache:
                return self._rate_cache
            raise MoneroPaymentError(f"Failed to fetch exchange rate: {e}")

    def fiat_to_xmr(self, amount_fiat: Decimal, currency: str = "usd") -> Decimal:
        """Convert a fiat amount to XMR using the current exchange rate."""
        rate = self._get_rate(currency)
        xmr_amount = amount_fiat / rate
        return xmr_amount.quantize(Decimal("0." + "0" * XMR_DECIMAL_PLACES), rounding=ROUND_DOWN)

    def xmr_to_fiat(self, amount_xmr: Decimal, currency: str = "usd") -> Decimal:
        """Convert XMR to fiat using the current exchange rate."""
        rate = self._get_rate(currency)
        return (amount_xmr * rate).quantize(Decimal("0.01"))

    def _get_rate(self, currency: str) -> Decimal:
        """Fetch exchange rate for a specific currency."""
        if currency == "usd":
            rate = self.get_xmr_usd_rate()
            return rate

        try:
            response = requests.get(COINGECKO_API_URL, params={
                "ids": "monero",
                "vs_currencies": currency,
            }, timeout=10)
            response.raise_for_status()
            data = response.json()
            return Decimal(str(data["monero"][currency]))
        except (requests.RequestException, KeyError) as e:
            raise MoneroPaymentError(f"Failed to fetch {currency.upper()} rate: {e}")

    def generate_payment_uri(self, address: str, amount_xmr: Decimal,
                             label: str = "") -> str:
        """
        Generate a 'monero:' URI string for QR code generation.
        Format: monero:<address>?amount=<XMR>&tx_description=<label>
        """
        uri = f"monero:{address}"
        if amount_xmr > 0:
            uri += f"?amount={amount_xmr}"
        if label:
            uri += f"&tx_description={label}"
        return uri


# Singleton instance
gateway = MoneroGateway()
