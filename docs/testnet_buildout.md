# Selfdroid — Monero Testnet Payment Support

## Executive Summary

**The project already has significant testnet infrastructure in place.** The `docker-compose.yml`, wallet initialization scripts, and deployment documentation all explicitly support both mainnet and testnet. However, the **Python payment module (`payments/settings.py`) lacks a runtime network selector**, meaning there's no programmatic way to switch between networks without changing configuration files or using environment variables.

---

## Architecture: Why Testnet Support Exists Already

Monero's RPC API is identical across all three network modes:

| Network | Flag | Default Port | Daemon Port |
|---------|------|--------------|-------------|
| Mainnet | (none) | 18088 | 18089 |
| Testnet | `--testnet` | 18088 | 28089 |
| Regtest | `--regtest` | 18088 | 18088 |

The RPC API (`create_address`, `get_balance`, `get_transfers`) is **identical** across all networks. The only difference is the subaddress prefix: mainnet addresses start with `4`, testnet starts with `T`. This is handled automatically by monero-wallet-rpc — no code changes needed in Selfdroid to handle this.

---

## Current State Assessment

### Files Already Configured for Testnet

#### 1. Docker Compose (`docker-compose.yml`)

The docker-compose file **already uses testnet**:

```yaml
# Lines 8-14 (current state)
command:
- --daemon-address=http://node.monerodevs.org:28089   # Testnet daemon port 28089
- --trusted-daemon
- --rpc-bind-port=18088
- --disable-rpc-login
- --wallet-file=/wallet/wallet_testnet                # Testnet wallet file
- --testnet                                           # Testnet flag present
- --password=testpass123
```

**To switch to mainnet**, only these lines would need changing:
- Line 8: Port `28089` → `18089`
- Line 12: `wallet_testnet` → `wallet_mainnet`
- Line 13: Remove `--testnet` flag

#### 2. Wallet Initialization Scripts (`scripts/init_wallet.py`)

Both network modes are supported via CLI arguments:

```python
# Lines 25-27 — Remote node endpoints already defined for both networks
REMOTE_NODES = {
    "mainnet": ["node3.monerodevs.org:18089", ...],
    "testnet": ["node.monerodevs.org:28089", ...]
}

# Lines 115, 219, 251 — Conditional testnet flag already implemented
flags.extend(["--testnet"] if network == "testnet" else [])

# Lines 330-334 — CLI argument for network selection exists
parser.add_argument("network", choices=["mainnet", "testnet"])
```

**Makefile targets already exist:**
- `make wallet-init-mainnet` → runs `scripts/init_wallet.sh mainnet`
- `make wallet-init-testnet` → runs `scripts/init_wallet.sh testnet`

#### 3. Wallet Data Files (Already Present)

The testnet wallet and daemon were previously set up and operational:

```
wallet_data/
├── wallet_backup_testnet.json    ← Testnet backup exists
├── wallet_testnet                ← Testnet wallet data file
├── wallet_testnet.address.txt    ← Testnet payment address
└── wallet_testnet.keys           ← Testnet private view key

monero_data/testnet/
├── bitmonero.log                 ← Testnet daemon log (was running)
├── lmdb/                         ← Testnet blockchain data
└── p2pstate.bin                  ← P2P state file
```

---

### Files That Are Network-Agnostic (Zero Changes Needed)

#### 4. Payment Gateway (`src/selfdroid/payments/gateway.py`)

**No hardcoded mainnet references anywhere.** All functionality is network-independent:

| Line | Finding | Complexity |
|------|---------|------------|
| All RPC calls | Uses `MONERO_WALLET_RPC_URL` from settings — port 18088 is standard for both networks | Trivial (already configured) |
| Lines 69-72, 78, 86-89, 109-113 | RPC methods (`create_address`, `get_balance`, `get_transfers`) work identically on testnet | None needed |
| Line 79-80, 120-121 | Amount conversion (piconero to XMR) is network-independent: 1e12 piconero = 1 XMR on all networks | None needed |
| Lines 141-168 | CoinGecko API for exchange rates — works the same regardless of blockchain | None needed |
| Line 204 | `monero:` URI scheme is standard across all networks | None needed |

**Verdict:** Zero code changes required. The gateway is already network-agnostic.

#### 5. Invoice Model (`src/selfdroid/payments/invoice.py`)

Fully network-agnostic:
- No network-specific fields; subaddress format is identical across networks (both start with `4` for mainnet, `T` for testnet)
- Confirmation count logic works identically on both networks

**Verdict:** Zero changes required.

#### 6. Payment Checker (`src/selfdroid/payments/checker.py`)

