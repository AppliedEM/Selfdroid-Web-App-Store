# Selfdroid Monero Payments — Buildout Plan

## Overview

Add Monero (XMR) payment support to the Selfdroid self-hosted Android app store. Customers can pay for app uploads/distributions with XMR, with prices displayed in both fiat (USD) and XMR.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Selfdroid (Flask app)                                │
│                                                       │
│  /web/payments/checkout → creates invoice             │
│  → calls monero-wallet-rpc "create_address"           │
│  → generates subaddress for this order                │
│  → fetches XMR/USD rate from CoinGecko                │
│  → displays subaddress + amount (XMR + USD) + QR      │
│                                                       │
│  Background worker (thread)                           │
│  → polls wallet-rpc "query_key"/"get_transfers"       │
│  → checks if subaddress received required amount      │
│  → on confirmed payment: updates order status         │
│  → fires webhook/callback to complete order           │
└──────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│  monero-wallet-rpc (Docker container)               │
│  - View-only wallet (no spend keys on server)        │
│  - Generates subaddresses                             │
│  - Scans for incoming payments                        │
│  - Connects to public node (testing) / own node (prod)│
└──────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│  monerod (Docker container, optional for testing)    │
│  - Full or pruned node for blockchain data           │
│  - For testing: connect to public node instead        │
└──────────────────────────────────────────────────────┘
```

## Key Decisions

### 1. Wallet Approach: View-Only Wallet + Subaddresses Per Invoice
- Create a **view-only wallet** from your main wallet (private view key + public address only)
- The server can generate subaddresses and detect incoming payments but **cannot spend funds**
- If the server is compromised, your XMR is safe
- Generate **one unique subaddress per invoice** (order)
- Use `monero-wallet-rpc` RPC calls for all wallet operations

### 2. Python Library: `monero` Package (pip install monero)
- AcceptXMR is a **Rust library** — not directly usable from Flask
- The `monero` Python package (`pip install monero`) provides a `JSONRPCWallet` backend
- It connects to `monero-wallet-rpc` and supports: balance, address generation, subaddresses
- For payment detection, we'll use direct RPC calls via `requests` library (lightweight for 5 invoices)

### 3. Fiat Pricing: CoinGecko Free API
- Endpoint: `GET https://api.coingecko.com/api/v3/simple/price?ids=monero&vs_currencies=usd`
- Free tier: no API key needed, rate-limited (~100 calls/min)
- Cache the rate for 60 seconds to avoid hitting limits
- Display both USD and XMR amounts to the customer

### 4. Public Node for Testing
- Use `node.moneroworld.com:18089` (restricted public RPC) or similar
- Run `monero-wallet-rpc` with `--daemon-address http://node.moneroworld.com:18089 --untrusted-daemon`
- Eventually replace with your own node

### 5. Scale: 5 Invoices Max
- No need for complex infrastructure yet
- Simple Flask background thread for polling
- SQLite for invoice storage (reuse existing DB or separate table)
- Polling interval: 10-30 seconds (plenty for low volume)

---

## Step-by-Step Buildout

### Phase 1: Foundation (Wallet Setup)

#### 1.1 Create a Monero Wallet (if you don't have one)
```bash
# Using monero-wallet-cli on your local machine (air-gapped if possible)
monero-wallet-cli --generate-new-wallet selfdroid_xmr

# Note down your:
# - Primary address (starts with 4)
# - Private view key
# - 25-word seed phrase (store securely!)
```

#### 1.2 Create a View-Only Wallet
```bash
# From your main wallet CLI:
monero-wallet-cli --wallet-file selfdroid_xmr --password <your_password> \
  --generate-from-view-key selfdroid_xmr_viewonly \
  --daemon-address http://node.moneroworld.com:18089

# When prompted, enter your primary address and private view key
# Leave spend key blank
```

#### 1.3 Test the View-Only Wallet
```bash
# Open the view-only wallet via RPC
monero-wallet-rpc \
  --wallet-file selfdroid_xmr_viewonly \
  --rpc-bind-port 18088 \
  --daemon-address http://node.moneroworld.com:18089 \
  --untrusted-daemon \
  --disable-rpc-login

# In another terminal, test address generation:
curl -X POST http://127.0.0.1:18088/json_rpc \
  -d '{"jsonrpc":"2.0","id":"0","method":"create_address","params":{"account_index":0,"label":"test"}}' \
  -H "Content-Type: application/json"
```

---

### Phase 2: Docker Infrastructure

