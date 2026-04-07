"""
Gap FADE Backtesting API + Dashboard Server
"""
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Gap FADE Backtest")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TICKERS = ["GOOGL", "NVDA", "TSLA", "SPY", "AAPL", "MSFT", "META", "AMZN"]
_cache = {}  # type: dict


def fetch_data(ticker: str) -> pd.DataFrame:
    if ticker in _cache:
        return _cache[ticker]
    df = yf.download(ticker, start="2025-07-01", end=datetime.now().strftime("%Y-%m-%d"), interval="1d", progress=False)
    df.columns = df.columns.get_level_values(0)
    df["Prev_Close"] = df["Close"].shift(1)
    df["Prev_Open"] = df["Open"].shift(1)
    df["Gap_Pct"] = (df["Open"] - df["Prev_Close"]) / df["Prev_Close"] * 100
    df["Gap_Abs"] = abs(df["Gap_Pct"])
    df["Prev_Body"] = abs((df["Prev_Close"] - df["Prev_Open"]) / df["Prev_Open"] * 100)
    df["Prev_Body_Dir"] = np.sign(df["Prev_Close"] - df["Prev_Open"])
    df["Gap_Dir"] = np.sign(df["Gap_Pct"])
    df["Prev_Body_Matches_Gap"] = (df["Prev_Body_Dir"] == df["Gap_Dir"]).astype(int)
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA_Dist"] = abs((df["Open"] - df["MA20"]) / df["MA20"] * 100)
    df["Prev_Gap"] = df["Gap_Pct"].shift(1)
    df["Consec"] = (np.sign(df["Gap_Pct"]) == np.sign(df["Prev_Gap"])).astype(int)
    df = df.dropna(subset=["Gap_Pct", "MA20"])
    _cache[ticker] = df
    return df


def _score_row(row, gap_th, body_th, consec, ma_dist):
    """Score a single row. Returns (score, reasons) or None."""
    if row["Gap_Abs"] < 0.3:
        return None
    score = 0
    reasons = []
    if row["Gap_Abs"] >= gap_th:
        score += 1
        reasons.append(f"gap:{row['Gap_Pct']:+.2f}%")
    if row["Prev_Body"] >= body_th and row["Prev_Body_Matches_Gap"]:
        score += 1
        reasons.append(f"body:{row['Prev_Body']:.1f}%")
    if consec and row["Consec"]:
        score += 1
        reasons.append("consec")
    if row["MA_Dist"] >= ma_dist:
        score += 1
        reasons.append(f"ma:{row['MA_Dist']:.1f}%")
    return score, reasons