Fully network-agnostic:
- Query for pending/confirming invoices — identical logic on both networks
- `is_expired()` check works identically
- `MIN_CONFIRMATION_THRESHOLD` = 1 piconero — this is the same threshold on testnet

**Note:** Testnet blocks are found faster (~every few minutes vs. ~2 hours for mainnet), so the 30-second poll interval in line 21 is actually *too aggressive* for mainnet and fine for testnet. No code change needed, but worth documenting.

#### 7. Payment Endpoints (`src/selfdroid/payments/endpoints.py`)

Fully network-agnostic:
- No hardcoded addresses or amounts — all values come from gateway/settings
- Currency symbol map is USD/EUR/GBP specific, not network-specific
- Invoice expiry of 24 hours (86400s) works on both networks

**Verdict:** Zero changes required.

#### 8. Exchange Rate Module (`src/selfdroid/payments/exchange.py`)

Uses CoinGecko API for XMR/USD rates. This is **network-agnostic** because:
- XMR exists as a cryptocurrency on both mainnet and testnet
- Testnet XMR has no market value, so the exchange rate would be $0 or fallback to cached mainnet rate

**Consideration:** CoinGecko only tracks mainnet XMR price. Displaying mainnet exchange rates for testnet invoices is fine for testing purposes — it's a reference value only.

#### 9. Payment Templates (HTML)

- `payment_page.html` — Generic payment UI, no hardcoded addresses
- `payments/payment_checkout.html` — Shows "Monero (XMR)" generically
- `payments/payment_invoice.html` — Displays invoice data dynamically

**Verdict:** Zero changes required.

---

### The Critical Gap: Payment Settings

#### 10. Payment Settings (`src/selfdroid/payments/settings.py`)

This is the **primary file that needs modification**. Current state:

```python
# Line 2 — Hardcoded; works for both networks via docker-compose env var override
MONERO_WALLET_RPC_URL = "http://localhost:18088/json_rpc"

# Lines 6-7 — Identical on both networks
MONERO_ACCOUNT_INDEX = 0
MONERO_SUBADDRESS_INDEX = 0

# Line 12 — This is 1 millinero; testnet XMR has no real value but this could be lowered for testing convenience
MIN_PAYMENT_AMOUNT_XMR = 0.001
```

**What needs to change:** Add a network selector that can be controlled via environment variable:

```python
# ADD THIS after line 2:
MONERO_NETWORK = os.environ.get("SELFDROID_MONERO_NETWORK", "mainnet")  # mainnet or testnet
```

Then optionally use this in `gateway.py` if any network-specific behavior is needed (currently none).

**Complexity:** Trivial — one line addition + optional env var propagation.

---

## Implementation Plan

### Phase 1: Minimum Viable Changes (~30 minutes)

Add runtime network selector to settings and propagate through configuration.

**File: `src/selfdroid/payments/settings.py`**
```python
# After line 2, add:
MONERO_NETWORK = os.environ.get("SELFDROID_MONERO_NETWORK", "mainnet")
```

**File: `docker-compose.yml` (flask service)**
Add environment variable to Flask container:
```yaml
environment:
- MONERO_WALLET_RPC_URL=http://host.docker.internal:18088/json_rpc
+ MONERO_NETWORK=testnet  # or mainnet depending on wallet-rpc config
```

**File: `docker-compose.yml` (wallet-rpc service)**
Make network configurable via environment variable instead of hardcoded:
```yaml
command:
- --daemon-address=${MONERO_DAEMON_ADDRESS:http://node.monerodevs.org:28089}
- ...
+ - ${MONERO_NETWORK_FLAG:--testnet}  # Pass as flag or empty string for mainnet
- --wallet-file=/wallet/${MONERO_WALLET_FILE:wallet_testnet}
```

### Phase 2: Optional Enhancements (~1-2 hours)

**A. Add network logging to gateway**

```python
# In src/selfdroid/payments/gateway.py, add after line 34:
def _log_network_info(self):
    logger.info("Monero network: %s", self._network if hasattr(self, '_network') else 'unknown')
```

Call this in `__init__` or on first RPC call for visibility.

**B. Adjust payment checker poll interval based on network**
--DO NOT DO--

Testnet has faster block times, so the 30-second poll might be unnecessary overhead:
```python
# In src/selfdroid/payments/checker.py line 21
POLL_INTERVAL = 60 if MONERO_NETWORK == "testnet" else 30  # Or vice versa based on preference
```

**C. Add testnet-specific minimum payment amount**
REMOVE ALL MINIMUM PAYMENT AMOUNTS

