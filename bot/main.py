#!/usr/bin/env python3
"""
Gap FADE Trading Bot — Binance Futures (REAL)

Usage:
    python3 main.py scan      # Scan gaps + save signals
    python3 main.py execute   # Enter positions (LONG or SHORT)
    python3 main.py close     # Close all positions
    python3 main.py status    # Show account + positions
    python3 main.py run       # scan + execute in one shot
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import scanner
import storage
import notifier
from bn_executor import BinanceExecutor


def cmd_scan():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  Gap FADE Scanner — {today}")
    print(f"  Tickers: {', '.join(config.TICKERS)}")
    print(f"  Score >= {config.MIN_SCORE}, Leverage {config.LEVERAGE}x")
    print(f"{'='*60}\n")

    signals = scanner.scan_all()

    if not signals:
        print("  No signals today.")
        notifier.signal_alert([])
        return []

    for s in signals:
        icon = "+" if s["direction"] == "LONG" else "-"
        print(f"  [{icon}] {s['ticker']} | Gap {s['gap_pct']:+.2f}% | Score {s['score']}/4 | {s['direction']}")
        print(f"      {', '.join(s['reasons'])}")
        storage.save_signal(s["date"], s["ticker"], s["direction"], s["score"], s["reasons"], s["gap_pct"])

    notifier.signal_alert(signals)
    return signals


def cmd_execute():
    today = datetime.now().strftime("%Y-%m-%d")
    ex = BinanceExecutor()
    capital = ex.get_balance()

    print(f"\n{'='*60}")
    print(f"  Gap FADE Executor — {today}")
    print(f"  Balance: ${capital:.2f}")
    print(f"{'='*60}\n")

    # Get all pending signals (any date)
    import sqlite3
    conn = sqlite3.connect(str(config.DB_PATH))
    rows = conn.execute("SELECT * FROM signals WHERE status='pending' ORDER BY score DESC").fetchall()

    if not rows:
        print("  No pending signals.")
        return

    n = len(rows)
    per_trade = capital * config.MAX_POSITION_PCT / n * config.LEVERAGE
    print(f"  Signals: {n}")
    print(f"  Per-trade position: ${per_trade:.2f} ({config.LEVERAGE}x on ${capital * config.MAX_POSITION_PCT / n:.2f})")
    print()

    for r in rows:
        sig_id, ts, date, ticker, direction, score, reasons, gap_pct, status = r

        # Set leverage
        try:
            ex.set_leverage(ticker, int(config.LEVERAGE))
        except Exception:
            pass

        print(f"  {ticker} {direction} (score {score})...")

        try:
            if direction == "LONG":
                result = ex.long(ticker, per_trade)
            else:
                result = ex.short(ticker, per_trade)

            if result["success"]:
                conn.execute("UPDATE signals SET status='executed' WHERE id=?", (sig_id,))
                conn.commit()
                print(f"    OK  {result['side']} {result['qty']} {ticker} @ ${result['price']:.2f}")
                notifier.trade_opened(ticker, direction, result["qty"], result["price"], capital)
            else:
                conn.execute("UPDATE signals SET status='failed' WHERE id=?", (sig_id,))
                conn.commit()
                print(f"    FAIL {result['error']}")
        except Exception as e:
            conn.execute("UPDATE signals SET status='failed' WHERE id=?", (sig_id,))
            conn.commit()
            print(f"    ERROR {e}")


def cmd_close():
    today = datetime.now().strftime("%Y-%m-%d")
    ex = BinanceExecutor()

    print(f"\n{'='*60}")
    print(f"  Gap FADE Closer — {today}")
    print(f"{'='*60}\n")

    balance_before = ex.get_balance()
    positions = ex.get_positions()

    if not positions:
        print("  No positions to close.")
        return

    for p in positions:
        sym = p["symbol"]
        amt = float(p["positionAmt"])
        entry = float(p["entryPrice"])
        pnl = float(p["unrealizedProfit"])
        direction = "LONG" if amt > 0 else "SHORT"
        print(f"  {sym}: {direction} {abs(amt)} @ ${entry:.2f} | PnL: ${pnl:+.2f}")

    print()
    results = ex.close_all()
    for r in results:
        if r["success"]:
            print(f"  Closed {r['ticker']} {r['qty']} @ ${r['price']:.2f}")
        else:
            print(f"  Failed: {r['error']}")

    import time
    time.sleep(2)
    balance_after = ex.get_balance()
    pnl = balance_after - balance_before
    print(f"\n  Balance: ${balance_before:.2f} -> ${balance_after:.2f} (P&L: ${pnl:+.2f})")
    notifier.daily_summary(today, len(results), sum(1 for r in results if r.get("success")), pnl, balance_after)


def cmd_status():
    ex = BinanceExecutor()
    bal = ex.get_balance()

    print(f"\n{'='*60}")
    print(f"  Gap FADE Bot — Binance Futures")
    print(f"{'='*60}")
    print(f"  Balance: ${bal:.2f}")
    print(f"  Tickers: {', '.join(config.TICKERS)}")
    print(f"  Strategy: FADE, score>={config.MIN_SCORE}, {config.LEVERAGE}x")

    positions = ex.get_positions()
    if positions:
        print(f"\n  Open Positions:")
        for p in positions:
            amt = float(p["positionAmt"])
            entry = float(p["entryPrice"])
            pnl = float(p["unrealizedProfit"])
            d = "LONG" if amt > 0 else "SHORT"
            print(f"    {p['symbol']}: {d} {abs(amt)} @ ${entry:.2f} | PnL: ${pnl:+.2f}")
    else:
        print(f"\n  No open positions")

    recent = storage.get_recent_trades(5)
    if recent:
        print(f"\n  Recent trades:")
        for t in recent:
            icon = "+" if t["net_pnl"] > 0 else "-"
            print(f"    [{icon}] {t['date']} {t['ticker']} {t['direction']} ${t['net_pnl']:+.2f}")
    print()


def cmd_run():
    signals = cmd_scan()
    if signals:
        cmd_execute()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmds = {"scan": cmd_scan, "execute": cmd_execute, "close": cmd_close, "status": cmd_status, "run": cmd_run}
    cmd = sys.argv[1].lower()
    if cmd in cmds:
        cmds[cmd]()
    else:
        print(f"Unknown: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