def run_backtest(
    tickers,
    gap_th: float = 0.5,
    body_th: float = 1.0,
    consec: bool = True,
    ma_dist: float = 0.0,
    min_score: int = 3,
    leverage: float = 5.0,
    capital: float = 1000.0,
    fee_pct: float = 0.07,
) -> dict:
    initial_capital = capital
    trades = []
    equity_curve = []
    max_cap = capital
    max_dd = 0.0

    # Load all data
    all_candles = {}
    for ticker in tickers:
        all_candles[ticker] = fetch_data(ticker)

    # Collect ALL signals across all tickers with their dates
    all_signals = []
    for ticker in tickers:
        df = all_candles[ticker]
        for idx, row in df.iterrows():
            result = _score_row(row, gap_th, body_th, consec, ma_dist)
            if result is None:
                continue
            score, reasons = result
            if score < min_score:
                continue
            direction = "SHORT" if row["Gap_Pct"] > 0 else "LONG"
            entry_price = float(row["Open"])
            exit_price = float(row["Close"])
            if direction == "SHORT":
                ret_pct = (entry_price - exit_price) / entry_price * 100
            else:
                ret_pct = (exit_price - entry_price) / entry_price * 100
            all_signals.append({
                "date": idx.strftime("%Y-%m-%d"),
                "ticker": ticker,
                "direction": direction,
                "score": score,
                "reasons": reasons,
                "gap_pct": float(row["Gap_Pct"]),
                "entry": entry_price,
                "exit": exit_price,
                "ret_pct": ret_pct,
            })

    # Sort by date, then by score descending (best signals first each day)
    all_signals.sort(key=lambda x: (x["date"], -x["score"]))

    # Group signals by date → simultaneous portfolio execution
    from itertools import groupby
    for date, day_signals_iter in groupby(all_signals, key=lambda x: x["date"]):
        if capital <= 0:
            break
        day_signals = list(day_signals_iter)
        n = len(day_signals)

        # Split capital equally across all signals for the day
        per_trade_capital = capital / n
        day_pnl = 0.0

        for sig in day_signals:
            position = per_trade_capital * leverage
            gross = position * (sig["ret_pct"] / 100)
            fee = position * (fee_pct / 100)
            net = gross - fee

            # Cap loss at allocated capital
            if net < -per_trade_capital:
                net = -per_trade_capital

            day_pnl += net
            win = bool(net > 0)

            trades.append({
                "date": sig["date"],
                "ticker": sig["ticker"],
                "direction": sig["direction"],
                "score": sig["score"],
                "reasons": sig["reasons"],
                "gap_pct": round(sig["gap_pct"], 3),
                "entry": round(sig["entry"], 2),
                "exit": round(sig["exit"], 2),
                "ret_pct": round(sig["ret_pct"], 3),
                "net_pnl": round(net, 2),
                "capital_after": 0,  # filled below
                "win": win,
                "n_simultaneous": n,
            })

        capital += day_pnl
        if capital < 0:
            capital = 0

        # Update capital_after for all trades on this date
        for t in trades:
            if t["date"] == date and t["capital_after"] == 0:
                t["capital_after"] = round(capital, 2)

        max_cap = max(max_cap, capital)
        dd = (max_cap - capital) / max_cap * 100 if max_cap > 0 else 0
        max_dd = max(max_dd, dd)
        equity_curve.append({
            "date": date,
            "capital": round(capital, 2),
            "drawdown": round(dd, 2),
            "n_trades": n,
        })

    # Summary stats
    total_trades = len(trades)
    wins = sum(1 for t in trades if t["win"])
    losses = total_trades - wins
    total_pnl = capital - initial_capital
    winrate = wins / total_trades * 100 if total_trades > 0 else 0
    avg_win = np.mean([t["net_pnl"] for t in trades if t["win"]]) if wins > 0 else 0
    avg_loss = np.mean([t["net_pnl"] for t in trades if not t["win"]]) if losses > 0 else 0
    best_trade = max((t["net_pnl"] for t in trades), default=0)
    worst_trade = min((t["net_pnl"] for t in trades), default=0)

    days = (pd.Timestamp(trades[-1]["date"]) - pd.Timestamp(trades[0]["date"])).days if len(trades) > 1 else 1
    annual_pct = total_pnl / initial_capital * 100 / max(days, 1) * 365

    # Candle data for chart (use first ticker)
    chart_ticker = tickers[0] if len(tickers) == 1 else tickers[0]
    cdf = all_candles.get(chart_ticker, pd.DataFrame())
    candles = []
    for idx, row in cdf.iterrows():
        candles.append({
            "time": idx.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
        })

    # MA20 line
    ma_line = []
    for idx, row in cdf.iterrows():
        if not pd.isna(row["MA20"]):
            ma_line.append({"time": idx.strftime("%Y-%m-%d"), "value": round(float(row["MA20"]), 2)})

    return {
        "candles": candles,
        "ma_line": ma_line,
        "trades": trades,
        "equity_curve": equity_curve,
        "summary": {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "winrate": round(winrate, 1),
            "total_pnl": round(total_pnl, 2),
            "total_pct": round(total_pnl / initial_capital * 100, 1),
            "max_drawdown": round(max_dd, 1),
            "annual_pct": round(annual_pct, 1),
            "avg_win": round(float(avg_win), 2),
            "avg_loss": round(float(avg_loss), 2),
            "best_trade": round(float(best_trade), 2),
            "worst_trade": round(float(worst_trade), 2),
            "final_capital": round(capital, 2),
            "initial_capital": initial_capital,
        },
    }


@app.get("/api/tickers")
def get_tickers():
    return {"tickers": TICKERS}


@app.get("/api/backtest")
def api_backtest(
    ticker: str = Query("GOOGL"),
    gap_th: float = Query(0.5),
    body_th: float = Query(1.0),
    consec: bool = Query(True),
    ma_dist: float = Query(0.0),
    min_score: int = Query(3),
    leverage: float = Query(5.0),
    capital: float = Query(1000.0),
    fee: float = Query(0.07),
):
    tickers = TICKERS if ticker == "ALL" else [t.strip() for t in ticker.split(",")]
    result = run_backtest(tickers, gap_th, body_th, consec, ma_dist, min_score, leverage, capital, fee)
    return JSONResponse(content=result)


@app.get("/")
def serve_dashboard():
    html_path = Path(__file__).parent / "dashboard.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    print("Starting Gap FADE Backtest Dashboard...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)
