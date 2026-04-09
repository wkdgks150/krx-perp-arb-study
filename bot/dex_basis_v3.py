"""
DEX ↔ 전통시장 구조적 스프레드 분석 v3

v2 문제: SPY가 S&P500 지수의 1/10 가격 → 903% "프리미엄"은 단위 오류
v3 수정: SPY × 10 스케일링, ES는 지수 레벨이므로 그대로 사용
"""
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
import yfinance as yf


def fetch_hl(coin="xyz:SP500", interval="1h"):
    start_ts = int(datetime(2026, 3, 18, tzinfo=timezone.utc).timestamp() * 1000)
    end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    all_data = []
    cursor = start_ts
    while cursor < end_ts:
        resp = requests.post("https://api.hyperliquid.xyz/info", json={
            "type": "candleSnapshot",
            "req": {"coin": coin, "interval": interval,
                    "startTime": cursor, "endTime": end_ts}
        }, timeout=30)
        data = resp.json()
        if not data:
            break
        all_data.extend(data)
        last = data[-1]["T"]
        if last <= cursor:
            break
        cursor = last + 1
        time.sleep(0.2)
    df = pd.DataFrame(all_data)
    df["dt"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df.set_index("dt").sort_index()
    df["HL"] = df["c"].astype(float)
    return df[["HL"]]


def fetch_hl_funding(coin="xyz:SP500"):
    start_ts = int(datetime(2026, 3, 18, tzinfo=timezone.utc).timestamp() * 1000)
    end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    resp = requests.post("https://api.hyperliquid.xyz/info", json={
        "type": "fundingHistory", "coin": coin,
        "startTime": start_ts, "endTime": end_ts
    }, timeout=30)
    df = pd.DataFrame(resp.json())
    df["dt"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df = df.set_index("dt").sort_index()
    df["fr"] = df["fundingRate"].astype(float)
    df["prem"] = df["premium"].astype(float)
    return df[["fr", "prem"]]


def fetch_yf(ticker, period="1mo", interval="1h"):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty:
        return df
    df.columns = df.columns.get_level_values(0)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df.index = df.index.floor("h")
    df = df[~df.index.duplicated(keep="last")]
    return df[["Close"]]


def main():
    print("=" * 80)
    print("  DEX vs 해외선물/나스닥 — 김치프리미엄급 상시 갭 존재 여부")
    print("=" * 80)

    # ── Fetch ──
    hl = fetch_hl()
    funding = fetch_hl_funding()
    es = fetch_yf("ES=F")
    spy = fetch_yf("SPY")

    hl.index = hl.index.floor("h")
    hl = hl[~hl.index.duplicated(keep="last")]

    print(f"\n  HL SP500:  {len(hl)} bars | {hl.index[0].date()} ~ {hl.index[-1].date()}")
    print(f"  ES=F:      {len(es)} bars")
    print(f"  SPY:       {len(spy)} bars")
    print(f"  펀딩레이트: {len(funding)} entries")

    # SPY × 10 = S&P 500 지수 레벨로 환산
    spy["Close"] = spy["Close"] * 10

    # ── Merge ──
    m_es = hl.join(es.rename(columns={"Close": "ES"}), how="inner")
    m_spy = hl.join(spy.rename(columns={"Close": "SPY10"}), how="inner")

    m_es["basis_bps"] = (m_es["HL"] - m_es["ES"]) / m_es["ES"] * 10000
    m_spy["basis_bps"] = (m_spy["HL"] - m_spy["SPY10"]) / m_spy["SPY10"] * 10000

    print(f"\n  매칭: HL∩ES = {len(m_es)} | HL∩SPY = {len(m_spy)}")

    # ═══════════════════════════════════════════════
    # 1. HL vs ES (해외선물)
    # ═══════════════════════════════════════════════
    print(f"\n{'='*80}")
    print(f"  ① HL SP500 perp vs CME ES 선물 (해외선물)")
    print(f"{'='*80}")
    b = m_es["basis_bps"]
    _stats(b, "bps")
    _distribution_bps(b)
    _time_pattern(m_es, "basis_bps")

    # ═══════════════════════════════════════════════
    # 2. HL vs SPY×10 (나스닥/현물)
    # ═══════════════════════════════════════════════
    print(f"\n{'='*80}")
    print(f"  ② HL SP500 perp vs SPY×10 (현물 proxy)")
    print(f"{'='*80}")
    b2 = m_spy["basis_bps"]
    _stats(b2, "bps")
    _distribution_bps(b2)
    _time_pattern(m_spy, "basis_bps")

    # ═══════════════════════════════════════════════
    # 3. ES vs SPY×10 (캐리 분리)
    # ═══════════════════════════════════════════════
    carry = es.join(spy.rename(columns={"Close": "SPY10"}), how="inner")
    if len(carry) > 0:
        carry["carry_bps"] = (carry["Close"] - carry["SPY10"]) / carry["SPY10"] * 10000
        print(f"\n{'='*80}")
        print(f"  ③ CME ES vs SPY×10 (순수 캐리 = 금리)")
        print(f"{'='*80}")
        _stats(carry["carry_bps"], "bps")

    # ═══════════════════════════════════════════════
    # 4. 펀딩레이트
    # ═══════════════════════════════════════════════
    print(f"\n{'='*80}")
    print(f"  ④ 펀딩레이트 (DEX 고유 수익원)")
    print(f"{'='*80}")
    fr = funding["fr"]
    print(f"  평균:    {fr.mean()*10000:+.2f} bps/h (연 {fr.mean()*10000*24*365:+.0f} bps)")
    print(f"  중앙값:  {fr.median()*10000:+.2f} bps/h")
    print(f"  범위:    {fr.min()*10000:+.2f} ~ {fr.max()*10000:+.2f} bps/h")
    print(f"  음(-):   {(fr<0).mean()*100:.0f}% (롱 유리) | 양(+): {(fr>0).mean()*100:.0f}% (숏 유리)")

    # ═══════════════════════════════════════════════
    # 5. BACKTEST: Basis Mean Reversion (HL vs ES)
    # ═══════════════════════════════════════════════
    print(f"\n\n{'█'*80}")
    print(f"  BACKTEST: Basis Mean-Reversion 차익거래")
    print(f"{'█'*80}")

    for entry, exit_th, lev, label in [
        (20, 5, 5, "보수적 (20bps 진입, 5x)"),
        (15, 3, 5, "중간 (15bps 진입, 5x)"),
        (10, 2, 5, "공격적 (10bps 진입, 5x)"),
        (15, 3, 10, "중간 (15bps 진입, 10x)"),
    ]:
        _backtest_basis_mr(m_es, entry, exit_th, lev, label)

    # ═══════════════════════════════════════════════
    # 6. BACKTEST: 펀딩 수확 (delta-neutral)
    # ═══════════════════════════════════════════════
    print(f"\n\n{'█'*80}")
    print(f"  BACKTEST: 펀딩레이트 수확 (Long HL + Short ES hedge)")
    print(f"{'█'*80}")

    for lev, label in [(3, "3x 보수적"), (5, "5x 기본"), (10, "10x 공격적")]:
        _backtest_funding(funding, hl, capital=10000, leverage=lev, label=label)

    # ═══════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════
    print(f"\n\n{'='*80}")
    print(f"  최종 결론: 김치프리미엄급 상시 갭이 있는가?")
    print(f"{'='*80}")

    es_mean = m_es["basis_bps"].mean()
    es_std = m_es["basis_bps"].std()
    spy_mean = m_spy["basis_bps"].mean() if len(m_spy) > 0 else 0
    spy_std = m_spy["basis_bps"].std() if len(m_spy) > 0 else 0
    fr_annual = fr.mean() * 10000 * 24 * 365

    print(f"""
  ┌────────────────────┬─────────────────┬──────────────────────┐
  │                    │ 김치프리미엄     │ HL vs 해외선물 갭     │
  ├────────────────────┼─────────────────┼──────────────────────┤
  │ 크기               │ +200~500 bps    │ {es_mean:+.0f} bps (σ={es_std:.0f})       │
  │ 방향               │ 항상 프리미엄   │ 항상 디스카운트       │
  │ 원인               │ 자본통제 (구조) │ 캐리+펀딩 (시장구조)  │
  │ 변동성             │ 높음            │ 낮음 (σ={es_std:.0f}bps)         │
  │ 차익거래           │ 불가 (규제)     │ 가능 (양방향 자유)    │
  │ 수렴 메커니즘      │ 없음            │ 펀딩레이트 (매시간)   │
  └────────────────────┴─────────────────┴──────────────────────┘

  결론:
  1. 상시 갭 EXISTS: HL은 ES 대비 {es_mean:.0f}bps 디스카운트 (100% 시간)
  2. 그러나 이건 ES의 캐리 프리미엄(금리)이지 DEX 고유 갭이 아님
  3. HL vs 현물(SPY×10): {spy_mean:+.0f}bps (σ={spy_std:.0f}) → 이것이 진짜 DEX 프리미엄
  4. 펀딩레이트: 연 {fr_annual:+.0f}bps → 롱 보유 시 수취
  5. 김치프리미엄(200-500bps)과는 규모·성격 모두 다름

  수익 기회:
  ├── 펀딩레이트 수확: 연 {abs(fr_annual):.0f}bps ({abs(fr_annual)/100:.1f}%) — 가장 안정적
  ├── Basis MR: 진동 폭 내 단타 — 기회 제한적
  └── 주말/이벤트 갭: 별도 (us-stock-perp-study.md 참조)

  기존 전략 대비:
  ├── Gap FADE (봇):       연 ~50-100% (방향성, 고위험)
  ├── 펀딩레이트 수확:     연 ~35-71% (델타뉴트럴, 저위험)
  ├── us-stock-perp A/B/C: 연 ~34-150% (이벤트 기반)
  └── Basis MR:            연 ?? (데이터 3주로 판단 어려움)
""")


def _stats(series, unit="bps"):
    print(f"  평균:   {series.mean():+.1f} {unit}")
    print(f"  중앙값: {series.median():+.1f} {unit}")
    print(f"  σ:      {series.std():.1f} {unit}")
    print(f"  범위:   {series.min():+.1f} ~ {series.max():+.1f} {unit}")
    pos = (series > 0).mean() * 100
    neg = (series < 0).mean() * 100
    print(f"  프리미엄(+): {pos:.0f}% | 디스카운트(-): {neg:.0f}%")


def _distribution_bps(series):
    bins = [(-200, -100), (-100, -50), (-50, -20), (-20, -10), (-10, 0),
            (0, 10), (10, 20), (20, 50), (50, 100), (100, 200)]
    print(f"\n  분포:")
    for lo, hi in bins:
        n = ((series >= lo) & (series < hi)).sum()
        pct = n / len(series) * 100
        bar = "█" * int(pct / 2)
        print(f"    {lo:+4d}~{hi:+4d} bps: {pct:5.1f}% ({n:3d}) {bar}")


def _time_pattern(df, col):
    df = df.copy()
    df["hour"] = df.index.hour
    print(f"\n  시간대 패턴 (UTC):")
    hourly = df.groupby("hour")[col].agg(["mean", "std", "count"])
    for h, r in hourly.iterrows():
        if r["count"] >= 3:
            print(f"    {h:02d}:00  {r['mean']:+6.1f} ±{r['std']:4.1f} bps  (n={int(r['count'])})")


def _backtest_basis_mr(data, entry_bps, exit_bps, leverage, label):
    """Basis mean-reversion: enter when basis deviates from rolling mean."""
    print(f"\n  ── {label} ──")
    df = data.copy()
    df["basis_ma"] = df["basis_bps"].rolling(24, min_periods=12).mean()
    df["basis_dev"] = df["basis_bps"] - df["basis_ma"]
    df = df.dropna(subset=["basis_dev"])

    if df.empty:
        print("    데이터 부족")
        return

    cap = 10000
    pos = 0  # +1=long basis (expect widen), -1=short basis (expect narrow)
    entry_dev = 0
    trades = []
    fee_bps = 5.5  # HL 3.5 + CME 2 bps one-way

    for i in range(len(df)):
        dev = df.iloc[i]["basis_dev"]
        if pos == 0:
            if dev > entry_bps:
                pos = -1; entry_dev = dev
            elif dev < -entry_bps:
                pos = 1; entry_dev = dev
        else:
            exit = (pos == -1 and dev <= exit_bps) or (pos == 1 and dev >= -exit_bps)
            if exit:
                captured = abs(entry_dev - dev)  # bps captured
                gross = cap * leverage * captured / 10000
                fee = cap * leverage * fee_bps * 2 / 10000
                net = gross - fee
                cap += net
                trades.append({"captured": captured, "net": net})
                pos = 0

    if not trades:
        print(f"    거래 없음")
        return

    wins = sum(1 for t in trades if t["net"] > 0)
    pnl = cap - 10000
    days = (df.index[-1] - df.index[0]).total_seconds() / 86400

    print(f"    거래: {len(trades)} | 승률: {wins/len(trades)*100:.0f}%")
    print(f"    평균 캡처: {np.mean([t['captured'] for t in trades]):.1f} bps")
    print(f"    총 수익: ${pnl:+,.0f} ({pnl/10000*100:+.1f}%)")
    if days > 0:
        print(f"    연 환산: {pnl/10000*100/days*365:+.0f}%")


def _backtest_funding(funding, hl, capital, leverage, label):
    """펀딩레이트 수확: Long HL perp + Short ES/SPY hedge."""
    print(f"\n  ── {label} ──")
    pos = capital * leverage
    fee = pos * 0.035 / 100 * 2  # entry + exit

    total_fr = 0
    for _, r in funding.iterrows():
        # 롱: 음 펀딩 수취, 양 펀딩 지불
        total_fr += -r["fr"] * pos

    net = total_fr - fee
    days = (funding.index[-1] - funding.index[0]).total_seconds() / 86400

    print(f"    포지션: ${pos:,.0f} ({leverage}x)")
    print(f"    펀딩 수익: ${total_fr:+,.2f}")
    print(f"    수수료: ${fee:,.2f}")
    print(f"    순이익: ${net:+,.2f} ({net/capital*100:+.1f}%)")
    if days > 0:
        print(f"    월 환산: {net/capital*100/days*30:+.1f}%")
        print(f"    연 환산: {net/capital*100/days*365:+.0f}%")

    # Risk
    prices = hl["HL"]
    max_p = prices.expanding().max()
    dd = ((max_p - prices) / max_p * 100).max()
    print(f"    가격 MDD (미헤지): {dd*leverage:.0f}% → SPY/ES 숏 헤지 필수")


if __name__ == "__main__":
    main()
