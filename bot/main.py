#!/usr/bin/env python3
"""
Gap FADE Trading Bot — Binance Futures (REAL)

Usage:
    python3 main.py scan      # Scan gaps + save signals
    python3 main.py execute   # Enter positions (LONG or SHORT)
    python3 main.py close     # Close all positions
    python3 main.py status    # Show account + positions
    python3 main.py run       # scan + execute in one shot
    python3 main.py dash      # Start live dashboard (port 8001)
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

    try:
        signals = scanner.scan_all()
    except Exception as e:
        notifier.error("Scanner crashed", e)
        raise

    if not signals:
        print("  No signals today.")
        notifier.no_signals()
        return []

    for s in signals:
        icon = "+" if s["direction"] == "LONG" else "-"
        print(f"  [{icon}] {s['ticker']} | Gap {s['gap_pct']:+.2f}% | Score {s['score']}/4 | {s['direction']}")
        print(f"      {', '.join(s['reasons'])}")
        storage.save_signal(s["date"], s["ticker"], s["direction"], s["score"], s["reasons"], s["gap_pct"])

    notifier.signal_detected(signals)
    return signals


def cmd_execute():
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        ex = BinanceExecutor()
        capital = ex.get_balance()
    except Exception as e:
        notifier.connection_error("Binance", e)
        raise

    print(f"\n{'='*60}")
    print(f"  Gap FADE Executor — {today}")
    print(f"  Balance: ${capital:.2f}")
    print(f"{'='*60}\n")

    # Check minimum balance
    min_required = 10.0
    if capital < min_required:
        notifier.balance_low(capital, min_required)
        print(f"  Balance too low: ${capital:.2f} < ${min_required}")
        return

    # Get all pending signals
    import sqlite3
    conn = sqlite3.connect(str(config.DB_PATH))
    rows = conn.execute("SELECT * FROM signals WHERE status='pending' ORDER BY score DESC").fetchall()

    if not rows:
        print("  No pending signals.")
        return

    n = len(rows)
    per_trade_capital = capital * config.MAX_POSITION_PCT / n
    per_trade_position = per_trade_capital * config.LEVERAGE
    print(f"  Signals: {n}")
    print(f"  Per-trade: ${per_trade_capital:.2f} x {config.LEVERAGE}x = ${per_trade_position:.2f}")
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
                result = ex.long(ticker, per_trade_position)
            else:
                result = ex.short(ticker, per_trade_position)

            if result["success"]:
                conn.execute("UPDATE signals SET status='executed' WHERE id=?", (sig_id,))
                conn.commit()
                print(f"    OK  {result['side']} {result['qty']} {ticker} @ ${result['price']:.2f}")
                notifier.trade_opened(ticker, direction, result["qty"], result["price"], capital)
            else:
                conn.execute("UPDATE signals SET status='failed' WHERE id=?", (sig_id,))
                conn.commit()
                err_msg = result["error"]
                print(f"    FAIL {err_msg}")
                notifier.error(f"Order failed: {ticker} {direction}\n{err_msg}")

        except Exception as e:
            conn.execute("UPDATE signals SET status='failed' WHERE id=?", (sig_id,))
            conn.commit()
            print(f"    ERROR {e}")
            notifier.error(f"Order exception: {ticker} {direction}", e)


def cmd_close():
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        ex = BinanceExecutor()
    except Exception as e:
        notifier.connection_error("Binance", e)
        raise

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
    n_success = 0
    for r in results:
        if r["success"]:
            n_success += 1
            print(f"  Closed {r['ticker']} {r['qty']} @ ${r['price']:.2f}")
            # Find entry price for P&L notification
            for p in positions:
                if r["ticker"] in p["symbol"]:
                    entry = float(p["entryPrice"])
                    pnl = float(p["unrealizedProfit"])
                    direction = "LONG" if float(p["positionAmt"]) > 0 else "SHORT"
                    notifier.trade_closed(r["ticker"], direction, entry, r["price"], pnl, balance_before + pnl)
        else:
            print(f"  Failed: {r['error']}")
            notifier.error(f"Close failed: {r.get('ticker','?')}\n{r['error']}")

    import time
    time.sleep(2)
    balance_after = ex.get_balance()
    pnl = balance_after - balance_before
    print(f"\n  Balance: ${balance_before:.2f} -> ${balance_after:.2f} (P&L: ${pnl:+.2f})")
    notifier.daily_summary(today, len(results), n_success, pnl, balance_after)


def cmd_status():
    try:
        ex = BinanceExecutor()
        bal = ex.get_balance()
    except Exception as e:
        print(f"Connection error: {e}")
        return

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
    print()


def cmd_run():
    """Scan + Execute + Trail in one shot."""
    notifier.bot_started()
    try:
        signals = cmd_scan()
        if signals:
            cmd_execute()
            # Start trailing stop monitor
            print("\n  Starting trailing stop monitor...")
            from trailer import run_trailer
            run_trailer()
    except Exception as e:
        notifier.error("Bot run failed", e)
        raise


def cmd_trail():
    """Start trailing stop monitor for existing positions."""
    from trailer import run_trailer
    run_trailer()


def cmd_dash():
    """Start live monitoring dashboard on port 8001."""
    from live_dashboard import app
    import uvicorn
    print("Starting Live Dashboard on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmds = {
        "scan": cmd_scan, "execute": cmd_execute, "close": cmd_close,
        "status": cmd_status, "run": cmd_run, "trail": cmd_trail, "dash": cmd_dash,
    }
    cmd = sys.argv[1].lower()
    if cmd in cmds:
        cmds[cmd]()
    else:
        print(f"Unknown: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