#### 2.1 Create `docker-compose.yml`

```yaml
version: '3.8'

services:
  # Monero Wallet RPC (view-only, handles payment detection)
  wallet-rpc:
    image: ghcr.io/monero-project/monero:latest
    container_name: selfdroid-wallet-rpc
    command: >
      monero-wallet-rpc
      --daemon-address http://node.moneroworld.com:18089
      --untrusted-daemon
      --rpc-bind-ip 0.0.0.0
      --rpc-bind-port 18088
      --disable-rpc-login
      --wallet-dir /wallet
      --confirm-external-bind
    volumes:
      - ./wallet_data:/wallet
    restart: unless-stopped
    networks:
      - selfdroid

  # Optional: Full Monero node for production
  # monerod:
  #   image: ghcr.io/monero-project/monero:latest
  #   container_name: selfdroid-monerod
  #   command: monerod --prune-blockchain --rpc-bind-ip 0.0.0.0 --rpc-bind-port 18081
  #   volumes:
  #     - ./monero_data:/home/monero/.bitmonero
  #   restart: unless-stopped
  #   networks:
  #     - selfdroid

networks:
  selfdroid:
    driver: bridge
```

#### 2.2 Create `.env` for wallet-rpc configuration
```bash
# .env (add to .gitignore)
MONERO_WALLET_FILE=selfdroid_xmr_viewonly
MONERO_WALLET_PASSWORD=
MONERO_DAEMON_ADDRESS=http://node.moneroworld.com:18089
COINGECKO_API_KEY=
```

#### 2.3 Create `Dockerfile` for the payment module (if running as separate service)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements_payments.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY selfdroid_payments/ ./selfdroid_payments/

# Expose port for Flask blueprints (if needed)
EXPOSE 5001

CMD ["python", "-m", "selfdroid_payments"]
```

---

### Phase 3: Flask Payment Module

#### 3.1 Directory Structure

```
src/
├── selfdroid/
│   ├── payments/                    # NEW: Payment module
│   │   ├── __init__.py
│   │   ├── settings.py              # Payment-specific config
│   │   ├── gateway.py               # Core payment gateway logic
│   │   ├── invoice.py               # Invoice model/ORM
│   │   ├── checker.py               # Background payment checker
│   │   ├── exchange.py              # Fiat exchange rate fetching
│   │   ├── endpoints.py             # Payment-related Flask endpoints
│   │   └── forms.py                 # Payment forms (WTForms)
│   ├── ... (existing files)
├── requirements_payments.txt        # NEW: Additional dependencies
├── docker-compose.yml               # NEW
├── Dockerfile                       # NEW (optional)
└── ... (existing files)
```

#### 3.2 `src/requirements_payments.txt`

```
# Existing Selfdroid requirements (from src/requirements.txt)
# Plus Monero payment dependencies:

# Monero wallet RPC communication
# Note: monero package requires monero-wallet-rpc running separately
# We use direct HTTP requests to wallet-rpc for simplicity

# Exchange rate API
requests>=2.28.0

# QR code generation
qrcode>=7.3.1
pillow>=8.3.1

# Decimal support (built-in, but explicit for clarity)
# Use Python's built-in decimal module for precise XMR amounts
```

#### 3.3 `src/selfdroid/payments/settings.py`

```python
# Monero payment configuration
MONERO_WALLET_RPC_URL = "http://wallet-rpc:18088/json_rpc"  # Docker internal
MONERO_WALLET_RPC_ENABLED = True

# Wallet settings
MONERO_ACCOUNT_INDEX = 0
MONERO_SUBADDRESS_INDEX = 0  # Increment per invoice

# Payment settings
DEFAULT_CONFIRMATIONS = 2  # Minimum confirmations before marking paid
INVOICE_EXPIRY_SECONDS = 86400  # 24 hours
MIN_PAYMENT_AMOUNT_XMR = 0.001  # 1 millinero minimum

# Exchange rate settings
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
EXCHANGE_RATE_CACHE_TTL = 60  # seconds
SUPPORTED_FIAT_CURRENCIES = ["usd", "eur", "gbp"]

# Display
XMR_DECIMAL_PLACES = 12  # Monero has 12 decimal places (piconero)
```

#### 3.4 `src/selfdroid/payments/gateway.py`

```python
"""
Core Monero payment gateway.

Handles:
- Creating invoices (generates unique subaddress per invoice)
- Checking payment status for an invoice
- Converting fiat amounts to XMR via CoinGecko
"""

