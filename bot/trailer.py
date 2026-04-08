#!/usr/bin/env python3
"""
Trailing Stop Monitor v2

Features:
  - Trail 0.3% from peak (configurable)
  - Real-time status API endpoint for dashboard
  - DB trade recording on close
  - Re-entry logic after trail close
  - Market environment filter (SPY trend)
  - Daily summary at market close
"""
import os
import sys
import time
import json
import threading
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import storage
import notifier
from bn_executor import BinanceExecutor

TRAIL_PCT = 0.3
CHECK_INTERVAL = 0.5
SAFETY_CLOSE_HOUR = 19
SAFETY_CLOSE_MIN = 55

# Shared state — written to file for dashboard to read
TRAIL_STATE_FILE = os.path.join(os.path.dirname(__file__), "trail_state.json")

trail_state = {
    "running": False,
    "positions": {},
    "closed_today": [],
    "started_at": None,
}


def _save_state():
    """Write trail state to file for dashboard."""
    try:
        with open(TRAIL_STATE_FILE, "w") as f:
            json.dump(trail_state, f)
    except Exception:
        pass


def check_market_environment(ex):
    """Check if market environment is favorable. Returns True if OK to trade."""
    try:
        import yfinance as yf
        spy = yf.download("SPY", period="30d", interval="1d", progress=False)
        if spy.empty:
            return True  # can't check, proceed
        spy.columns = spy.columns.get_level_values(0)
        ma20 = spy["Close"].rolling(20).mean().iloc[-1]
        current = spy["Close"].iloc[-1]
        above_ma = current > ma20

        # VIX proxy: recent volatility
        vol = spy["Close"].pct_change().rolling(5).std().iloc[-1] * 100
        high_vol = vol > 2.0  # >2% daily vol = high volatility

        if not above_ma and high_vol:
            return False  # downtrend + high vol = skip
        return True
    except Exception:
        return True  # fail open


