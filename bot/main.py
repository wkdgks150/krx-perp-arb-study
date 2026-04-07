#!/usr/bin/env python3
"""
Gap FADE Trading Bot — Main Entry Point

Usage:
    python3 main.py scan      # Pre-market: detect signals
    python3 main.py execute   # Market open: enter positions
    python3 main.py close     # Market close: exit all positions
    python3 main.py status    # Show current state
"""
import sys
import os
from datetime import datetime

# Ensure bot/ is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import scanner
import storage
import notifier
from executor import get_executor


def cmd_scan():
    """Pre-market scan: detect gaps and score signals."""
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
        return

    for s in signals:
        icon = "🟢" if s["direction"] == "LONG" else "🔴"
        print(f"  {icon} {s['ticker']} | Gap {s['gap_pct']:+.2f}% | Score {s['score']}/4 | {s['direction']}")
        print(f"     Reasons: {', '.join(s['reasons'])}")
        print(f"     Open: ${s['open_price']:.2f} | Prev Close: ${s['prev_close']:.2f}")
        print()

        # Save to DB
        storage.save_signal(
            date=s["date"], ticker=s["ticker"], direction=s["direction"],
            score=s["score"], reasons=s["reasons"], gap_pct=s["gap_pct"],
        )

    notifier.signal_alert(signals)
    print(f"  → {len(signals)} signal(s) saved. Run 'python3 main.py execute' to trade.")


