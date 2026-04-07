"""
Trade executor — Alpaca API (paper/live)
"""
import json
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import config


class AlpacaExecutor:
    def __init__(self):
        self.base_url = config.ALPACA_BASE_URL
        self.headers = {
            "APCA-API-KEY-ID": config.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY,
            "Content-Type": "application/json",
        }
        self.enabled = bool(config.ALPACA_API_KEY and config.ALPACA_SECRET_KEY)

    def _request(self, method, path, body=None):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = Request(url, data=data, headers=self.headers, method=method)
        try:
            with urlopen(req) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            error_body = e.read().decode()
            print(f"[ALPACA ERROR] {e.code}: {error_body}")
            raise

    def get_account(self):
        return self._request("GET", "/v2/account")

    def get_buying_power(self):
        acct = self.get_account()
        return float(acct["buying_power"])

    def get_positions(self):
        return self._request("GET", "/v2/positions")

    def get_position(self, ticker):
        try:
            return self._request("GET", f"/v2/positions/{ticker}")
        except HTTPError:
            return None

    def market_buy(self, ticker, notional=None, qty=None):
        """Buy at market price. Use notional ($) or qty (shares)."""
        order = {
            "symbol": ticker,
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
        }
        if notional:
            order["notional"] = str(round(notional, 2))
        elif qty:
            order["qty"] = str(qty)
        return self._request("POST", "/v2/orders", order)

    def market_sell(self, ticker, notional=None, qty=None):
        """Sell at market price."""
        order = {
            "symbol": ticker,
            "side": "sell",
            "type": "market",
            "time_in_force": "day",
        }
        if notional:
            order["notional"] = str(round(notional, 2))
        elif qty:
            order["qty"] = str(qty)
        return self._request("POST", "/v2/orders", order)

    def close_position(self, ticker):
        """Close entire position for a ticker."""
        try:
            return self._request("DELETE", f"/v2/positions/{ticker}")
        except HTTPError:
            return None

    def close_all_positions(self):
        """Close all open positions."""
        return self._request("DELETE", "/v2/positions")


class DryRunExecutor:
    """Simulated executor that logs but doesn't trade."""

    def __init__(self):
        self.enabled = True
        self.positions = {}

    def get_buying_power(self):
        return 999999.0

    def get_positions(self):
        return list(self.positions.values())

    def get_position(self, ticker):
        return self.positions.get(ticker)

    def market_buy(self, ticker, notional=None, qty=None):
        order_id = f"dry-{datetime.now().strftime('%H%M%S')}"
        self.positions[ticker] = {"symbol": ticker, "side": "long", "notional": notional, "qty": qty}
        print(f"  [DRY RUN] BUY {ticker} notional=${notional} qty={qty} → {order_id}")
        return {"id": order_id, "status": "filled", "filled_avg_price": "0"}

    def market_sell(self, ticker, notional=None, qty=None):
        order_id = f"dry-{datetime.now().strftime('%H%M%S')}"
        self.positions[ticker] = {"symbol": ticker, "side": "short", "notional": notional, "qty": qty}
        print(f"  [DRY RUN] SELL {ticker} notional=${notional} qty={qty} → {order_id}")
        return {"id": order_id, "status": "filled", "filled_avg_price": "0"}

    def close_position(self, ticker):
        if ticker in self.positions:
            del self.positions[ticker]
        print(f"  [DRY RUN] CLOSE {ticker}")
        return {"status": "closed"}

    def close_all_positions(self):
        self.positions.clear()
        print(f"  [DRY RUN] CLOSE ALL")
        return {"status": "closed"}


def get_executor():
    """Get the appropriate executor based on config."""
    if config.DRY_RUN:
        print("[MODE] Dry Run — no real trades")
        return DryRunExecutor()
    if not config.ALPACA_API_KEY:
        print("[MODE] No Alpaca keys — falling back to Dry Run")
        return DryRunExecutor()
    mode = "PAPER" if config.ALPACA_PAPER else "LIVE"
    print(f"[MODE] Alpaca {mode}")
    return AlpacaExecutor()
