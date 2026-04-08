#!/usr/bin/env python3
"""
Trailing Stop Monitor — runs continuously while positions are open.

Tracks best price per position, closes when price drops 0.5% from peak.
Runs between market open (22:35 KST) and close (04:55 KST).
"""
import os
import sys
import time
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import notifier
from bn_executor import BinanceExecutor

TRAIL_PCT = 0.5   # close when price drops 0.5% from peak
CHECK_INTERVAL = 0.5  # check every 0.5s (API limit 20% — 최대 안전 속도)
SAFETY_CLOSE_HOUR = 19  # 19:55 UTC = 04:55 KST (safety net)
SAFETY_CLOSE_MIN = 55


def run_trailer():
    ex = BinanceExecutor()

    # Track best prices per symbol
    best_prices = {}  # symbol -> best price since entry
    entry_prices = {}  # symbol -> entry price
    directions = {}  # symbol -> "LONG" or "SHORT"

    notifier.send("📡 <b>Trailer Started</b>\nTrailing stop 0.5% 모니터링 시작")

    while True:
        try:
            now_utc = datetime.now(timezone.utc)

            # Safety net: close all at 19:55 UTC (04:55 KST)
            if now_utc.hour == SAFETY_CLOSE_HOUR and now_utc.minute >= SAFETY_CLOSE_MIN:
                positions = ex.get_positions()
                if positions:
                    notifier.send("⏰ <b>장 마감 안전망</b>\n남은 포지션 전량 청산")
                    results = ex.close_all()
                    bal = ex.get_balance()
                    for r in results:
                        if r["success"]:
                            notifier.trade_closed(r["ticker"], directions.get(r["ticker"]+"USDT","?"),
                                entry_prices.get(r["ticker"]+"USDT",0), r["price"], 0, bal)
                    notifier.daily_summary(now_utc.strftime("%Y-%m-%d"), len(results),
                        sum(1 for r in results if r["success"]), 0, bal)
                # Reset and stop until next day
                best_prices.clear()
                entry_prices.clear()
                directions.clear()
                notifier.send("⏹ <b>Trailer 종료</b>\n내일 22:35 KST에 재시작")
                break

            # Get current positions
            positions = ex.get_positions()

            if not positions:
                # No positions — check every minute instead
                time.sleep(60)
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

                # Get current price
                ticker = sym.replace("USDT", "")
                try:
                    current = ex.get_price(ticker)
                except Exception:
                    continue

                if current <= 0:
                    continue

                # Initialize best price
                if sym not in best_prices:
                    best_prices[sym] = current
                    print(f"[{now_utc.strftime('%H:%M:%S')}] {ticker} {dire} tracking started @ ${current:.2f}")

                # Update best price
                if dire == "LONG":
                    if current > best_prices[sym]:
                        best_prices[sym] = current

                    # Check trailing stop
                    drop_from_peak = (best_prices[sym] - current) / best_prices[sym] * 100
                    pnl_pct = (current - entry) / entry * 100

                    if drop_from_peak >= TRAIL_PCT:
                        # TRIGGER: close position
                        print(f"[TRAIL] {ticker} LONG: peak ${best_prices[sym]:.2f} → now ${current:.2f} (drop {drop_from_peak:.2f}%)")
                        result = ex.close_position(ticker)
                        if result["success"]:
                            pnl = (result["price"] - entry) * abs(amt)
                            bal = ex.get_balance()
                            notifier.trade_closed(ticker, dire, entry, result["price"], pnl, bal)
                            print(f"[CLOSED] {ticker} @ ${result['price']:.2f} | PnL: ${pnl:+.2f}")
                            del best_prices[sym]
                        else:
                            notifier.error(f"Trail close failed: {ticker}\n{result['error']}")
                    else:
                        print(f"[{now_utc.strftime('%H:%M:%S')}] {ticker} LONG: ${current:.2f} (peak ${best_prices[sym]:.2f}, drop {drop_from_peak:.2f}%, pnl {pnl_pct:+.2f}%)")

                else:  # SHORT
                    if current < best_prices[sym]:
                        best_prices[sym] = current

                    rise_from_bottom = (current - best_prices[sym]) / best_prices[sym] * 100
                    pnl_pct = (entry - current) / entry * 100

                    if rise_from_bottom >= TRAIL_PCT:
                        print(f"[TRAIL] {ticker} SHORT: bottom ${best_prices[sym]:.2f} → now ${current:.2f} (rise {rise_from_bottom:.2f}%)")
                        result = ex.close_position(ticker)
                        if result["success"]:
                            pnl = (entry - result["price"]) * abs(amt)
                            bal = ex.get_balance()
                            notifier.trade_closed(ticker, dire, entry, result["price"], pnl, bal)
                            print(f"[CLOSED] {ticker} @ ${result['price']:.2f} | PnL: ${pnl:+.2f}")
                            del best_prices[sym]
                        else:
                            notifier.error(f"Trail close failed: {ticker}\n{result['error']}")
                    else:
                        print(f"[{now_utc.strftime('%H:%M:%S')}] {ticker} SHORT: ${current:.2f} (bottom ${best_prices[sym]:.2f}, rise {rise_from_bottom:.2f}%, pnl {pnl_pct:+.2f}%)")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\nTrailer stopped by user")
            break
        except Exception as e:
            notifier.error(f"Trailer error: {e}")
            print(f"[ERROR] {e}")
            time.sleep(60)


if __name__ == "__main__":
    print("=" * 50)
    print("  Trailing Stop Monitor (0.5%)")
    print("  Checking every 30s")
    print("=" * 50)
    run_trailer()