def cmd_execute():
    """Enter positions for pending signals."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  Gap FADE Executor — {today}")
    print(f"  Mode: {'DRY RUN' if config.DRY_RUN else 'LIVE'}")
    print(f"{'='*60}\n")

    executor = get_executor()

    # Get pending signals
    pending = storage.get_pending_signals(today)
    if not pending:
        print("No pending signals for today.")
        print("Run 'python3 main.py scan' first.")
        return

    # Get capital
    if config.DRY_RUN:
        capital = storage.get_latest_capital() or 1000.0
    else:
        capital = executor.get_buying_power()

    print(f"  Capital: ${capital:,.2f}")
    print(f"  Signals: {len(pending)}")
    print(f"  Per-trade allocation: ${capital * config.MAX_POSITION_PCT / len(pending):,.2f}")
    print()

    per_trade = capital * config.MAX_POSITION_PCT / len(pending)

    for sig in pending:
        ticker = sig["ticker"]
        direction = sig["direction"]
        score = sig["score"]
        gap_pct = sig["gap_pct"]
        reasons = sig["reasons"] if isinstance(sig["reasons"], list) else []

        print(f"  Executing {ticker} {direction} (score {score})...")

        try:
            if direction == "LONG":
                order = executor.market_buy(ticker, notional=per_trade)
            else:
                # For short: sell first (need to handle short selling)
                order = executor.market_sell(ticker, notional=per_trade)

            storage.mark_signal(sig["id"], "executed")

            entry_price = float(order.get("filled_avg_price", 0))
            notifier.trade_opened(ticker, direction, per_trade, entry_price, capital)
            print(f"    ✓ Order placed: {order.get('id', 'n/a')}")

        except Exception as e:
            storage.mark_signal(sig["id"], "failed")
            notifier.error_alert(f"Failed to execute {ticker}: {e}")
            print(f"    ✗ Failed: {e}")

    print(f"\n  → {len(pending)} position(s) opened.")


def cmd_close():
    """Close all positions at market close."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  Gap FADE Closer — {today}")
    print(f"{'='*60}\n")

    executor = get_executor()

    # Get today's executed signals
    today_trades = storage.get_today_trades(today)
    executed_signals = [s for s in storage.get_pending_signals(today)] if not today_trades else []

    # Close all positions
    positions = executor.get_positions()
    if not positions:
        print("No open positions to close.")

    n_trades = 0
    n_wins = 0
    total_pnl = 0.0
    capital = storage.get_latest_capital() or 1000.0
    capital_start = capital

    # For dry run, simulate closes based on today's closing prices
    if config.DRY_RUN:
        import yfinance as yf
        signals = storage._conn().execute(
            "SELECT * FROM signals WHERE date = ? AND status = 'executed'", (today,)
        ).fetchall()

        for sig in signals:
            sig = dict(sig)
            ticker = sig["ticker"]
            direction = sig["direction"]

            # Get today's close price
            df = yf.download(ticker, period="1d", progress=False)
            if df.empty:
                print(f"  [WARN] No data for {ticker}, skipping close")
                continue
            df.columns = df.columns.get_level_values(0)
            close_price = float(df["Close"].iloc[-1])
            open_price = float(df["Open"].iloc[-1])

            per_trade = capital_start * config.MAX_POSITION_PCT / max(len(signals), 1)
            position = per_trade * config.LEVERAGE

            if direction == "LONG":
                ret_pct = (close_price - open_price) / open_price * 100
            else:
                ret_pct = (open_price - close_price) / open_price * 100

            gross = position * (ret_pct / 100)
            fee = position * (config.FEE_PCT / 100)
            net = gross - fee
            capital += net
            n_trades += 1
            if net > 0:
                n_wins += 1
            total_pnl += net

            storage.save_trade(
                signal_id=sig["id"], date=today, ticker=ticker,
                direction=direction, score=sig["score"],
                reasons=sig.get("reasons", ""), gap_pct=sig["gap_pct"],
                entry_price=open_price, exit_price=close_price,
                shares=0, gross_pnl=round(gross, 2), fee=round(fee, 2),
                net_pnl=round(net, 2), capital_before=round(capital_start, 2),
                capital_after=round(capital, 2), platform="dry_run",
            )
            storage.mark_signal(sig["id"], "closed")

            icon = "✅" if net > 0 else "❌"
            print(f"  {icon} {ticker} {direction}: ${open_price:.2f}→${close_price:.2f} P&L ${net:+,.2f} ({ret_pct:+.2f}%)")
            notifier.trade_closed(ticker, direction, open_price, close_price, net, capital)

    else:
        # Live: close all via Alpaca
        result = executor.close_all_positions()
        print(f"  Closed all positions: {result}")
        # TODO: fetch actual fill prices and record trades

    # Daily summary
    if n_trades > 0:
        storage.save_daily_summary(today, capital_start, capital, n_trades, n_wins, total_pnl)
        notifier.daily_summary(today, n_trades, n_wins, total_pnl, capital)

    print(f"\n  Trades: {n_trades} | Wins: {n_wins} | P&L: ${total_pnl:+,.2f}")
    print(f"  Capital: ${capital_start:,.2f} → ${capital:,.2f}")


def cmd_status():
    """Show current bot status."""
    print(f"\n{'='*60}")
    print(f"  Gap FADE Bot Status")
    print(f"{'='*60}")
    print(f"  Mode: {'DRY RUN' if config.DRY_RUN else 'LIVE'}")
    print(f"  Tickers: {', '.join(config.TICKERS)}")
    print(f"  Strategy: FADE, score>={config.MIN_SCORE}, {config.LEVERAGE}x lev")
    print()

    capital = storage.get_latest_capital()
    if capital:
        print(f"  Capital: ${capital:,.2f}")
    else:
        print(f"  Capital: $1,000.00 (default)")

    recent = storage.get_recent_trades(10)
    if recent:
        print(f"\n  Recent trades:")
        for t in recent:
            icon = "✅" if t["net_pnl"] > 0 else "❌"
            print(f"    {icon} {t['date']} {t['ticker']} {t['direction']} "
                  f"${t['entry_price']:.2f}→${t['exit_price']:.2f} "
                  f"P&L ${t['net_pnl']:+,.2f}")
    else:
        print(f"\n  No trades yet.")
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "scan":
        cmd_scan()
    elif cmd == "execute":
        cmd_execute()
    elif cmd == "close":
        cmd_close()
    elif cmd == "status":
        cmd_status()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