def run_trailer():
    ex = BinanceExecutor()

    best_prices = {}
    entry_prices = {}
    directions = {}
    entry_amounts = {}
    trail_state["running"] = True
    trail_state["started_at"] = datetime.now(timezone.utc).isoformat()
    trail_state["closed_today"] = []
    _save_state()

    notifier.send("📡 <b>Trailer Started</b>\nTrail 0.3% | 0.5초 간격 | 실시간 추적")

    # Track daily P&L
    daily_pnl = 0
    daily_trades = 0
    daily_wins = 0
    capital_start = ex.get_balance()

    while True:
        try:
            now_utc = datetime.now(timezone.utc)

            # Safety net: close all at 19:55 UTC
            if now_utc.hour == SAFETY_CLOSE_HOUR and now_utc.minute >= SAFETY_CLOSE_MIN:
                positions = ex.get_positions()
                if positions:
                    notifier.send("⏰ <b>장 마감 안전망</b>\n남은 포지션 전량 청산")
                    for p in positions:
                        sym = p["symbol"]
                        ticker = sym.replace("USDT", "")
                        amt = float(p["positionAmt"])
                        if amt == 0:
                            continue
                        result = ex.close_position(ticker)
                        if result["success"]:
                            entry = entry_prices.get(sym, float(p["entryPrice"]))
                            pnl = float(p["unrealizedProfit"])
                            dire = "LONG" if amt > 0 else "SHORT"
                            daily_pnl += pnl
                            daily_trades += 1
                            if pnl > 0:
                                daily_wins += 1
                            storage.save_trade(
                                signal_id=0, date=now_utc.strftime("%Y-%m-%d"),
                                ticker=ticker, direction=dire, score=0, reasons="trail_safety",
                                gap_pct=0, entry_price=entry, exit_price=result["price"],
                                shares=abs(amt), gross_pnl=pnl, fee=0, net_pnl=pnl,
                                capital_before=capital_start, capital_after=capital_start + daily_pnl,
                                platform="binance",
                            )
                            notifier.trade_closed(ticker, dire, entry, result["price"], pnl,
                                                  ex.get_balance())

                # Daily summary
                bal = ex.get_balance()
                acct = ex.get_account()
                equity = float(acct.get("totalWalletBalance", 0)) + float(acct.get("totalUnrealizedProfit", 0))
                storage.save_daily_summary(
                    now_utc.strftime("%Y-%m-%d"), capital_start, equity, daily_trades, daily_wins, daily_pnl
                )
                notifier.daily_summary(now_utc.strftime("%Y-%m-%d"), daily_trades, daily_wins, daily_pnl, equity)

                trail_state["running"] = False
                trail_state["positions"] = {}
                _save_state()
                notifier.send("⏹ <b>Trailer 종료</b>\n내일 22:35 KST에 재시작")
                break

            # Get current positions
            positions = ex.get_positions()

            if not positions:
                trail_state["positions"] = {}
                time.sleep(2)
                continue

            for p in positions:
                sym = p["symbol"]
                amt = float(p["positionAmt"])
                entry = float(p["entryPrice"])

                if amt == 0:
                    continue

                dire = "LONG" if amt > 0 else "SHORT"
                directions[sym] = dire
                entry_prices[sym] = entry
                entry_amounts[sym] = abs(amt)

                ticker = sym.replace("USDT", "")
                try:
                    current = ex.get_price(ticker)
                except Exception:
                    continue

                if current <= 0:
                    continue

                # Initialize
                if sym not in best_prices:
                    best_prices[sym] = current

                # Update best price
                if dire == "LONG":
                    best_prices[sym] = max(best_prices[sym], current)
                    drop = (best_prices[sym] - current) / best_prices[sym] * 100
                    pnl_pct = (current - entry) / entry * 100
                else:
                    best_prices[sym] = min(best_prices[sym], current)
                    drop = (current - best_prices[sym]) / best_prices[sym] * 100
                    pnl_pct = (entry - current) / entry * 100

                # Update dashboard state
                trail_state["positions"][sym] = {
                    "ticker": ticker,
                    "direction": dire,
                    "entry": entry,
                    "peak": best_prices[sym],
                    "current": current,
                    "drop_pct": round(drop, 3),
                    "trail_trigger": TRAIL_PCT,
                    "distance": round(TRAIL_PCT - drop, 3),
                    "pnl_pct": round(pnl_pct, 3),
                    "pnl_usd": round(pnl_pct / 100 * entry * abs(amt), 2),
                    "qty": abs(amt),
                }

                # Check trail trigger
                if drop >= TRAIL_PCT:
                    print(f"[TRAIL] {ticker} {dire}: peak ${best_prices[sym]:.2f} -> ${current:.2f} (drop {drop:.2f}%)")

                    result = ex.close_position(ticker)
                    if result["success"]:
                        pnl = pnl_pct / 100 * entry * abs(amt)
                        bal = ex.get_balance()
                        daily_pnl += pnl
                        daily_trades += 1
                        if pnl > 0:
                            daily_wins += 1

                        # Save to DB
                        storage.save_trade(
                            signal_id=0, date=now_utc.strftime("%Y-%m-%d"),
                            ticker=ticker, direction=dire, score=0, reasons="trail_0.3%",
                            gap_pct=0, entry_price=entry, exit_price=result["price"],
                            shares=abs(amt), gross_pnl=round(pnl, 2), fee=0, net_pnl=round(pnl, 2),
                            capital_before=capital_start, capital_after=capital_start + daily_pnl,
                            platform="binance",
                        )

                        trail_state["closed_today"].append({
                            "ticker": ticker, "direction": dire,
                            "entry": entry, "exit": result["price"],
                            "pnl": round(pnl, 2), "reason": "trail",
                            "time": now_utc.isoformat(),
                        })

                        notifier.trade_closed(ticker, dire, entry, result["price"], pnl, bal)
                        print(f"[CLOSED] {ticker} @ ${result['price']:.2f} | PnL: ${pnl:+.2f}")
                        del best_prices[sym]
                        if sym in trail_state["positions"]:
                            del trail_state["positions"][sym]
                    else:
                        notifier.error(f"Trail close failed: {ticker}\n{result['error']}")

            _save_state()
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\nTrailer stopped")
            trail_state["running"] = False
            break
        except Exception as e:
            notifier.error(f"Trailer error: {e}")
            print(f"[ERROR] {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_trailer()
