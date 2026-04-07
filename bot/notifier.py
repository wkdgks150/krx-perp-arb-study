"""
Telegram notification sender
"""
import json
from urllib.request import Request, urlopen
from urllib.error import URLError
import config


def send(message: str):
    """Send message via Telegram bot."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print(f"[NOTIFY] (no Telegram config) {message}")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    body = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        req = Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        urlopen(req, timeout=10)
    except URLError as e:
        print(f"[NOTIFY ERROR] {e}")


def signal_alert(signals: list[dict]):
    """Send signal detection alert."""
    if not signals:
        send("📊 <b>Gap FADE Scan</b>\nNo signals today.")
        return

    lines = ["📊 <b>Gap FADE Signals</b>", ""]
    for s in signals:
        icon = "🟢 LONG" if s["direction"] == "LONG" else "🔴 SHORT"
        lines.append(f"<b>{s['ticker']}</b> | {icon}")
        lines.append(f"  Gap: {s['gap_pct']:+.2f}% | Score: {s['score']}/4")
        lines.append(f"  {', '.join(s['reasons'])}")
        lines.append("")
    send("\n".join(lines))


def trade_opened(ticker, direction, shares, price, capital):
    icon = "🟢" if direction == "LONG" else "🔴"
    send(
        f"{icon} <b>OPENED</b> {ticker}\n"
        f"Dir: {direction} | Shares: {shares}\n"
        f"Entry: ${price:.2f}\n"
        f"Capital: ${capital:,.2f}"
    )


def trade_closed(ticker, direction, entry, exit_price, pnl, capital):
    icon = "✅" if pnl >= 0 else "❌"
    send(
        f"{icon} <b>CLOSED</b> {ticker}\n"
        f"Dir: {direction}\n"
        f"Entry: ${entry:.2f} → Exit: ${exit_price:.2f}\n"
        f"P&L: ${pnl:+,.2f}\n"
        f"Capital: ${capital:,.2f}"
    )


def daily_summary(date, n_trades, n_wins, total_pnl, capital):
    wr = n_wins / n_trades * 100 if n_trades > 0 else 0
    icon = "📈" if total_pnl >= 0 else "📉"
    send(
        f"{icon} <b>Daily Summary</b> {date}\n"
        f"Trades: {n_trades} | Wins: {n_wins} ({wr:.0f}%)\n"
        f"P&L: ${total_pnl:+,.2f}\n"
        f"Capital: ${capital:,.2f}"
    )


def error_alert(msg):
    send(f"🚨 <b>ERROR</b>\n{msg}")
