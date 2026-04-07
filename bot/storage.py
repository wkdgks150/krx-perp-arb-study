"""
SQLite trade storage
"""
import sqlite3
import json
from datetime import datetime
from config import DB_PATH


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT (datetime('now')),
                date TEXT,
                ticker TEXT,
                direction TEXT,
                score INTEGER,
                reasons TEXT,
                gap_pct REAL,
                status TEXT DEFAULT 'pending'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                timestamp TEXT DEFAULT (datetime('now')),
                date TEXT,
                ticker TEXT,
                direction TEXT,
                score INTEGER,
                reasons TEXT,
                gap_pct REAL,
                entry_price REAL,
                exit_price REAL,
                shares REAL,
                gross_pnl REAL,
                fee REAL,
                net_pnl REAL,
                capital_before REAL,
                capital_after REAL,
                platform TEXT,
                FOREIGN KEY (signal_id) REFERENCES signals(id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                capital_start REAL,
                capital_end REAL,
                n_trades INTEGER,
                n_wins INTEGER,
                total_pnl REAL
            )
        """)


def save_signal(date, ticker, direction, score, reasons, gap_pct):
    with _conn() as c:
        c.execute(
            "INSERT INTO signals (date, ticker, direction, score, reasons, gap_pct) VALUES (?,?,?,?,?,?)",
            (date, ticker, direction, score, json.dumps(reasons), gap_pct),
        )
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_pending_signals(date):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM signals WHERE date = ? AND status = 'pending'", (date,)
        ).fetchall()
        return [dict(r) for r in rows]


def mark_signal(signal_id, status):
    with _conn() as c:
        c.execute("UPDATE signals SET status = ? WHERE id = ?", (status, signal_id))


def save_trade(signal_id, date, ticker, direction, score, reasons, gap_pct,
               entry_price, exit_price, shares, gross_pnl, fee, net_pnl,
               capital_before, capital_after, platform):
    with _conn() as c:
        c.execute("""
            INSERT INTO trades (signal_id, date, ticker, direction, score, reasons, gap_pct,
                                entry_price, exit_price, shares, gross_pnl, fee, net_pnl,
                                capital_before, capital_after, platform)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (signal_id, date, ticker, direction, score, json.dumps(reasons), gap_pct,
              entry_price, exit_price, shares, gross_pnl, fee, net_pnl,
              capital_before, capital_after, platform))


def save_daily_summary(date, capital_start, capital_end, n_trades, n_wins, total_pnl):
    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO daily_summary (date, capital_start, capital_end, n_trades, n_wins, total_pnl)
            VALUES (?,?,?,?,?,?)
        """, (date, capital_start, capital_end, n_trades, n_wins, total_pnl))


def get_latest_capital():
    with _conn() as c:
        row = c.execute(
            "SELECT capital_end FROM daily_summary ORDER BY date DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None


def get_today_trades(date):
    with _conn() as c:
        rows = c.execute("SELECT * FROM trades WHERE date = ?", (date,)).fetchall()
        return [dict(r) for r in rows]


def get_recent_trades(n=20):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM trades ORDER BY date DESC, id DESC LIMIT ?", (n,)
        ).fetchall()
        return [dict(r) for r in rows]


# Auto-init on import
init_db()