import time
import requests
from decimal import Decimal, ROUND_DOWN
from selfdroid.payments.settings import (
    MONERO_WALLET_RPC_URL,
    MONERO_ACCOUNT_INDEX,
    DEFAULT_CONFIRMATIONS,
    COINGECKO_API_URL,
    EXCHANGE_RATE_CACHE_TTL,
    XMR_DECIMAL_PLACES,
)


class MoneroPaymentError(Exception):
    """Base exception for payment errors."""
    pass


class MoneroGateway:
    def __init__(self):
        self._rate_cache = None
        self._rate_cache_time = 0

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

    def create_invoice_address(self, label: str) -> tuple[str, int]:
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
                "status": str,              # "pending", "confirmed", "underpaid", "expired"
            }
        """
        if min_confirmations is None:
            min_confirmations = DEFAULT_CONFIRMATIONS

        # Get incoming transfers to this address
        # Note: wallet-rpc doesn't have a direct "check address balance" RPC
        # We use get_transfers with the address filter or query the blockchain
        # For view-only wallets, we check via the "incoming_transfers" method
        # or by scanning outputs with the view key

        # Alternative: use the "get_address_balance" approach via get_transfers
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
                # Check if transaction is confirmed (not in mempool)
                if not tx.get("pool", True):
                    confirmed_count += 1

        # For view-only wallets, confirmation count is estimated
        # A more accurate approach uses the block height from the transfer
        confirmed = received >= expected_amount_xmr and confirmed_count >= min_confirmations

        if received >= expected_amount_xmr:
            status = "confirmed" if confirmed else "confirming"
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
            # Return cached rate even if expired, or raise
            if self._rate_cache:
                return self._rate_cache
            raise MoneroPaymentError(f"Failed to fetch exchange rate: {e}")

    def fiat_to_xmr(self, amount_fiat: Decimal, currency: str = "usd") -> Decimal:
        """Convert a fiat amount to XMR using the current exchange rate."""
        rate = self._get_rate(currency)
        # XMR = fiat_amount / rate
        xmr_amount = amount_fiat / rate
        # Round down to 12 decimal places (piconero precision)
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

        # For other currencies, fetch via CoinGecko
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
```

#### 3.5 `src/selfdroid/payments/invoice.py`

```python
"""
Invoice model for storing payment requests.

Reuses the existing SQLite database via Flask-SQLAlchemy.
"""

from selfdroid import db
from datetime import datetime


class PaymentInvoice(db.Model):
    __tablename__ = "payment_invoice"

    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    order_id = db.Column(db.String(64), unique=True, nullable=False)  # Selfdroid order/app ID
    subaddress = db.Column(db.String(95), unique=True, nullable=False)
    subaddress_index = db.Column(db.Integer(), nullable=False)
    amount_xmr = db.Column(db.String(32), nullable=False)  # Stored as string for precision
    amount_fiat = db.Column(db.String(32), nullable=False)
    fiat_currency = db.Column(db.String(3), default="usd")
    exchange_rate_at_creation = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(16), default="pending")  # pending, confirming, confirmed, expired, failed
    confirmations = db.Column(db.Integer(), default=0)
    required_confirmations = db.Column(db.Integer(), default=2)
    payment_tx_hash = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime(), nullable=False)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "subaddress": self.subaddress,
            "amount_xmr": self.amount_xmr,
            "amount_fiat": self.amount_fiat,
            "fiat_currency": self.fiat_currency,
            "status": self.status,
            "confirmations": self.confirmations,
            "required_confirmations": self.required_confirmations,
            "payment_tx_hash": self.payment_tx_hash,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": self.expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            "is_expired": self.is_expired(),
        }
```

#### 3.6 `src/selfdroid/payments/exchange.py`

```python
"""
Fiat exchange rate module.

