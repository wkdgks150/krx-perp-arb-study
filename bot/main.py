#!/usr/bin/env python3
"""
Gap FADE Trading Bot — Hyperliquid Live

Usage:
    python3 main.py scan      # Scan gaps + save signals
    python3 main.py execute   # Enter positions for signals
    python3 main.py close     # Close all stock positions
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
from hl_executor import HyperliquidExecutor


def cmd_scan():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  Gap FADE Scanner — {today}")
    print(f"  Tickers: {', '.join(config.TICKERS)}")
    print(f"  Filters: gap>{config.GAP_THRESHOLD}% body>{config.BODY_THRESHOLD}% score>={config.MIN_SCORE}")
    print(f"{'='*60}\n")

    signals = scanner.scan_all()

    if not signals:
        print("No signals today.")
        notifier.signal_alert([])
        return []

    for s in signals:
        icon = "+" if s["direction"] == "LONG" else "-"
        print(f"  [{icon}] {s['ticker']} | Gap {s['gap_pct']:+.2f}% | Score {s['score']}/4 | {s['direction']}")
        print(f"      Reasons: {', '.join(s['reasons'])}")
        storage.save_signal(s["date"], s["ticker"], s["direction"], s["score"], s["reasons"], s["gap_pct"])

    notifier.signal_alert(signals)
    return signals


def cmd_execute():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  Gap FADE Executor — {today}")
    print(f"{'='*60}\n")

    ex = HyperliquidExecutor()
    capital = ex.get_balance()
    print(f"  USDC Balance: ${capital:.2f}")

    pending = storage.get_pending_signals(today)
    if not pending:
        print("  No pending signals. Run 'scan' first.")
        return

    n = len(pending)
    per_trade = capital * config.MAX_POSITION_PCT / n
    print(f"  Signals: {n}")
    print(f"  Per-trade: ${per_trade:.2f}")
    print()

    for sig in pending:
        ticker = sig["ticker"]
        direction = sig["direction"]
        print(f"  {ticker} {direction} (score {sig['score']})...")

        try:
            if direction == "LONG":
                result = ex.buy(ticker, per_trade)
            else:
                # SHORT on spot = we'd need to have borrowed shares
                # For now: skip short signals on spot (can only long)
                print(f"    SKIP — spot market, SHORT not available")
                storage.mark_signal(sig["id"], "skipped")
                continue

            if result["success"]:
                storage.mark_signal(sig["id"], "executed")
                print(f"    OK  {result['side']} {result['sz']} {ticker} @ ${result['price']:.2f} (${result['value']:.2f})")
                notifier.trade_opened(ticker, direction, result["sz"], result["price"], capital)
            else:
                storage.mark_signal(sig["id"], "failed")
                print(f"    FAIL {result['error']}")

        except Exception as e:
            storage.mark_signal(sig["id"], "failed")
            print(f"    ERROR {e}")


def cmd_close():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  Gap FADE Closer — {today}")
    print(f"{'='*60}\n")

    ex = HyperliquidExecutor()
    balances = ex.get_all_balances()
    usdc_before = balances.get("USDC", 0)

    print(f"  USDC: ${usdc_before:.2f}")
    stocks = {k: v for k, v in balances.items() if k != "USDC" and v > 0}
    if not stocks:
        print("  No stock positions to close.")
        return

    for ticker, sz in stocks.items():
        price = ex.get_price(ticker) if ticker in ex.STOCK_MARKETS else 0
        print(f"  {ticker}: {sz} shares (~${sz * price:.2f})")

    print()
    results = ex.sell_all()
    for r in results:
        if r["success"]:
            print(f"  SOLD {r['sz']} {r['ticker']} @ ${r['price']:.2f} (${r['value']:.2f})")
        else:
            print(f"  FAIL {r.get('ticker','?')}: {r['error']}")

    import time
    time.sleep(2)
    usdc_after = ex.get_balance()
    pnl = usdc_after - usdc_before
    print(f"\n  USDC: ${usdc_before:.2f} -> ${usdc_after:.2f} (P&L: ${pnl:+.2f})")
    notifier.daily_summary(today, len(results), sum(1 for r in results if r["success"]), pnl, usdc_after)


def cmd_status():
    print(f"\n{'='*60}")
    print(f"  Gap FADE Bot — Status")
    print(f"{'='*60}")

    ex = HyperliquidExecutor()
    balances = ex.get_all_balances()

    print(f"  Wallet: {ex.wallet[:10]}...{ex.wallet[-6:]}")
    print(f"  USDC: ${balances.get('USDC', 0):.2f}")
    print(f"  Tickers: {', '.join(config.TICKERS)}")
    print(f"  Strategy: FADE, score>={config.MIN_SCORE}, {config.LEVERAGE}x")
    print()

    stocks = {k: v for k, v in balances.items() if k != "USDC" and v > 0}
    if stocks:
        print("  Positions:")
        for ticker, sz in stocks.items():
            try:
                price = ex.get_price(ticker)
                print(f"    {ticker}: {sz} shares @ ${price:.2f} = ${sz * price:.2f}")
            except Exception:
                print(f"    {ticker}: {sz} shares")
    else:
        print("  No open positions")

    recent = storage.get_recent_trades(5)
    if recent:
        print(f"\n  Recent trades:")
        for t in recent:
            icon = "+" if t["net_pnl"] > 0 else "-"
            print(f"    [{icon}] {t['date']} {t['ticker']} {t['direction']} P&L ${t['net_pnl']:+.2f}")
    print()


def cmd_run():
    """Scan + Execute in one shot."""
    signals = cmd_scan()
    if signals:
        cmd_execute()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    cmds = {"scan": cmd_scan, "execute": cmd_execute, "close": cmd_close, "status": cmd_status, "run": cmd_run}

    if cmd in cmds:
        cmds[cmd]()
    else:
        print(f"Unknown: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
