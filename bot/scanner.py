"""
Gap FADE Scanner — detects trading signals at market open
"""
from typing import Optional, List
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import config


def fetch_recent_data(ticker: str, days: int = 60) -> pd.DataFrame:
    """Fetch recent daily data for scoring."""
    end = datetime.now()
    start = end - timedelta(days=days)
    df = yf.download(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                     interval="1d", progress=False)
    if df.empty:
        return df
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
    return df.dropna(subset=["Gap_Pct", "MA20"])


def score_today(ticker: str) -> Optional[dict]:
    """
    Score today's gap for a ticker.
    Returns signal dict or None if no signal.
    """
    df = fetch_recent_data(ticker)
    if df.empty or len(df) < 2:
        return None

    row = df.iloc[-1]  # today
    today_date = df.index[-1].strftime("%Y-%m-%d")

    if row["Gap_Abs"] < 0.3:
        return None

    score = 0
    reasons = []

    if row["Gap_Abs"] >= config.GAP_THRESHOLD:
        score += 1
        reasons.append(f"gap:{row['Gap_Pct']:+.2f}%")

    if row["Prev_Body"] >= config.BODY_THRESHOLD and row["Prev_Body_Matches_Gap"]:
        score += 1
        reasons.append(f"body:{row['Prev_Body']:.1f}%")

    if config.CONSECUTIVE_GAP and row["Consec"]:
        score += 1
        reasons.append("consec")

    if row["MA_Dist"] >= config.MA_DISTANCE:
        score += 1
        reasons.append(f"ma:{row['MA_Dist']:.1f}%")

    if score < config.MIN_SCORE:
        return None

    direction = "SHORT" if row["Gap_Pct"] > 0 else "LONG"

    return {
        "date": today_date,
        "ticker": ticker,
        "direction": direction,
        "score": score,
        "reasons": reasons,
        "gap_pct": round(float(row["Gap_Pct"]), 3),
        "open_price": round(float(row["Open"]), 2),
        "prev_close": round(float(row["Prev_Close"]), 2),
    }


def scan_all() -> List[dict]:
    """Scan all configured tickers for signals."""
    signals = []
    for ticker in config.TICKERS:
        try:
            signal = score_today(ticker)
            if signal:
                signals.append(signal)
        except Exception as e:
            print(f"[WARN] Failed to scan {ticker}: {e}")
    # Sort by score descending
    signals.sort(key=lambda x: x["score"], reverse=True)
    return signals


if __name__ == "__main__":
    print(f"Scanning {config.TICKERS}...")
    signals = scan_all()
    if not signals:
        print("No signals today.")
    for s in signals:
        dir_icon = "🟢" if s["direction"] == "LONG" else "🔴"
        print(f"  {dir_icon} {s['ticker']} | Gap {s['gap_pct']:+.2f}% | Score {s['score']}/4 | {s['direction']}")
        print(f"     Reasons: {', '.join(s['reasons'])}")
