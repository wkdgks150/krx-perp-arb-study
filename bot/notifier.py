"""
Telegram Alert Bot — trade execution & error notifications ONLY

Purpose: Push alerts to phone. Not for monitoring (that's the dashboard).
Sends:
  - Trade opened (entry confirmed)
  - Trade closed (exit + P&L)
  - Errors (order failed, connection lost, balance insufficient)
  - Daily summary
"""
import os
import json
import traceback
from urllib.request import Request, urlopen
from urllib.error import URLError
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

# Load env
for line in open(os.path.join(os.path.dirname(__file__), ".env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def send(message: str):
    if not TOKEN or not CHAT_ID:
        print(f"[TG] {message}")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    body = json.dumps({"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}).encode()
    try:
        req = Request(url, data=body, headers={"Content-Type": "application/json"})
        urlopen(req, timeout=10)
    except URLError as e:
        print(f"[TG ERROR] {e}")


# ─── Trade Alerts ───

def signal_detected(signals: list):
    if not signals:
        return
    lines = ["📡 <b>Signal Detected</b>", ""]
    for s in signals:
        icon = "🟢" if s["direction"] == "LONG" else "🔴"
        lines.append(f"{icon} <b>{s['ticker']}</b> {s['direction']}")
        lines.append(f"   Gap: {s['gap_pct']:+.2f}% | Score: {s['score']}/4")
        lines.append(f"   {', '.join(s['reasons'])}")
        lines.append("")
    send("\n".join(lines))


def trade_opened(ticker, direction, qty, price, capital):
    icon = "🟢" if direction == "LONG" else "🔴"
    send(
        f"{icon} <b>OPENED</b>\n"
        f"{ticker} {direction}\n"
        f"Qty: {qty} @ ${price:.2f}\n"
        f"Value: ${qty * price:,.2f}\n"
        f"Balance: ${capital:,.2f}"
    )


def trade_closed(ticker, direction, entry, exit_price, pnl, balance):
    icon = "✅" if pnl >= 0 else "❌"
    pct = 0
    if entry and entry > 0:
        pct = (exit_price - entry) / entry * 100 if direction == "LONG" else (entry - exit_price) / entry * 100
    send(
        f"{icon} <b>CLOSED</b>\n"
        f"{ticker} {direction}\n"
        f"${entry:.2f} → ${exit_price:.2f} ({pct:+.2f}%)\n"
        f"P&L: <b>${pnl:+,.2f}</b>\n"
        f"Balance: ${balance:,.2f}"
    )


def daily_summary(date, n_trades, n_wins, total_pnl, capital):
    wr = n_wins / n_trades * 100 if n_trades > 0 else 0
    icon = "📈" if total_pnl >= 0 else "📉"
    send(
        f"{icon} <b>Daily Summary</b> {date}\n"
        f"Trades: {n_trades} | Wins: {n_wins} ({wr:.0f}%)\n"
        f"P&L: <b>${total_pnl:+,.2f}</b>\n"
        f"Balance: ${capital:,.2f}"
    )


def no_signals():
    send("📊 <b>Scan Complete</b>\nNo signals today.")


# ─── Error Alerts ───

def error(msg, exc=None):
    tb = ""
    if exc:
        tb = f"\n<pre>{traceback.format_exception_only(type(exc), exc)[0].strip()}</pre>"
    send(f"🚨 <b>ERROR</b>\n{msg}{tb}")


def balance_low(balance, required):
    send(
        f"⚠️ <b>Low Balance</b>\n"
        f"Available: ${balance:.2f}\n"
        f"Required: ${required:.2f}\n"
        f"Bot paused."
    )


def connection_error(platform, exc):
    send(
        f"🔌 <b>Connection Failed</b>\n"
        f"Platform: {platform}\n"
        f"<pre>{str(exc)[:200]}</pre>"
    )


def bot_started():
    send("🤖 <b>Bot Started</b>\nGap FADE Bot is running.")


def bot_stopped(reason="manual"):
    send(f"⏹ <b>Bot Stopped</b>\nReason: {reason}")


# ─── Signal alerts (legacy compat) ───
def signal_alert(signals):
    if signals:
        signal_detected(signals)
    else:
        no_signals()