Caches CoinGecko rates to avoid API rate limits.
"""

import time
import requests
from decimal import Decimal
from selfdroid.payments.settings import COINGECKO_API_URL, EXCHANGE_RATE_CACHE_TTL


class RateCache:
    _cache = {}
    _cache_times = {}
    _ttl = EXCHANGE_RATE_CACHE_TTL

    @classmethod
    def get(cls, key: str) -> Decimal | None:
        if key in cls._cache and (time.time() - cls._cache_times[key]) < cls._ttl:
            return cls._cache[key]
        return None

    @classmethod
    def set(cls, key: str, value: Decimal):
        cls._cache[key] = value
        cls._cache_times[key] = time.time()


def get_xmr_rate(currency: str = "usd") -> Decimal:
    """Get XMR price in the given currency."""
    cache_key = f"xmr_{currency}"
    cached = RateCache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(COINGECKO_API_URL, params={
            "ids": "monero",
            "vs_currencies": currency,
        }, timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = Decimal(str(data["monero"][currency]))
        RateCache.set(cache_key, rate)
        return rate
    except (requests.RequestException, KeyError, TypeError) as e:
        raise Exception(f"Failed to fetch {currency.upper()} rate: {e}")


def xmr_to_fiat(amount_xmr: Decimal, currency: str = "usd") -> str:
    """Convert XMR to fiat, return formatted string."""
    rate = get_xmr_rate(currency)
    result = (amount_xmr * rate).quantize(Decimal("0.01"))
    return str(result)


def fiat_to_xmr(amount_fiat: Decimal, currency: str = "usd") -> str:
    """Convert fiat to XMR, return formatted string."""
    rate = get_xmr_rate(currency)
    if rate <= 0:
        raise Exception("Invalid exchange rate")
    result = (amount_fiat / rate).quantize(Decimal("0." + "0" * 12))
    return str(result)
```

#### 3.7 `src/selfdroid/payments/checker.py`

```python
"""
Background payment checker.

Runs as a Flask application thread. Polls monero-wallet-rpc
for payment confirmations on all pending invoices.
"""

import threading
import time
import logging
from decimal import Decimal
from selfdroid import app
from selfdroid.payments.invoice import PaymentInvoice
from selfdroid.payments.gateway import gateway

logger = logging.getLogger(__name__)

# Polling interval in seconds (30s is fine for low-volume)
POLL_INTERVAL = 30
# Minimum received amount before checking confirmations (in XMR)
MIN_CONFIRMATION_THRESHOLD = Decimal("0.000000000001")


class PaymentChecker:
    """Background thread that checks pending payments."""

    def __init__(self):
        self._thread = None
        self._running = False

    def start(self):
        """Start the background checker thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        logger.info("Payment checker started")

    def stop(self):
        """Stop the background checker thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Payment checker stopped")

    def _check_loop(self):
        """Main polling loop."""
        while self._running:
            try:
                with app.app_context():
                    self._check_pending_invoices()
            except Exception as e:
                logger.error(f"Error in payment checker: {e}")
            time.sleep(POLL_INTERVAL)

    def _check_pending_invoices(self):
        """Check all pending invoices for payments."""
        pending = PaymentInvoice.query.filter(
            PaymentInvoice.status.in_(["pending", "confirming"])
        ).all()

        for invoice in pending:
            try:
                # Skip expired invoices
                if invoice.is_expired():
                    invoice.status = "expired"
                    app.logger.warning(f"Invoice {invoice.order_id} expired")
                    continue

                expected = Decimal(invoice.amount_xmr)
                result = gateway.check_payment(
                    invoice.subaddress,
                    expected,
                    invoice.required_confirmations,
                )

                # Update invoice status
                if result["status"] == "confirming":
                    invoice.status = "confirming"
                    invoice.confirmations = result["confirmations"]
                elif result["status"] == "confirmed":
                    invoice.status = "confirmed"
                    invoice.confirmations = result["confirmations"]
                    app.logger.info(
                        f"Invoice {invoice.order_id} confirmed: "
                        f"{result['received']} XMR"
                    )
                    # TODO: Trigger webhook/callback here
                    # self._on_payment_confirmed(invoice)
                elif result["status"] == "underpaid":
                    invoice.status = "pending"
                    invoice.confirmations = result["confirmations"]

                # Commit changes
                from selfdroid import db
                db.session.commit()

            except Exception as e:
                app.logger.error(f"Error checking invoice {invoice.order_id}: {e}")
                from selfdroid import db
                db.session.rollback()


# Singleton
checker = PaymentChecker()
```

#### 3.8 `src/selfdroid/payments/endpoints.py`

```python
"""
Flask blueprint for payment-related endpoints.

