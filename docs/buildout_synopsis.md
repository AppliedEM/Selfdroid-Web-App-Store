# Monero Payment Buildout — Synopsis

## Overview

Added Monero (XMR) payment support to Selfdroid for app upload/distribution fees. Customers pay with XMR, with prices displayed in both fiat (USD) and XMR. A unique subaddress is generated per invoice for privacy and tracking.

## What Was Built

### Payment Module (`src/selfdroid/payments/`)

| File | Purpose |
|------|---------|
| `settings.py` | Configuration: wallet RPC URL, confirmations threshold, exchange rate TTL, supported currencies |
| `gateway.py` | Core `MoneroGateway` class — JSON-RPC calls to `monero-wallet-rpc` for address creation, balance, payment checking, fiat/XMR conversion, QR URI generation |
| `invoice.py` | `PaymentInvoice` SQLAlchemy model — stores order ID, subaddress, amounts, status, confirmations, expiry |
| `exchange.py` | CoinGecko rate fetching with class-level TTL cache (60s) |
| `checker.py` | `PaymentChecker` background thread — polls every 30s for pending/confirming invoices, updates status, detects expired invoices |
| `endpoints.py` | Flask blueprint (`/web` prefix) with 4 routes: checkout form, invoice creation, status check, QR image, webhook receiver |
| `forms.py` | WTForms for payment checkout and gateway settings |
| `__init__.py` | Blueprint registration, checker thread start |

### Templates (`src/selfdroid/web/templates/payments/`)

| File | Purpose |
|------|---------|
| `payment_checkout.html` | Admin form: enter order ID, amount, currency |
| `payment_invoice.html` | Invoice display: QR code (base64), payment address, fiat/XMR amounts, exchange rate, status badge, expiry |

### Infrastructure

| File | Purpose |
|------|---------|
| `docker-compose.yml` | `wallet-rpc` service (view-only wallet, public Monero node) |
| `Dockerfile` | Optional separate payment service container |
| `.env` | Wallet file, password, daemon address, CoinGecko key template |
| `.gitignore` | Added `.env`, `wallet_data/`, `*.keys`, `*.wallet` |
| `src/requirements_payments.txt` | Additional deps: `requests`, `qrcode`, `Pillow` |

### Integration

- `src/selfdroid/__init__.py` updated to call `init_payments(app)` — registers blueprint and starts checker thread

## Architecture

```
Flask App
  ├── /web/payment-checkout (GET/POST) → generates invoice + QR
  ├── /web/payment-status/<id> (GET) → JSON status + payment check
  ├── /web/payment-qr/<id> (GET) → PNG QR image
  ├── /web/payment-webhook (POST) → external callback receiver
  └── PaymentChecker (background thread, 30s poll)
        └── checks all pending invoices via wallet-rpc get_transfers

monero-wallet-rpc (Docker)
  ├── View-only wallet (no spend keys on server)
  ├── create_address → unique subaddress per invoice
  ├── get_transfers → payment detection
  └── Connects to public node (node.moneroworld.com)
```

## Key Design Decisions

- **View-only wallet**: Server can detect payments but never spend funds. Safe against server compromise.
- **Unique subaddress per invoice**: Privacy + automatic payment matching.
- **2 confirmations**: Minimum before marking payment confirmed (balances double-spend risk).
- **24h invoice expiry**: Auto-expired by checker thread.
- **CoinGecko free API**: Cached for 60s. No API key required for low volume.
- **Direct HTTP RPC**: Lightweight `requests` calls to wallet-rpc JSON-RPC endpoint (no heavy library dependency).

## Pre-Deployment Checklist

1. [ ] Create Monero wallet: `monero-wallet-cli --generate-new-wallet selfdroid_xmr`
2. [ ] Create view-only wallet: `monero-wallet-cli --generate-from-view-key selfdroid_xmr_viewonly`
3. [ ] Copy wallet files to server: `scp selfdroid_xmr_viewonly* user@server:/srv/selfdroid/wallet_data/`
4. [ ] Update `docker-compose.yml` with wallet file path and password
5. [ ] Fill in `.env` with wallet credentials
6. [ ] Start infrastructure: `docker-compose up -d`
7. [ ] Verify wallet-rpc: `curl http://localhost:18088/json_rpc`
8. [ ] Test with Monero testnet before mainnet deployment

## Routes

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/web/payment-checkout` | GET/POST | Admin | Create payment invoice |
| `/web/payment-status/<id>` | GET | — | JSON payment status |
| `/web/payment-qr/<id>` | GET | — | PNG QR code image |
| `/web/payment-webhook` | POST | — | External callback receiver |

## Estimated Effort (Remaining)

| Task | Effort |
|------|--------|
| Wallet setup | 30 min |
| Docker infra + test | 30 min |
| Testnet testing | 2 hours |
| Mainnet deployment | 1 hour |
| **Total remaining** | **~3.5 hours** |
