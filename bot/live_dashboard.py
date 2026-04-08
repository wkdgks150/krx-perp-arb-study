"""
Live Trading Dashboard — real-time account monitoring

Purpose: Visual monitoring. Not for alerts (that's Telegram).
Shows:
  - Account balance + P&L
  - Open positions (real-time)
  - Trade history from DB
  - Equity curve
  - Next signals preview

Port 8001 (backtest dashboard = port 8000)
"""
import json
import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from bn_executor import BinanceExecutor
import config

app = FastAPI(title="Gap FADE Live Dashboard")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = Path(__file__).parent / "trades.db"


@app.get("/api/live/account")
def api_account():
    try:
        ex = BinanceExecutor()
        acct = ex.get_account()
        positions = ex.get_positions()

        pos_list = []
        for p in positions:
            amt = float(p["positionAmt"])
            pos_list.append({
                "symbol": p["symbol"],
                "direction": "LONG" if amt > 0 else "SHORT",
                "qty": abs(amt),
                "entryPrice": float(p["entryPrice"]),
                "markPrice": float(p.get("markPrice", 0)),
                "pnl": float(p["unrealizedProfit"]),
                "leverage": p.get("leverage", "?"),
            })

        return {
            "balance": float(acct.get("totalWalletBalance", 0)),
            "available": float(acct.get("availableBalance", 0)),
            "unrealizedPnl": float(acct.get("totalUnrealizedProfit", 0)),
            "positions": pos_list,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/live/trades")
def api_trades():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM trades ORDER BY date DESC, id DESC LIMIT 50").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/live/signals")
def api_signals():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 30").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/live/equity")
def api_equity():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM daily_summary ORDER BY date").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/live/prices")
def api_prices():
    try:
        ex = BinanceExecutor()
        prices = {}
        for t in config.TICKERS:
            try:
                prices[t] = ex.get_price(t)
            except Exception:
                prices[t] = 0
        return prices
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
def serve():
    return HTMLResponse(content=DASHBOARD_HTML)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gap FADE 실시간</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Pretendard', sans-serif; background:#0a0a0f; color:#e0e0e0; }
  .header { padding:16px 24px; background:#12121a; border-bottom:1px solid #1e1e2e; display:flex; justify-content:space-between; align-items:center; }
  .header h1 { font-size:18px; color:#fff; }
  .header .live { color:#4ecdc4; font-size:12px; animation: blink 1s infinite; }
  @keyframes blink { 50% { opacity:0.5; } }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:1px; background:#1e1e2e; padding:1px; }
  .card { background:#12121a; padding:20px; }
  .card h2 { font-size:13px; color:#666; margin-bottom:12px; letter-spacing:0.5px; }
  .big-num { font-size:32px; font-weight:700; }
  .big-num.positive { color:#4ecdc4; }
  .big-num.negative { color:#ff6b6b; }
  .row { display:flex; gap:24px; margin-top:8px; }
  .row .label { font-size:10px; color:#666; }
  .row .val { font-size:16px; font-weight:600; }
  table { width:100%; border-collapse:collapse; font-size:12px; margin-top:8px; }
  th { text-align:left; padding:6px 8px; color:#666; font-size:10px; border-bottom:1px solid #1e1e2e; }
  td { padding:6px 8px; border-bottom:1px solid #0a0a0f; }
  .long { color:#4ecdc4; }
  .short { color:#ff6b6b; }
  .pos { color:#4ecdc4; }
  .neg { color:#ff6b6b; }
  .badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; }
  .badge.executed { background:#1a3a2a; color:#4ecdc4; }
  .badge.pending { background:#3a3a1a; color:#ffd93d; }
  .badge.failed { background:#3a1a1a; color:#ff6b6b; }
  .badge.skipped { background:#1a1a2e; color:#666; }
  .full-width { grid-column: 1 / -1; }
  .refresh-info { font-size:11px; color:#444; margin-top:8px; }
  .strat-detail { font-size:12px; color:#999; line-height:2.0; }
  .strat-detail b { color:#e0e0e0; }
  .tag { background:#1a1a2e; padding:6px 12px; border-radius:6px; font-size:11px; display:inline-block; }
  .tag-active { background:#4ecdc4; color:#000; font-weight:600; }
</style>
</head>
<body>

<div class="header">
  <h1>Gap FADE 실시간 대시보드</h1>
  <div><span class="live">● LIVE</span> <span id="clock" style="color:#666;font-size:12px;margin-left:8px"></span></div>
</div>

<div class="grid">
  <!-- 전략 상세 -->
  <div class="card full-width" style="background:#0e1117;border-left:3px solid #4ecdc4;padding:16px 24px;">
    <div style="font-size:15px;font-weight:700;color:#4ecdc4;margin-bottom:12px;">전략: 오버나이트 갭 FADE (평균회귀)</div>
    <div class="strat-detail">
      미국 주식시장은 하루 6.5시간만 열린다. 장이 닫힌 사이 뉴스/이벤트로 <b>갭</b>(전일 종가 vs 당일 시가 차이)이 발생한다.<br>
      이 갭은 통계적으로 <b>당일 장중에 메워지는 경향</b>이 있다 (평균회귀). 이걸 이용한다.<br><br>
      <b>갭업(+) 발생 → 숏(SHORT)</b> 진입 — 가격이 내려올 것에 베팅<br>
      <b>갭다운(-) 발생 → 롱(LONG)</b> 진입 — 가격이 올라올 것에 베팅<br>
      장 시작(22:35 KST)에 진입, 장 마감(04:55 KST)에 청산. <b>당일 매매</b>.
    </div>

    <div style="margin-top:16px;margin-bottom:8px;font-size:12px;color:#888;font-weight:600;">진입 조건 (스코어링 시스템)</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
      <div class="tag"><span style="color:#666;">1.</span> 갭 > 0.5%</div>
      <div class="tag"><span style="color:#666;">2.</span> 전일 캔들 몸통 > 1% + 갭과 같은 방향</div>
      <div class="tag"><span style="color:#666;">3.</span> 연속 갭 (전일과 같은 방향)</div>
      <div class="tag"><span style="color:#666;">4.</span> 20일 이동평균 이탈</div>
      <div class="tag tag-active">3개 이상 충족 시 거래</div>
    </div>

    <div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:16px;padding-top:12px;border-top:1px solid #1e1e2e;">
      <div><div style="font-size:9px;color:#666;">종목</div><div style="font-size:13px;font-weight:600;">GOOGL  NVDA  TSLA</div></div>
      <div><div style="font-size:9px;color:#666;">레버리지</div><div style="font-size:13px;font-weight:600;">10x</div></div>
      <div><div style="font-size:9px;color:#666;">플랫폼</div><div style="font-size:13px;font-weight:600;">Binance Futures</div></div>
      <div><div style="font-size:9px;color:#666;">스캔</div><div style="font-size:13px;font-weight:600;">22:35 KST</div></div>
      <div><div style="font-size:9px;color:#666;">청산</div><div style="font-size:13px;font-weight:600;">04:55 KST</div></div>
    </div>

    <div style="margin-top:12px;font-size:11px;color:#555;">
      백테스트 (9개월): 195거래 | 승률 55% | 수익 +136% (10x, 슬리피지 반영) | Sharpe 1.83
    </div>
  </div>

  <!-- 계좌 잔고 -->
  <div class="card">
    <h2>계좌 잔고</h2>
    <div class="big-num positive" id="balance">$---</div>
    <div class="row">
      <div class="item"><div class="label">가용 잔고</div><div class="val" id="available">---</div></div>
      <div class="item"><div class="label">미실현 손익</div><div class="val" id="upnl">---</div></div>
    </div>
  </div>

  <!-- 현재 가격 -->
  <div class="card">
    <h2>현재 주가</h2>
    <div id="prices" style="display:flex;gap:16px;flex-wrap:wrap;"></div>
  </div>

  <!-- 보유 포지션 -->
  <div class="card full-width">
    <h2>보유 포지션</h2>
    <table>
      <thead><tr><th>종목</th><th>방향</th><th>수량</th><th>진입가</th><th>현재가</th><th>손익</th><th>레버</th></tr></thead>
      <tbody id="positionsBody"><tr><td colspan="7" style="color:#444">포지션 없음</td></tr></tbody>
    </table>
  </div>

  <!-- 시그널 내역 -->
  <div class="card">
    <h2>시그널 내역</h2>
    <table>
      <thead><tr><th>날짜</th><th>종목</th><th>방향</th><th>점수</th><th>갭</th><th>상태</th></tr></thead>
      <tbody id="signalsBody"></tbody>
    </table>
  </div>

  <!-- 거래 내역 -->
  <div class="card">
    <h2>거래 내역</h2>
    <table>
      <thead><tr><th>날짜</th><th>종목</th><th>방향</th><th>진입가</th><th>청산가</th><th>손익</th></tr></thead>
      <tbody id="tradesBody"><tr><td colspan="6" style="color:#444">거래 없음</td></tr></tbody>
    </table>
  </div>
</div>

<div style="padding:8px 24px;" class="refresh-info">10초마다 자동 새로고침</div>

<script>
async function refresh() {
  try {
    // Account
    const acct = await (await fetch('/api/live/account')).json();
    if (!acct.error) {
      document.getElementById('balance').textContent = '$' + acct.balance.toFixed(2);
      document.getElementById('balance').className = 'big-num ' + (acct.balance >= 100 ? 'positive' : 'negative');
      document.getElementById('available').textContent = '$' + acct.available.toFixed(2);
      const upnl = acct.unrealizedPnl;
      document.getElementById('upnl').textContent = (upnl >= 0 ? '+' : '') + '$' + upnl.toFixed(2);
      document.getElementById('upnl').className = 'val ' + (upnl >= 0 ? 'pos' : 'neg');

      // Positions
      const pb = document.getElementById('positionsBody');
      if (acct.positions.length === 0) {
        pb.innerHTML = '<tr><td colspan="7" style="color:#444">포지션 없음</td></tr>';
      } else {
        pb.innerHTML = acct.positions.map(p => `
          <tr>
            <td>${p.symbol}</td>
            <td class="${p.direction.toLowerCase()}">${p.direction}</td>
            <td>${p.qty}</td>
            <td>$${p.entryPrice.toFixed(2)}</td>
            <td>$${p.markPrice.toFixed(2)}</td>
            <td class="${p.pnl >= 0 ? 'pos' : 'neg'}">${p.pnl >= 0 ? '+' : ''}$${p.pnl.toFixed(2)}</td>
            <td>${p.leverage}x</td>
          </tr>
        `).join('');
      }
    }

    // Prices
    const prices = await (await fetch('/api/live/prices')).json();
    if (!prices.error) {
      document.getElementById('prices').innerHTML = Object.entries(prices).map(([k,v]) =>
        `<div><div style="font-size:10px;color:#666">${k}</div><div style="font-size:18px;font-weight:600">$${v.toFixed(2)}</div></div>`
      ).join('');
    }

    // Signals
    const signals = await (await fetch('/api/live/signals')).json();
    document.getElementById('signalsBody').innerHTML = signals.slice(0, 10).map(s => `
      <tr>
        <td>${s.date}</td>
        <td>${s.ticker}</td>
        <td class="${s.direction === 'LONG' ? 'long' : 'short'}">${s.direction}</td>
        <td>${s.score}/4</td>
        <td>${s.gap_pct > 0 ? '+' : ''}${s.gap_pct.toFixed(2)}%</td>
        <td><span class="badge ${s.status}">${s.status}</span></td>
      </tr>
    `).join('');

    // Trades
    const trades = await (await fetch('/api/live/trades')).json();
    if (trades.length > 0) {
      document.getElementById('tradesBody').innerHTML = trades.slice(0, 10).map(t => `
        <tr>
          <td>${t.date}</td>
          <td>${t.ticker}</td>
          <td class="${t.direction === 'LONG' ? 'long' : 'short'}">${t.direction}</td>
          <td>$${t.entry_price?.toFixed(2) || '?'}</td>
          <td>$${t.exit_price?.toFixed(2) || '?'}</td>
          <td class="${t.net_pnl >= 0 ? 'pos' : 'neg'}">${t.net_pnl >= 0 ? '+' : ''}$${t.net_pnl?.toFixed(2) || '?'}</td>
        </tr>
      `).join('');
    }
  } catch(e) { console.error(e); }

  document.getElementById('clock').textContent = new Date().toLocaleTimeString();
}

refresh();
setInterval(refresh, 10000);
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    print("Live Dashboard: http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