Routes:
- /web/payment-checkout (GET/POST) - Create payment invoice
- /web/payment-status/<invoice_id> (GET) - Check payment status
- /web/payment-qr/<invoice_id> (GET) - Get QR code data
- /web/payment-webhook (POST) - External webhook receiver (optional)
"""

import logging
import qrcode
import io
import base64
from decimal import Decimal
from flask import (
    Blueprint, request, jsonify, render_template, url_for,
    redirect, send_file, current_app
)
from selfdroid.EndpointExecutor import EndpointExecutor
from selfdroid.web.authenticator.admin_authenticator import AdminAuthenticator
from selfdroid.payments.invoice import PaymentInvoice
from selfdroid.payments.gateway import gateway
from selfdroid.payments.exchange import xmr_to_fiat, fiat_to_xmr
from selfdroid import db

logger = logging.getLogger(__name__)

web_payments_blueprint = Blueprint(
    "web_payments_blueprint", __name__, url_prefix="/web"
)


@web_payments_blueprint.route("/payment-checkout", methods=["GET", "POST"])
def fl_web_payment_checkout():
    """
    Create a payment invoice for an order.

    GET: Show payment form (enter order ID, amount, currency)
    POST: Create invoice, show payment details with QR code
    """
    # Admin authentication required
    if not AdminAuthenticator.is_admin_logged_in():
        return redirect(url_for("web_blueprint.fl_web_login"))

    if request.method == "GET":
        return render_template(
            "payments/payment_checkout.html",
            title="Monero Payment",
        )

    # POST: Create invoice
    order_id = request.form.get("order_id", "")
    amount_fiat = request.form.get("amount_fiat", "0")
    currency = request.form.get("currency", "usd").lower()

    if not order_id or not amount_fiat:
        return render_template(
            "payments/payment_checkout.html",
            title="Monero Payment",
            error="Order ID and amount are required.",
        )

    try:
        amount_fiat_decimal = Decimal(amount_fiat)
        if amount_fiat_decimal <= 0:
            raise ValueError("Amount must be positive")

        # Convert fiat to XMR
        xmr_amount = fiat_to_xmr(amount_fiat_decimal, currency)

        # Generate new subaddress for this invoice
        label = f"Selfdroid Order #{order_id}"
        address, sub_index = gateway.create_invoice_address(label)

        # Get exchange rate at creation time
        rate = gateway.get_xmr_usd_rate() if currency == "usd" else gateway._get_rate(currency)

        # Create invoice record
        from datetime import datetime, timedelta
        invoice = PaymentInvoice(
            order_id=order_id,
            subaddress=address,
            subaddress_index=sub_index,
            amount_xmr=str(xmr_amount),
            amount_fiat=str(amount_fiat_decimal),
            fiat_currency=currency,
            exchange_rate_at_creation=str(rate),
            status="pending",
            required_confirmations=2,
            expires_at=datetime.utcnow() + timedelta(seconds=86400),  # 24h
        )
        db.session.add(invoice)
        db.session.commit()

        # Generate payment URI for QR code
        payment_uri = gateway.generate_payment_uri(address, Decimal(xmr_amount), label)

        # Generate QR code as base64 PNG
        qr = qrcode.make(payment_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return render_template(
            "payments/payment_invoice.html",
            title="Monero Payment",
            invoice=invoice,
            payment_uri=payment_uri,
            qr_base64=qr_base64,
            fiat_amount=str(amount_fiat_decimal),
            currency_symbol={"usd": "$", "eur": "€", "gbp": "£"}.get(currency, currency.upper()),
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating payment invoice: {e}")
        return render_template(
            "payments/payment_checkout.html",
            title="Monero Payment",
            error=str(e),
        )


@web_payments_blueprint.route("/payment-status/<int:invoice_id>", methods=["GET"])
def fl_web_payment_status(invoice_id):
    """Check the status of a payment invoice."""
    invoice = PaymentInvoice.query.get_or_404(invoice_id)
    result = gateway.check_payment(
        invoice.subaddress,
        Decimal(invoice.amount_xmr),
        invoice.required_confirmations,
    )
    return jsonify({
        **invoice.to_dict(),
        "payment_check": result,
    })


@web_payments_blueprint.route("/payment-qr/<int:invoice_id>", methods=["GET"])
def fl_web_payment_qr(invoice_id):
    """Return a QR code image for a payment invoice."""
    invoice = PaymentInvoice.query.get_or_404(invoice_id)
    xmr_amount = Decimal(invoice.amount_xmr)
    label = f"Selfdroid Order #{invoice.order_id}"
    payment_uri = gateway.generate_payment_uri(invoice.subaddress, xmr_amount, label)

    qr = qrcode.make(payment_uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")


@web_payments_blueprint.route("/payment-webhook", methods=["POST"])
def fl_web_payment_webhook():
    """
    Webhook receiver for external payment confirmation callbacks.

    Expected JSON body:
    {
        "invoice_id": 123,
        "subaddress": "4...",
        "amount_xmr": "0.500000000000",
        "tx_hash": "...",
        "confirmations": 6,
        "status": "confirmed"
    }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    invoice_id = data.get("invoice_id")
    if not invoice_id:
        return jsonify({"error": "Missing invoice_id"}), 400

    invoice = PaymentInvoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    # Update invoice
    invoice.status = data.get("status", invoice.status)
    invoice.confirmations = data.get("confirmations", invoice.confirmations)
    invoice.payment_tx_hash = data.get("tx_hash", invoice.payment_tx_hash)
    db.session.commit()

    # TODO: Trigger fulfillment logic here
    # e.g., update Selfdroid order status, notify admin, etc.

    return jsonify({"status": "ok", "invoice_id": invoice_id})
