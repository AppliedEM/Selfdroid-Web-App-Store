# Monero payment configuration
import os

MONERO_NETWORK = os.environ.get("SELFDROID_MONERO_NETWORK", "mainnet")  # mainnet or testnet
MONERO_WALLET_RPC_URL = os.environ.get(
    "MONERO_WALLET_RPC_URL",
    "http://localhost:18088/json_rpc" if MONERO_NETWORK == "mainnet" else "http://localhost:28088/json_rpc"
)  # Local wallet-rpc (testnet uses port 28088 by convention)
MONERO_WALLET_RPC_ENABLED = True

# Wallet settings
MONERO_ACCOUNT_INDEX = 0
MONERO_SUBADDRESS_INDEX = 0  # Increment per invoice

# Payment settings
DEFAULT_CONFIRMATIONS = 2  # Minimum confirmations before marking paid
INVOICE_EXPIRY_SECONDS = 86400  # 24 hours
MIN_PAYMENT_AMOUNT_XMR = 0.001 if MONERO_NETWORK == "mainnet" else 0.01  # Higher threshold on testnet (no real value)

# Network-specific daemon address for wallet-rpc command
MONERO_DAEMON_ADDRESS = os.environ.get(
    "MONERO_DAEMON_ADDRESS",
    "http://node.monerodevs.org:18089" if MONERO_NETWORK == "mainnet" else "http://node.monerodevs.org:28089"
)

# Network-specific flag for wallet-rpc startup command
MONERO_NETWORK_FLAG = f"--{MONERO_NETWORK}" if MONERO_NETWORK != "mainnet" else ""

# Exchange rate settings
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
EXCHANGE_RATE_CACHE_TTL = 60  # seconds
SUPPORTED_FIAT_CURRENCIES = ["usd", "eur", "gbp"]

# Display
XMR_DECIMAL_PLACES = 12  # Monero has 12 decimal places (piconero)
