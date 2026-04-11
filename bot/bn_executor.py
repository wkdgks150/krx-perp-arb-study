"""
Binance Futures Executor — stock perp trading (REAL MONEY)
"""
import os
import json
import hmac
import hashlib
import time
import ssl
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode

ssl._create_default_https_context = ssl._create_unverified_context

# Load env
for line in open(os.path.join(os.path.dirname(__file__), ".env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("BINANCE_API_KEY", "")
SECRET = os.environ.get("BINANCE_SECRET_KEY", "")
BASE = "https://fapi.binance.com"

# Ticker → Binance symbol
SYMBOLS = {
    "GOOGL": "GOOGLUSDT",
    "NVDA":  "NVDAUSDT",
    "TSLA":  "TSLAUSDT",
    "AAPL":  "AAPLUSDT",
    "META":  "METAUSDT",
    "AMZN":  "AMZNUSDT",
    "SPY":   "SPYUSDT",
    "QQQ":   "QQQUSDT",
    "MSFT":  "MSFTUSDT",  # might not exist, will error gracefully
    "COIN":  "COINUSDT",
    "MSTR":  "MSTRUSDT",
    "INTC":  "INTCUSDT",
}


def _read_error_body(e: HTTPError) -> str:
    try:
        return e.read().decode("utf-8", errors="replace")[:400]
    except Exception:
        return ""


def _signed(method, path, params=None):
    params = params or {}
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 10000
    query = urlencode(params)
    sig = hmac.new(SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE}{path}?{query}&signature={sig}"
    data = None
    if method == "POST":
        url = f"{BASE}{path}"
        body = f"{query}&signature={sig}"
        data = body.encode()
    req = Request(url, data=data, method=method, headers={"X-MBX-APIKEY": API_KEY})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        raise RuntimeError(f"Binance {method} {path} → HTTP {e.code}: {_read_error_body(e)}") from None


def _public(path, params=None):
    query = urlencode(params) if params else ""
    url = f"{BASE}{path}?{query}" if query else f"{BASE}{path}"
    req = Request(url)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        raise RuntimeError(f"Binance GET {path} → HTTP {e.code}: {_read_error_body(e)}") from None


class BinanceExecutor:
    def get_balance(self):
        acct = _signed("GET", "/fapi/v2/account")
        return float(acct.get("availableBalance", 0))

    def get_account(self):
        return _signed("GET", "/fapi/v2/account")

    def get_price(self, ticker):
        sym = SYMBOLS.get(ticker, ticker + "USDT")
        data = _public("/fapi/v1/ticker/price", {"symbol": sym})
        return float(data["price"])

    def get_positions(self):
        acct = _signed("GET", "/fapi/v2/account")
        return [p for p in acct.get("positions", []) if float(p.get("positionAmt", 0)) != 0]

    def set_isolated(self, ticker):
        """Set margin type to ISOLATED."""
        sym = SYMBOLS.get(ticker, ticker + "USDT")
        try:
            return _signed("POST", "/fapi/v1/marginType", {"symbol": sym, "marginType": "ISOLATED"})
        except Exception:
            pass  # already isolated

    def set_leverage(self, ticker, leverage=10):
        sym = SYMBOLS.get(ticker, ticker + "USDT")
        self.set_isolated(ticker)  # always ensure isolated
        return _signed("POST", "/fapi/v1/leverage", {"symbol": sym, "leverage": leverage})

    def market_order(self, ticker, side, usdc_amount):
        """
        Place market order.
        side: "BUY" (long) or "SELL" (short)
        usdc_amount: dollar value of position
        """
        sym = SYMBOLS.get(ticker, ticker + "USDT")
        price = self.get_price(ticker)
        qty = round(usdc_amount / price, 2)

        if qty * price < 5:
            return {"success": False, "error": f"Order too small: ${qty * price:.2f} < $5"}

        try:
            result = _signed("POST", "/fapi/v1/order", {
                "symbol": sym,
                "side": side,
                "type": "MARKET",
                "quantity": qty,
            })
            # avgPrice often comes as 0 for MARKET orders — fetch actual fill
            fill_price = float(result.get("avgPrice", 0))
            if fill_price == 0:
                import time
                time.sleep(1)
                fill_price = self.get_price(ticker)  # fallback to current price
            return {
                "success": True,
                "ticker": ticker,
                "symbol": sym,
                "side": side,
                "qty": float(result.get("origQty", qty)),
                "price": fill_price,
                "value": float(result.get("origQty", qty)) * fill_price,
                "orderId": result.get("orderId"),
                "status": result.get("status"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def long(self, ticker, usdc_amount):
        return self.market_order(ticker, "BUY", usdc_amount)

    def short(self, ticker, usdc_amount):
        return self.market_order(ticker, "SELL", usdc_amount)

    def close_position(self, ticker):
        """Close position for a ticker."""
        sym = SYMBOLS.get(ticker, ticker + "USDT")
        acct = _signed("GET", "/fapi/v2/account")
        for p in acct.get("positions", []):
            if p["symbol"] == sym:
                amt = float(p["positionAmt"])
                if amt == 0:
                    return {"success": False, "error": "No position"}
                side = "SELL" if amt > 0 else "BUY"
                qty = abs(amt)
                try:
                    result = _signed("POST", "/fapi/v1/order", {
                        "symbol": sym,
                        "side": side,
                        "type": "MARKET",
                        "quantity": qty,
                        "reduceOnly": "true",
                    })
                    fill_price = float(result.get("avgPrice", 0))
                    if fill_price == 0:
                        import time
                        time.sleep(1)
                        fill_price = self.get_price(ticker)
                    return {
                        "success": True,
                        "ticker": ticker,
                        "side": side,
                        "qty": qty,
                        "price": fill_price,
                        "value": qty * fill_price,
                        "orderId": result.get("orderId"),
                    }
                except Exception as e:
                    return {"success": False, "error": str(e)}
        return {"success": False, "error": f"No position for {ticker}"}

    def close_all(self):
        results = []
        positions = self.get_positions()
        for p in positions:
            sym = p["symbol"]
            # Find ticker from symbol
            ticker = sym.replace("USDT", "")
            r = self.close_position(ticker)
            results.append(r)
        return results


if __name__ == "__main__":
    ex = BinanceExecutor()
    bal = ex.get_balance()
    print(f"Balance: ${bal:.2f}")
    print()
    for t in ["GOOGL", "NVDA", "TSLA"]:
        p = ex.get_price(t)
        print(f"{t}: ${p:.2f}")
    print()
    positions = ex.get_positions()
    if positions:
        for p in positions:
            print(f"Position: {p['symbol']} qty={p['positionAmt']} entry=${float(p['entryPrice']):.2f}")
    else:
        print("No positions")