Testnet XMR has no value, so lower the minimum for testing convenience:
```python
# In src/selfdroid/payments/settings.py line 12
MIN_PAYMENT_AMOUNT_XMR = 0.001 if MONERO_NETWORK == "mainnet" else 0.01  # Higher threshold on testnet (no real value)
```

**D. Update docker-compose with network-specific daemon addresses**

```yaml
environment:
- MONERO_DAEMON_ADDRESS=http://node.monerodevs.org:${MONERO_DAEMON_PORT:28089}  # Testnet port
- MONERO_WALLET_FILE=wallet_${MONERO_NETWORK:testnet}
```

### Phase 3: Testing & Validation (~1-2 hours)

1. **Verify wallet-rpc connects to testnet daemon**
   - Run `docker-compose up` and check health endpoint
   - Test `monero-wallet-rpc --testnet get_version` via RPC call

2. **Test subaddress generation and QR codes**
   - Create a test invoice for any app
   - Verify the subaddress starts with `T` (testnet prefix)
   - Generate QR code and verify it's scannable

3. **Simulate payment flow on testnet**
   - Use testnet faucets to send XMR to generated subaddress
   - Verify payment checker detects incoming payment
   - Confirm status transitions through `pending` → `confirming` → `confirmed`

4. **Test download access after confirmed payment**
   - Verify that downloading the APK works after payment confirmation
   - Check that expired downloads are properly rejected

---

## Known Considerations (Not Bugs)

### Testnet Faucets

To test payments, you need testnet XMR from a faucet:
- `https://t.xmr.pm/` — Quick faucet (2 XMR/day, no registration)
- `http://monero.fail/` — Alternative faucet
- `https://testnet.moneroexplorer.com/faucet` — Explorer-based faucet

### Daemon Availability

The public testnet daemon `node.monerodevs.org:28089` is generally reliable but occasionally goes down. For production testing, consider running your own monerod instance with `--testnet`.

### Exchange Rates Display

CoinGecko only tracks mainnet XMR price. Testnet invoices will show mainnet reference prices (displayed as "≈ $X.XX"). This is acceptable for testing purposes since testnet has no real value. Consider adding a banner or note: *"Testnet — displayed prices are mainnet reference values."*

### Subaddress Prefix Handling

No changes needed in Selfdroid code, but worth noting for debugging:
- Mainnet addresses start with `4` (e.g., `49...`)
- Testnet addresses start with `T` (e.g., `TF...`)

---

## Effort Estimate Summary

| Category | Effort |
|----------|--------|
| **Minimum viable changes** (Phase 1) | 30 minutes |
| **Polished implementation** (Phase 2) | 1-2 hours |
| **Testing & validation** (Phase 3) | 1-2 hours |
| **Documentation updates** | 30 minutes |

**Total: ~4-6 hours for a polished, production-ready testnet experience.**

---

## Quick Start Commands for Testing

### Using existing docker-compose (already in testnet mode):

```bash
# 1. Ensure wallet-rpc is running with testnet flags
docker-compose up -d wallet-rpc

# 2. Verify connection to testnet daemon
curl -X POST http://localhost:18088/json_rpc \
     -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","id":"0","method":"get_version"}'

# 3. Start Flask app with network selector
docker-compose up flask

# 4. Test payment flow through web UI
# Navigate to /web/payment-checkout and create an invoice
```

### With mainnet configuration:

```bash
# Edit docker-compose.yml lines 8, 12-13:
# Line 8: --daemon-address=http://node.monerodevs.org:18089  (mainnet port)
# Line 12: --wallet-file=/wallet/wallet_mainnet
# Line 13: Remove --testnet flag

# Or set environment variables:
MONERO_NETWORK=mainnet MONERO_DAEMON_PORT=18089 docker-compose up -d wallet-rpc
```

### Initializing wallets from scratch:

```bash
# Testnet wallet initialization (existing Makefile target)
make wallet-init-testnet PASSWORD=testpass123 NETWORK=testnet

# Mainnet wallet initialization (existing Makefile target)  
make wallet-init-mainnet PASSWORD=yourmainnethere NETWORK=mainnet
```

---

## Migration Path for Production

If you want to ship testnet as an option alongside mainnet:

1. **Add `MONERO_NETWORK` environment variable** to both Flask and wallet-rpc services
2. **Create separate docker-compose files**: `docker-compose.mainnet.yml` and `docker-compose.testnet.yml`
3. **Document the difference prominently** in deployment guides
4. **Consider adding a visual indicator** in the web UI showing which network is active (e.g., "Running on Testnet" banner)
