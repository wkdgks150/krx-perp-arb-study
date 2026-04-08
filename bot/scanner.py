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


def check_market_ok() -> bool:
    """Check if market environment is favorable (SPY above MA20 or low vol)."""
    try:
        df = fetch_recent_data("SPY", days=30)
        if df.empty or len(df) < 5:
            return True
        ma20 = df["Close"].rolling(20).mean().iloc[-1]
        current = df["Close"].iloc[-1]
        above_ma = current > ma20
        vol = df["Close"].pct_change().rolling(5).std().iloc[-1] * 100
        high_vol = vol > 2.5
        if not above_ma and high_vol:
            print(f"  [MARKET FILTER] SPY below MA20 + high vol ({vol:.1f}%) — skipping")
            return False
        return True
    except Exception:
        return True


def auto_select_tickers() -> List[str]:
    """Auto-select best FADE tickers based on recent win rate."""
    ALL_CANDIDATES = ["GOOGL", "NVDA", "TSLA", "AAPL", "META", "AMZN", "MSFT", "SPY"]
    scores = {}

    for ticker in ALL_CANDIDATES:
        try:
            df = fetch_recent_data(ticker, days=90)
            if df.empty or len(df) < 20:
                continue
            wins = 0
            total = 0
            for i in range(20, len(df)):
                row = df.iloc[i]
                if row["Gap_Abs"] < 0.5:
                    continue
                # FADE: gap up→short (win if close<open), gap down→long (win if close>open)
                if row["Gap_Pct"] > 0:
                    win = df["Close"].iloc[i] < df["Open"].iloc[i]
                else:
                    win = df["Close"].iloc[i] > df["Open"].iloc[i]
                total += 1
                if win:
                    wins += 1
            if total >= 5:
                scores[ticker] = wins / total
        except Exception:
            continue

    # Select tickers with >50% FADE win rate, top 3
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    selected = [t for t, wr in ranked if wr > 0.50][:3]

    if selected:
        print(f"  [AUTO SELECT] {', '.join(f'{t}({scores[t]*100:.0f}%)' for t in selected)}")
    return selected if selected else config.TICKERS


def scan_all() -> List[dict]:
    """Scan all configured tickers for signals with market filter."""
    # Market environment check
    if not check_market_ok():
        return []

    # Use configured tickers (auto-select can be enabled later)
    tickers = config.TICKERS

    signals = []
    for ticker in tickers:
        try:
            signal = score_today(ticker)
            if signal:
                signals.append(signal)
        except Exception as e:
            print(f"[WARN] Failed to scan {ticker}: {e}")
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
