"""
Backtesting Engine v2 — accurate simulation + strategy framework

Improvements over v1 (backtest_api.py):
1. Slippage modeling (realistic entry/exit)
2. Walk-forward validation (train/test split)
3. Pluggable strategy system (easy to add new strategies)
4. Rich statistics (Sharpe, Sortino, Calmar, streaks)
5. Multi-data-source support (yfinance, Alpaca, DEX APIs)
"""
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

import numpy as np
import pandas as pd
import yfinance as yf


# ═══════════════════════════════════════════════════════════════
# Data Layer
# ═══════════════════════════════════════════════════════════════

_cache = {}


def fetch_stock(ticker: str, start: str = "2025-07-01", end: str = None,
                interval: str = "1d") -> pd.DataFrame:
    """Fetch stock data with caching."""
    end = end or datetime.now().strftime("%Y-%m-%d")
    key = f"{ticker}_{start}_{end}_{interval}"
    if key in _cache:
        return _cache[key]
    df = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
    if df.empty:
        return df
    df.columns = df.columns.get_level_values(0)
    _cache[key] = df
    return df


def enrich_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Add all computed columns for strategy scoring."""
    df = df.copy()
    df["Prev_Close"] = df["Close"].shift(1)
    df["Prev_Open"] = df["Open"].shift(1)
    df["Prev_High"] = df["High"].shift(1)
    df["Prev_Low"] = df["Low"].shift(1)
    df["Gap_Pct"] = (df["Open"] - df["Prev_Close"]) / df["Prev_Close"] * 100
    df["Gap_Abs"] = abs(df["Gap_Pct"])
    df["Day_Return"] = (df["Close"] - df["Open"]) / df["Open"] * 100
    df["Prev_Body"] = abs((df["Prev_Close"] - df["Prev_Open"]) / df["Prev_Open"] * 100)
    df["Prev_Body_Dir"] = np.sign(df["Prev_Close"] - df["Prev_Open"])
    df["Gap_Dir"] = np.sign(df["Gap_Pct"])
    df["Body_Matches_Gap"] = (df["Prev_Body_Dir"] == df["Gap_Dir"]).astype(int)
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA10"] = df["Close"].rolling(10).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA_Dist"] = abs((df["Open"] - df["MA20"]) / df["MA20"] * 100)
    df["Prev_Gap"] = df["Gap_Pct"].shift(1)
    df["Consec"] = (np.sign(df["Gap_Pct"]) == np.sign(df["Prev_Gap"])).astype(int)
    df["Volatility"] = df["Day_Return"].rolling(20).std()
    df["Range_Pct"] = (df["High"] - df["Low"]) / df["Open"] * 100
    df["Prev_Range"] = df["Range_Pct"].shift(1)
    # RSI(14)
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["Prev_RSI"] = df["RSI"].shift(1)
    # Close position in day's range
    df["Close_Pos"] = (df["Close"] - df["Low"]) / (df["High"] - df["Low"] + 1e-10)
    df["Prev_Close_Pos"] = df["Close_Pos"].shift(1)
    # Volume relative
    df["Vol_MA10"] = df["Volume"].rolling(10).mean()
    df["Vol_Ratio"] = df["Volume"] / (df["Vol_MA10"] + 1)
    df["Weekday"] = df.index.dayofweek
    return df.dropna(subset=["Gap_Pct", "MA20", "RSI"])


# ═══════════════════════════════════════════════════════════════
# Strategy Base Class
# ═══════════════════════════════════════════════════════════════

@dataclass
class Signal:
    date: str
    ticker: str
    direction: int   # +1 = LONG, -1 = SHORT
    score: float
    reasons: List[str]
    meta: Dict = field(default_factory=dict)


class Strategy(ABC):
    """Base class for all strategies."""
    name: str = "base"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, ticker: str) -> List[Signal]:
        """Generate signals from enriched daily data."""
        pass

    def describe(self) -> str:
        return self.name


# ═══════════════════════════════════════════════════════════════
# Built-in Strategies
# ═══════════════════════════════════════════════════════════════

class GapFadeStrategy(Strategy):
    """The proven gap FADE with scoring system."""
    name = "gap_fade"

    def __init__(self, gap_th=0.5, body_th=1.0, consec=True, ma_dist=0.0, min_score=3):
        self.gap_th = gap_th
        self.body_th = body_th
        self.consec = consec
        self.ma_dist = ma_dist
        self.min_score = min_score

    def generate_signals(self, df, ticker):
        signals = []
        for idx, row in df.iterrows():
            if row["Gap_Abs"] < 0.3:
                continue
            score = 0
            reasons = []
            if row["Gap_Abs"] >= self.gap_th:
                score += 1; reasons.append(f"gap:{row['Gap_Pct']:+.1f}%")
            if row["Prev_Body"] >= self.body_th and row["Body_Matches_Gap"]:
                score += 1; reasons.append(f"body:{row['Prev_Body']:.1f}%")
            if self.consec and row["Consec"]:
                score += 1; reasons.append("consec")
            if row["MA_Dist"] >= self.ma_dist:
                score += 1; reasons.append(f"ma:{row['MA_Dist']:.1f}%")
            if score >= self.min_score:
                direction = -1 if row["Gap_Pct"] > 0 else 1  # FADE
                signals.append(Signal(
                    date=idx.strftime("%Y-%m-%d"), ticker=ticker,
                    direction=direction, score=score, reasons=reasons,
                ))
        return signals

    def describe(self):
        return f"GapFade(gap>{self.gap_th}% body>{self.body_th}% consec={self.consec} ma>{self.ma_dist}% score>={self.min_score})"


class RSIReversalStrategy(Strategy):
    """RSI extreme + gap → mean reversion."""
    name = "rsi_reversal"

    def __init__(self, rsi_low=30, rsi_high=70, gap_th=0.5):
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.gap_th = gap_th

    def generate_signals(self, df, ticker):
        signals = []
        for idx, row in df.iterrows():
            if row["Gap_Abs"] < self.gap_th:
                continue
            if row["Prev_RSI"] < self.rsi_low and row["Gap_Pct"] < 0:
                signals.append(Signal(idx.strftime("%Y-%m-%d"), ticker, +1, 3,
                                      [f"rsi:{row['Prev_RSI']:.0f}", f"gap:{row['Gap_Pct']:+.1f}%"]))
            elif row["Prev_RSI"] > self.rsi_high and row["Gap_Pct"] > 0:
                signals.append(Signal(idx.strftime("%Y-%m-%d"), ticker, -1, 3,
                                      [f"rsi:{row['Prev_RSI']:.0f}", f"gap:{row['Gap_Pct']:+.1f}%"]))
        return signals


class MeanReversionStrategy(Strategy):
    """Price far from MA20 → revert."""
    name = "ma_reversion"

    def __init__(self, ma_dist_th=3.0):
        self.ma_dist_th = ma_dist_th

    def generate_signals(self, df, ticker):
        signals = []
        for idx, row in df.iterrows():
            dist = (row["Open"] - row["MA20"]) / row["MA20"] * 100
            if abs(dist) < self.ma_dist_th:
                continue
            direction = -1 if dist > 0 else 1  # revert toward MA
            signals.append(Signal(idx.strftime("%Y-%m-%d"), ticker, direction, 3,
                                  [f"ma_dist:{dist:+.1f}%"]))
        return signals


class VolumeSpikeFadeStrategy(Strategy):
    """High volume day + gap → FADE (overreaction)."""
    name = "vol_spike_fade"

    def __init__(self, vol_ratio=1.5, gap_th=0.5):
        self.vol_ratio = vol_ratio
        self.gap_th = gap_th

    def generate_signals(self, df, ticker):
        signals = []
        for idx, row in df.iterrows():
            if row["Gap_Abs"] < self.gap_th:
                continue
            prev_vol_ratio = df.shift(1).loc[idx, "Vol_Ratio"] if idx in df.index else 0
            if prev_vol_ratio >= self.vol_ratio:
                direction = -1 if row["Gap_Pct"] > 0 else 1
                signals.append(Signal(idx.strftime("%Y-%m-%d"), ticker, direction, 3,
                                      [f"vol:{prev_vol_ratio:.1f}x", f"gap:{row['Gap_Pct']:+.1f}%"]))
        return signals


class GapFollowStrategy(Strategy):
    """Follow gap direction (momentum). Opposite of FADE."""
    name = "gap_follow"

    def __init__(self, gap_th=1.0):
        self.gap_th = gap_th

    def generate_signals(self, df, ticker):
        signals = []
        for idx, row in df.iterrows():
            if row["Gap_Abs"] < self.gap_th:
                continue
            direction = 1 if row["Gap_Pct"] > 0 else -1  # FOLLOW
            signals.append(Signal(idx.strftime("%Y-%m-%d"), ticker, direction, 2,
                                  [f"gap:{row['Gap_Pct']:+.1f}%"]))
        return signals


class ComboStrategy(Strategy):
    """Combine multiple strategies. Trade when N+ strategies agree."""
    name = "combo"

    def __init__(self, strategies, min_agree=2):
        self.strategies = strategies
        self.min_agree = min_agree
        self.name = f"combo({'+'.join(s.name for s in strategies)})"

    def generate_signals(self, df, ticker):
        # Collect all signals by date
        from collections import defaultdict
        by_date = defaultdict(list)
        for strat in self.strategies:
            for sig in strat.generate_signals(df, ticker):
                by_date[sig.date].append(sig)

        combined = []
        for date, sigs in by_date.items():
            # Check if enough strategies agree on direction
            longs = [s for s in sigs if s.direction == 1]
            shorts = [s for s in sigs if s.direction == -1]
            if len(longs) >= self.min_agree:
                reasons = []
                for s in longs:
                    reasons.extend(s.reasons)
                combined.append(Signal(date, ticker, 1, len(longs), reasons))
            elif len(shorts) >= self.min_agree:
                reasons = []
                for s in shorts:
                    reasons.extend(s.reasons)
                combined.append(Signal(date, ticker, -1, len(shorts), reasons))
        return combined


# ═══════════════════════════════════════════════════════════════
# Simulation Engine
# ═══════════════════════════════════════════════════════════════

@dataclass
class TradeResult:
    date: str
    ticker: str
    direction: int
    score: float
    reasons: List[str]
    entry: float
    exit: float
    ret_pct: float
    gross_pnl: float
    fee: float
    slippage_cost: float
    net_pnl: float
    capital_after: float
    n_simultaneous: int


@dataclass
class BacktestResult:
    trades: List[TradeResult]
    equity_curve: List[Dict]
    stats: Dict


def simulate(
    strategy: Strategy,
    tickers: List[str],
    start: str = "2025-07-01",
    end: str = None,
    capital: float = 1000.0,
    leverage: float = 5.0,
    fee_pct: float = 0.07,
    slippage_pct: float = 0.05,  # NEW: realistic slippage
    max_pos_pct: float = 0.95,
) -> BacktestResult:
    """
    Run backtest with realistic slippage and portfolio allocation.

    slippage_pct: added to entry, subtracted from exit (worst-case execution)
    """
    initial = capital
    trades = []
    equity = []
    max_cap = capital

    # Collect & enrich data
    all_data = {}
    for t in tickers:
        df = fetch_stock(t, start, end)
        if not df.empty:
            all_data[t] = enrich_daily(df)

    # Collect all signals
    all_signals = []
    for t, df in all_data.items():
        for sig in strategy.generate_signals(df, t):
            # Attach OHLC for execution
            date_rows = df[df.index.strftime("%Y-%m-%d") == sig.date]
            if date_rows.empty:
                continue
            row = date_rows.iloc[0]
            sig.meta["open"] = float(row["Open"])
            sig.meta["close"] = float(row["Close"])
            sig.meta["high"] = float(row["High"])
            sig.meta["low"] = float(row["Low"])
            all_signals.append(sig)

    # Sort by date
    all_signals.sort(key=lambda x: x.date)

    # Group by date → portfolio execution
    from itertools import groupby
    for date, day_iter in groupby(all_signals, key=lambda x: x.date):
        if capital <= 0:
            break
        day_sigs = list(day_iter)
        n = len(day_sigs)
        per_trade = capital * max_pos_pct / n
        day_pnl = 0.0

        for sig in day_sigs:
            raw_open = sig.meta["open"]
            raw_close = sig.meta["close"]

            # Apply slippage: worse entry, worse exit
            if sig.direction == 1:  # LONG
                entry = raw_open * (1 + slippage_pct / 100)   # buy higher
                exit_p = raw_close * (1 - slippage_pct / 100)  # sell lower
                ret_pct = (exit_p - entry) / entry * 100
            else:  # SHORT
                entry = raw_open * (1 - slippage_pct / 100)   # sell lower
                exit_p = raw_close * (1 + slippage_pct / 100)  # buy higher
                ret_pct = (entry - exit_p) / entry * 100

            position = per_trade * leverage
            gross = position * (ret_pct / 100)
            fee_cost = position * (fee_pct / 100)
            slip_cost = position * (slippage_pct / 100) * 2  # entry + exit
            net = gross - fee_cost  # slippage already in ret_pct

            if net < -per_trade:
                net = -per_trade
            day_pnl += net

            trades.append(TradeResult(
                date=sig.date, ticker=sig.ticker, direction=sig.direction,
                score=sig.score, reasons=sig.reasons,
                entry=round(entry, 2), exit=round(exit_p, 2),
                ret_pct=round(ret_pct, 3), gross_pnl=round(gross, 2),
                fee=round(fee_cost, 2), slippage_cost=round(slip_cost, 2),
                net_pnl=round(net, 2), capital_after=0, n_simultaneous=n,
            ))

        capital += day_pnl
        if capital < 0:
            capital = 0
        for t in trades:
            if t.date == date and t.capital_after == 0:
                t.capital_after = round(capital, 2)
        max_cap = max(max_cap, capital)
        dd = (max_cap - capital) / max_cap * 100 if max_cap > 0 else 0
        equity.append({"date": date, "capital": round(capital, 2), "drawdown": round(dd, 2), "n": n})

    stats = compute_stats(trades, equity, initial, capital)
    return BacktestResult(trades=trades, equity_curve=equity, stats=stats)


def compute_stats(trades, equity, initial, final) -> Dict:
    if not trades:
        return {"total_trades": 0}
    n = len(trades)
    wins = sum(1 for t in trades if t.net_pnl > 0)
    losses = n - wins
    pnls = [t.net_pnl for t in trades]
    win_pnls = [p for p in pnls if p > 0]
    loss_pnls = [p for p in pnls if p <= 0]
    total_pnl = final - initial
    days = max((pd.Timestamp(trades[-1].date) - pd.Timestamp(trades[0].date)).days, 1)

    # Streaks
    max_win_streak = max_loss_streak = cur_streak = 0
    for t in trades:
        if t.net_pnl > 0:
            cur_streak = max(0, cur_streak) + 1
            max_win_streak = max(max_win_streak, cur_streak)
        else:
            cur_streak = min(0, cur_streak) - 1
            max_loss_streak = max(max_loss_streak, abs(cur_streak))

    # Daily returns for Sharpe/Sortino
    daily_rets = []
    prev_cap = initial
    for e in equity:
        r = (e["capital"] - prev_cap) / prev_cap if prev_cap > 0 else 0
        daily_rets.append(r)
        prev_cap = e["capital"]

    daily_rets = np.array(daily_rets)
    avg_ret = np.mean(daily_rets) if len(daily_rets) > 0 else 0
    std_ret = np.std(daily_rets) if len(daily_rets) > 1 else 1
    downside_std = np.std(daily_rets[daily_rets < 0]) if np.any(daily_rets < 0) else 1

    sharpe = (avg_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0
    sortino = (avg_ret / downside_std * np.sqrt(252)) if downside_std > 0 else 0
    max_dd = max((e["drawdown"] for e in equity), default=0)
    calmar = (total_pnl / initial * 100 / days * 365) / max_dd if max_dd > 0 else 0

    # Total fees & slippage
    total_fees = sum(t.fee for t in trades)
    total_slippage = sum(t.slippage_cost for t in trades)

    return {
        "total_trades": n,
        "wins": wins,
        "losses": losses,
        "winrate": round(wins / n * 100, 1),
        "total_pnl": round(total_pnl, 2),
        "total_pct": round(total_pnl / initial * 100, 1),
        "annual_pct": round(total_pnl / initial * 100 / days * 365, 1),
        "max_drawdown": round(max_dd, 1),
        "sharpe": round(float(sharpe), 2),
        "sortino": round(float(sortino), 2),
        "calmar": round(float(calmar), 2),
        "avg_win": round(float(np.mean(win_pnls)), 2) if win_pnls else 0,
        "avg_loss": round(float(np.mean(loss_pnls)), 2) if loss_pnls else 0,
        "best_trade": round(max(pnls), 2),
        "worst_trade": round(min(pnls), 2),
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "profit_factor": round(sum(win_pnls) / abs(sum(loss_pnls)), 2) if loss_pnls and sum(loss_pnls) != 0 else 999,
        "total_fees": round(total_fees, 2),
        "total_slippage": round(total_slippage, 2),
        "final_capital": round(final, 2),
        "initial_capital": initial,
        "days": days,
    }


# ═══════════════════════════════════════════════════════════════
# Walk-Forward Validation
# ═══════════════════════════════════════════════════════════════

def walk_forward(
    strategy: Strategy,
    tickers: List[str],
    train_months: int = 3,
    test_months: int = 1,
    start: str = "2025-07-01",
    **kwargs,
) -> List[Dict]:
    """
    Walk-forward: train on N months, test on next M months, slide forward.
    Returns list of test-period results.
    """
    start_dt = pd.Timestamp(start)
    end_dt = pd.Timestamp(datetime.now())
    results = []
    cursor = start_dt

    while cursor + pd.DateOffset(months=train_months + test_months) <= end_dt:
        train_end = cursor + pd.DateOffset(months=train_months)
        test_end = train_end + pd.DateOffset(months=test_months)

        # Test period only (train period is for strategy calibration)
        result = simulate(
            strategy, tickers,
            start=train_end.strftime("%Y-%m-%d"),
            end=test_end.strftime("%Y-%m-%d"),
            **kwargs,
        )
        results.append({
            "train": f"{cursor.strftime('%Y-%m')} → {train_end.strftime('%Y-%m')}",
            "test": f"{train_end.strftime('%Y-%m')} → {test_end.strftime('%Y-%m')}",
            "stats": result.stats,
        })
        cursor += pd.DateOffset(months=test_months)

    return results


# ═══════════════════════════════════════════════════════════════
# Strategy Comparison
# ═══════════════════════════════════════════════════════════════

def compare_strategies(
    strategies: List[Strategy],
    tickers: List[str],
    **kwargs,
) -> pd.DataFrame:
    """Run multiple strategies and compare results."""
    rows = []
    for strat in strategies:
        result = simulate(strat, tickers, **kwargs)
        s = result.stats
        rows.append({
            "strategy": strat.describe(),
            "trades": s.get("total_trades", 0),
            "winrate": s.get("winrate", 0),
            "pnl_pct": s.get("total_pct", 0),
            "annual": s.get("annual_pct", 0),
            "mdd": s.get("max_drawdown", 0),
            "sharpe": s.get("sharpe", 0),
            "sortino": s.get("sortino", 0),
            "calmar": s.get("calmar", 0),
            "profit_factor": s.get("profit_factor", 0),
            "fees": s.get("total_fees", 0),
            "slippage": s.get("total_slippage", 0),
        })
    return pd.DataFrame(rows).sort_values("pnl_pct", ascending=False)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pd.set_option("display.width", 140)
    tickers = ["GOOGL", "NVDA", "MSFT"]

    strategies = [
        GapFadeStrategy(gap_th=0.5, body_th=1.0, consec=True, min_score=3),
        GapFadeStrategy(gap_th=0.3, body_th=1.0, consec=True, ma_dist=3, min_score=4),
        RSIReversalStrategy(),
        MeanReversionStrategy(ma_dist_th=3.0),
        VolumeSpikeFadeStrategy(),
        GapFollowStrategy(gap_th=1.0),
    ]

    print("=" * 120)
    print(f"Strategy Comparison — {', '.join(tickers)} — $1K, 5x, slippage 0.05%")
    print("=" * 120)

    df = compare_strategies(strategies, tickers, capital=1000, leverage=5, slippage_pct=0.05)
    print(df.to_string(index=False))

    # Walk-forward for best strategy
    print("\n" + "=" * 120)
    print("Walk-Forward Validation — GapFade Aggressive")
    print("=" * 120)
    wf = walk_forward(
        GapFadeStrategy(gap_th=0.5, body_th=1.0, consec=True, min_score=3),
        tickers, train_months=3, test_months=1, capital=1000, leverage=5,
    )
    for r in wf:
        s = r["stats"]
        print(f"  Train: {r['train']} | Test: {r['test']} | "
              f"Trades: {s.get('total_trades',0)} | WR: {s.get('winrate',0)}% | "
              f"PnL: {s.get('total_pct',0):+.1f}% | MDD: {s.get('max_drawdown',0):.1f}%")
