"""
Hyperliquid Executor — real trading on DEX
Trades stock tokens (GOOGL, NVDA, MSFT) via spot margin on Hyperliquid
"""
import os
import json
import time
from typing import Optional

# Load env
for line in open(os.path.join(os.path.dirname(__file__), ".env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from eth_account import Account

# Token name → Hyperliquid spot market name
STOCK_MARKETS = {
    "GOOGL": "@266",
    "TSLA":  "@264",
    "AAPL":  "@268",
    "MSFT":  "@289",
    "META":  "@287",
    "AMZN":  "@280",
    "SPY":   "@279",
    "HOOD":  "@271",
    # NVDA: not yet listed as spot market on Hyperliquid
}


class HyperliquidExecutor:
    def __init__(self):
        self.wallet = os.environ["HYPERLIQUID_WALLET"]
        account = Account.from_key(os.environ["HYPERLIQUID_PRIVATE_KEY"])
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        self.exchange = Exchange(account, constants.MAINNET_API_URL)

    def get_balance(self) -> float:
        """Get USDC balance."""
        spot = self.info.spot_user_state(self.wallet)
        for b in spot.get("balances", []):
            if b["coin"] == "USDC":
                return float(b["total"])
        return 0.0

    def get_all_balances(self) -> dict:
        """Get all token balances."""
        spot = self.info.spot_user_state(self.wallet)
        return {b["coin"]: float(b["total"]) for b in spot.get("balances", []) if float(b["total"]) > 0}

    def get_price(self, ticker: str) -> float:
        """Get current mid price for a stock token."""
        market = STOCK_MARKETS.get(ticker)
        if not market:
            raise ValueError(f"Unknown ticker: {ticker}")
        mids = self.info.all_mids()
        return float(mids.get(market, 0))

    def buy(self, ticker: str, usdc_amount: float) -> dict:
        """Buy stock token with USDC amount."""
        market = STOCK_MARKETS.get(ticker)
        if not market:
            raise ValueError(f"Unknown ticker: {ticker}")

        price = self.get_price(ticker)
        if price <= 0:
            raise ValueError(f"Invalid price for {ticker}: {price}")

        # Calculate shares (round to 2 decimals for stock tokens)
        sz = round(usdc_amount / price, 2)
        if sz * price < 10:
            raise ValueError(f"Order too small: ${sz * price:.2f} < $10 minimum")

        result = self.exchange.market_open(
            name=market,
            is_buy=True,
            sz=sz,
            px=price,
            slippage=0.01,
        )
        status = result.get("response", {}).get("data", {}).get("statuses", [{}])[0]
        filled = status.get("filled")
        error = status.get("error")

        if error:
            return {"success": False, "error": error}

        return {
            "success": True,
            "ticker": ticker,
            "side": "BUY",
            "sz": float(filled["totalSz"]),
            "price": float(filled["avgPx"]),
            "value": float(filled["totalSz"]) * float(filled["avgPx"]),
            "oid": filled["oid"],
        }

    def sell(self, ticker: str, sz: float = None) -> dict:
        """Sell stock token. If sz=None, sell all."""
        market = STOCK_MARKETS.get(ticker)
        if not market:
            raise ValueError(f"Unknown ticker: {ticker}")

        # Get current holdings if sz not specified
        if sz is None:
            balances = self.get_all_balances()
            sz = balances.get(ticker, 0)

        if sz <= 0:
            return {"success": False, "error": f"No {ticker} to sell"}

        price = self.get_price(ticker)
        sz = round(sz, 2)

        if sz * price < 10:
            return {"success": False, "error": f"Position too small to sell: ${sz * price:.2f}"}

        result = self.exchange.market_open(
            name=market,
            is_buy=False,
            sz=sz,
            px=price,
            slippage=0.01,
        )
        status = result.get("response", {}).get("data", {}).get("statuses", [{}])[0]
        filled = status.get("filled")
        error = status.get("error")

        if error:
            return {"success": False, "error": error}

        return {
            "success": True,
            "ticker": ticker,
            "side": "SELL",
            "sz": float(filled["totalSz"]),
            "price": float(filled["avgPx"]),
            "value": float(filled["totalSz"]) * float(filled["avgPx"]),
            "oid": filled["oid"],
        }

    def sell_all(self) -> list:
        """Sell all stock positions."""
        balances = self.get_all_balances()
        results = []
        for coin, amount in balances.items():
            if coin == "USDC":
                continue
            if coin in STOCK_MARKETS:
                r = self.sell(coin, amount)
                results.append(r)
        return results


if __name__ == "__main__":
    ex = HyperliquidExecutor()
    print(f"USDC Balance: ${ex.get_balance():.2f}")
    print(f"All balances: {ex.get_all_balances()}")
    print()
    for t in ["GOOGL", "NVDA", "MSFT"]:
        try:
            p = ex.get_price(t)
            print(f"{t}: ${p:.2f}")
        except Exception as e:
            print(f"{t}: {e}")