```

#### 3.9 `src/selfdroid/payments/forms.py`

```python
"""
WTForms for payment-related forms.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class PaymentCheckoutForm(FlaskForm):
    """Form for creating a Monero payment invoice."""
    order_id = StringField("Order ID", validators=[DataRequired()])
    amount_fiat = DecimalField(
        "Amount (USD)",
        validators=[DataRequired(), NumberRange(min=0.01)],
        places=2,
    )
    currency = SelectField(
        "Currency",
        choices=[("usd", "USD ($)")],
        default="usd",
        validators=[DataRequired()],
    )
    submit = SubmitField("Generate Payment")


class PaymentSettingsForm(FlaskForm):
    """Form for payment gateway configuration."""
    confirmations_required = StringField(
        "Confirmations Required",
        default="2",
        validators=[Optional()],
    )
    invoice_expiry_hours = StringField(
        "Invoice Expiry (hours)",
        default="24",
        validators=[Optional()],
    )
    min_payment_xmr = StringField(
        "Minimum Payment (XMR)",
        default="0.001",
        validators=[Optional()],
    )
    submit = SubmitField("Save Settings")
```

#### 3.10 `src/selfdroid/payments/__init__.py`

```python
"""
Monero payment module for Selfdroid.

Initializes the payment gateway, registers the Flask blueprint,
and starts the background payment checker.
"""

import logging
from flask import Blueprint
from selfdroid.payments.endpoints import web_payments_blueprint
from selfdroid.payments.checker import checker

logger = logging.getLogger(__name__)


def init_payments(app):
    """Initialize the payment module with the Flask app."""
    # Register blueprint
    app.register_blueprint(web_payments_blueprint)

    # Start background checker
    checker.start()
    logger.info("Monero payment module initialized")

    return app
```

---

### Phase 4: Templates

#### 4.1 `src/selfdroid/web/templates/payments/payment_checkout.html`

```html
{% extends "_web_base.html" %}

{% block title %}Monero Payment - {{ instance_name }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <h2>Monero (XMR) Payment</h2>
    <p class="text-muted">Pay for your order using Monero. A unique payment address will be generated for this transaction.</p>

    {% if error %}
    <div class="alert alert-danger">{{ error }}</div>
    {% endif %}

    <form method="POST" class="mt-3">
        <div class="mb-3">
            <label for="order_id" class="form-label">Order ID</label>
            <input type="text" class="form-control" id="order_id" name="order_id" required
                   placeholder="e.g., APP-12345">
        </div>

        <div class="mb-3">
            <label for="amount_fiat" class="form-label">Amount (USD)</label>
            <input type="number" class="form-control" id="amount_fiat" name="amount_fiat" required
                   step="0.01" min="0.01" placeholder="0.00">
        </div>

        <div class="mb-3">
            <label for="currency" class="form-label">Currency</label>
            <select class="form-select" id="currency" name="currency">
                <option value="usd" selected>USD ($)</option>
            </select>
        </div>

        <button type="submit" class="btn btn-primary">Generate Payment</button>
    </form>

    <div class="mt-4">
        <h5>How to pay with Monero</h5>
        <ol>
            <li>Scan the QR code with your Monero wallet (Cake, Monerujo, etc.)</li>
            <li>Or copy the address and send the exact XMR amount</li>
            <li>Payment is confirmed automatically after 2 blockchain confirmations</li>
            <li>Your order will be processed once payment is confirmed</li>
        </ol>
    </div>
</div>
{% endblock %}
```

#### 4.2 `src/selfdroid/web/templates/payments/payment_invoice.html`

```html
{% extends "_web_base.html" %}

{% block title %}Monero Payment - {{ instance_name }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <h2>Monero Payment Invoice</h2>

    <div class="card mt-3">
        <div class="card-body">
            <h5 class="card-title">Order #{{ invoice.order_id }}</h5>

            <div class="row mt-3">
                <div class="col-md-6">
                    <h6>Payment Details</h6>
                    <table class="table table-sm">
                        <tr>
                            <th>Amount:</th>
                            <td>{{ currency_symbol }}{{ fiat_amount }} USD</td>
                        </tr>
                        <tr>
                            <th>XMR Amount:</th>
                            <td>{{ invoice.amount_xmr }} XMR</td>
                        </tr>
                        <tr>
                            <th>Exchange Rate:</th>
                            <td>1 XMR = {{ invoice.exchange_rate_at_creation }} USD</td>
                        </tr>
                        <tr>
                            <th>Status:</th>
                            <td>
                                <span class="badge bg-{{ 'warning' if invoice.status == 'pending' else 'info' if invoice.status == 'confirming' else 'success' if invoice.status == 'confirmed' else 'danger' }}">
                                    {{ invoice.status|upper }}
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <th>Expires:</th>
                            <td>{{ invoice.expires_at.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                        </tr>
                    </table>
                </div>

                <div class="col-md-6 text-center">
                    <h6>Scan to Pay</h6>
                    <img src="data:image/png;base64,{{ qr_base64 }}"
                         alt="Payment QR Code" class="img-fluid" style="max-width: 256px;">
                    <p class="mt-2 text-break" style="font-size: 0.8rem;">
                        {{ payment_uri }}
                    </p>
                </div>
            </div>

            <div class="mt-3">
                <h6>Payment Address</h6>
                <code class="d-block p-2 bg-light text-break">{{ invoice.subaddress }}</code>
                <button class="btn btn-sm btn-outline-secondary"
                        onclick="navigator.clipboard.writeText('{{ invoice.subaddress }}')">
                    Copy Address
                </button>
            </div>
        </div>
    </div>

    <div class="mt-3">
        <a href="/web/payment-status/{{ invoice.id }}" class="btn btn-outline-primary">
            Check Payment Status
        </a>
        <a href="/web/payment-checkout" class="btn btn-outline-secondary">
            New Payment
        </a>
    </div>
</div>
{% endblock %}
```

---

### Phase 5: Integration with Selfdroid

#### 5.1 Update `src/selfdroid/__init__.py`

```python
# Add at the bottom of the file, after existing blueprints are registered:

from selfdroid.payments import init_payments

# Initialize payment module
init_payments(app)
```

#### 5.2 Add Payment Status to App Details Page

In `src/selfdroid/web/endpoints/WebAppDetailsEndpoint.py` or the template,
add a section showing whether an app upload order has been paid:

```html
<!-- Add to web_app_details.html -->
{% if order.payment_status %}
<div class="alert alert-{{ 'success' if order.payment_status == 'confirmed' else 'warning' }}">
    Payment {{ order.payment_status }}
    {% if order.payment_status == 'pending' %}
    <a href="/web/payment-checkout?order={{ order.id }}">Complete Payment</a>
    {% endif %}
</div>
{% endif %}
```

---

### Phase 6: Security & Operations

#### 6.1 Security Considerations

| Concern | Mitigation |
|---------|-----------|
| View key exposure on server | Use view-only wallet — spend keys never stored on server |
| Wallet-rpc exposed to internet | Bind to `127.0.0.1` or Docker internal network only |
| Payment address reuse | Each invoice gets a unique subaddress |
| Double-spend attacks | Wait for `DEFAULT_CONFIRMATIONS` (2+) before fulfilling |
| Exchange rate manipulation | Cache CoinGecko rate for 60s; use locked-in rate at invoice creation |
| Invoice expiry | Auto-expire invoices after 24h; mark as `expired` in checker |
| Server compromise | Funds are safe — view-only wallet cannot spend |

#### 6.2 Environment Variables (`.env` — add to `.gitignore`)

```bash
# Monero wallet-rpc
MONERO_WALLET_FILE=selfdroid_xmr_viewonly
MONERO_WALLET_PASSWORD=
MONERO_DAEMON_ADDRESS=http://node.moneroworld.com:18089
MONERO_WALLET_RPC_URL=http://wallet-rpc:18088/json_rpc

# CoinGecko (optional API key for higher rate limits)
COINGECKO_API_KEY=

# Payment settings
DEFAULT_CONFIRMATIONS=2
INVOICE_EXPIRY_HOURS=24
MIN_PAYMENT_XMR=0.001
```

#### 6.3 Adding to `.gitignore`

```
# .gitignore additions
.env
wallet_data/
*.keys
*.wallet
__pycache__/
*.pyc
venv/
virtualenv/
```

---

### Phase 7: Deployment Steps

#### 7.1 Initial Setup

```bash
# 1. Create view-only wallet (on your local machine, NOT on the server)
monero-wallet-cli --generate-new-wallet selfdroid_xmr
# Note your address and private view key

monero-wallet-cli --generate-from-view-key selfdroid_xmr_viewonly
# Enter address and private view key, leave spend key blank

# 2. Copy wallet files to server
scp selfdroid_xmr_viewonly* user@server:/srv/selfdroid/wallet_data/

# 3. Update docker-compose.yml with your wallet file path

# 4. Create .env file with your settings

# 5. Start infrastructure
docker-compose up -d

# 6. Verify wallet-rpc is running
curl http://localhost:18088/json_rpc \
  -d '{"jsonrpc":"2.0","id":"0","method":"get_version"}' \
  -H "Content-Type: application/json"

# 7. Verify address generation works
curl -X POST http://localhost:18088/json_rpc \
  -d '{"jsonrpc":"2.0","id":"0","method":"create_address","params":{"account_index":0,"label":"test"}}' \
  -H "Content-Type: application/json"

# 8. Deploy Selfdroid with payment module
# (standard Selfdroid deployment, payment module is included)
```

#### 7.2 Production: Running Your Own Node

```bash
# Replace public node with your own monerod instance
# In docker-compose.yml, uncomment the monerod service

# Then update wallet-rpc command:
# --daemon-address http://monerod:18081 \
# --trusted-daemon
```

---

### Phase 8: Testing

#### 8.1 Test with Monero Testnet

```bash
# Use testnet to avoid spending real XMR
# 1. Create testnet wallet
monero-wallet-cli --testnet --generate-new-wallet test_selfdroid

# 2. Get testnet XMR from a faucet (e.g., https://testnet.xmrchain.net)

# 3. Update docker-compose.yml for testnet:
#    image: ghcr.io/monero-project/monero:latest-v0.18
#    command: monero-wallet-rpc --testnet ...

# 4. Run end-to-end test:
#    - Create invoice via /web/payment-checkout
#    - Send test XMR to the generated address
#    - Verify payment status updates to "confirmed"
```

#### 8.2 Manual RPC Testing

```bash
# Test address generation
curl -X POST http://localhost:18088/json_rpc \
  -d '{"jsonrpc":"2.0","id":"0","method":"create_address","params":{"account_index":0,"label":"test-order-1"}}' \
  -H "Content-Type: application/json"

# Test balance
curl -X POST http://localhost:18088/json_rpc \
  -d '{"jsonrpc":"2.0","id":"0","method":"get_balance","params":{"account_index":0}}' \
  -H "Content-Type: application/json"

# Test CoinGecko rate
curl "https://api.coingecko.com/api/v3/simple/price?ids=monero&vs_currencies=usd"
```

---

## Summary of Changes to Selfdroid

| File | Change |
|------|--------|
| `src/selfdroid/payments/` | New module (8 files) |
| `src/selfdroid/__init__.py` | Register payment blueprint + start checker |
| `src/selfdroid/web/templates/payments/` | New templates (checkout + invoice) |
| `src/requirements_payments.txt` | New requirements file |
| `docker-compose.yml` | New (wallet-rpc service) |
| `.env` | New (wallet config — gitignored) |
| `monero_payments_buildout.md` | This document |

## Estimated Effort

| Phase | Effort | Notes |
|-------|--------|-------|
| Phase 1: Wallet setup | 30 min | One-time setup |
| Phase 2: Docker infra | 30 min | Write compose + test |
| Phase 3: Flask module | 4-6 hours | Core gateway logic |
| Phase 4: Templates | 1-2 hours | UI integration |
| Phase 5: Integration | 1-2 hours | Wire into existing flows |
| Phase 6: Security | 1 hour | Review + hardening |
| Phase 7: Deployment | 1 hour | Initial deploy + test |
| Phase 8: Testing | 2 hours | End-to-end verification |
| **Total** | **~12-16 hours** | For a working MVP |
