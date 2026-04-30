# Monero payment configuration
MONERO_WALLET_RPC_URL = "http://localhost:18088/json_rpc"  # Local wallet-rpc
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
