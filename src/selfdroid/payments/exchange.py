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
