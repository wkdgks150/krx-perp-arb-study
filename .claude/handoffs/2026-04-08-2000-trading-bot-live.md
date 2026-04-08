# Session Handoff — 2026-04-08 Gap FADE 트레이딩 봇 실전 배포 완료

## Status

리서치 → 백테스트 → 봇 개발 → 실전 배포까지 풀 사이클 완료.

### 완료된 것
- **리서치** (docs/research/): Level 1~10 차익거래 전략 분석, 20개 전략 백테스트, 종목별 비교
- **백테스팅 대시보드** (bot/backtest_api.py + dashboard.html): port 8000, 파라미터 슬라이더, 캔들차트+마커
- **백테스트 엔진 v2** (bot/engine.py): 슬리피지 모델링, walk-forward, 플러거블 전략 클래스, 전략 비교
- **자동매매 봇** (bot/main.py): scan → execute → close CLI, 바이낸스 선물 연동
- **바이낸스 실행기** (bot/bn_executor.py): 주식 Perp 롱/숏, ISOLATED 마진, 10x 레버리지
- **텔레그램 알림** (bot/notifier.py): 체결/청산/에러/잔고부족/연결실패 푸시
- **라이브 대시보드** (bot/live_dashboard.py): port 8001, 한글 UI, 전략 상세, 10초 자동새로고침
- **서버 배포**: DigitalOcean $6/mo (159.65.6.136), systemd 서비스, git push 자동 배포

### 실전 거래 테스트
- GOOGL LONG 0.03주 @ $319.04 → 청산 완료 (P&L -$0.008, 수수료만)
- Alpaca paper에서도 GOOGL SHORT 33주 테스트 성공
- Hyperliquid에서 GOOGL spot 매수/매도 테스트 성공 (스팟만 가능, perp 없음)

## Key Decisions

1. **전략**: Gap FADE (오버나이트 갭 역방향 베팅) — 20개 전략 중 백테스트 승률/수익 최고
2. **스코어링**: 4조건 (갭>0.5%, 전일캔들>1%+방향일치, 연속갭, MA20이탈), 3점 이상 진입
3. **종목**: GOOGL, NVDA, TSLA — 바이낸스 주식 Perp 사용 (Hyperliquid는 스팟만, 숏 불가)
4. **플랫폼 결정 과정**: Lighter DEX 한국주식 (OI $13, 죽은 시장) → Hyperliquid (스팟만, 숏 불가) → **Binance Futures** (주식 Perp, 롱+숏, 10x, 유동성 충분)
5. **레버리지**: 10x (20x에서 파산 확인됨, 10x가 수익/리스크 최적)
6. **마진**: ISOLATED 강제 (한 종목 청산이 다른 종목에 영향 없도록)
7. **서버**: DigitalOcean Singapore $6/mo (첫 시도 $4 서버는 네트워크 문제로 교체)

## Open Issues

1. **첫 실전 거래 미실행**: 오늘 밤 22:35 KST가 첫 자동 실행. 결과 모니터링 필요
2. **장외시간 체결가 0 문제**: bn_executor의 market order 응답에서 `avgPrice`가 0으로 옴 (장외시간). 장중에는 정상일 것으로 예상하나 확인 필요
3. **MSFT 미지원**: 바이낸스에 MSFTUSDT perp 없음. NVDA로 대체했으나, 원래 백테스트 최적 조합은 GOOGL+NVDA+MSFT
4. **숏 진입 시 수량 계산**: `ex.short(ticker, notional_amount)` — 내부에서 `quantity = notional / price` 계산하는데, 바이낸스 stepSize(0.01)에 맞게 반올림 필요할 수 있음
5. **서버 .env 유실**: DigitalOcean 콘솔에서 heredoc(`<<`) 안 먹힘 → echo 한 줄씩 써야 함. 재부팅 시 .env 확인 필요
6. **공개 리포**: 배포 편의상 public으로 전환함 (wkdgks150/krx-perp-arb-study). API 키는 .gitignore됨
7. **walk-forward 결과**: 2026-03 구간 -21.7% — 하락 추세장에서 FADE 약함. 시장 환경 필터 추가 검토

## Next Steps

1. **오늘 밤 22:35 KST 첫 실전 결과 확인** — 텔레그램 알림 + 대시보드 체크
2. **장중 체결가 정상 수신 확인** — `avgPrice`가 제대로 오는지
3. **1주일 실전 운영 후 성과 평가** — 승률, P&L, MDD 실측
4. **전략 개선 후보**:
   - 첫 30분 확인 필터 (FADE 92% 정확도) — scanner.py에 추가
   - 시장 환경 필터 (하락장 감지 시 거래 중단)
   - Combo 전략 (GapFade + MeanReversion 동시 충족)
5. **새 알파 탐색**: engine.py의 Strategy 클래스로 새 전략 추가 + compare_strategies()로 비교
6. **DEX 연동 재검토**: 바이낸스 주식 perp 유동성/수수료 vs Bitget(25x) vs 다른 DEX

## Files Modified

### 핵심 파일
- `bot/main.py` — 메인 CLI (scan/execute/close/status/run/dash)
- `bot/bn_executor.py` — 바이낸스 선물 실행기 (롱/숏/청산, ISOLATED 마진)
- `bot/scanner.py` — 갭 스캔 + 4조건 스코어링
- `bot/engine.py` — 백테스트 엔진 v2 (전략 프레임워크, 슬리피지, walk-forward)
- `bot/notifier.py` — 텔레그램 알림 (체결/에러/일일요약)
- `bot/live_dashboard.py` — 라이브 대시보드 (port 8001, 한글)
- `bot/backtest_api.py` — 백테스트 대시보드 API (port 8000)
- `bot/dashboard.html` — 백테스트 대시보드 UI
- `bot/storage.py` — SQLite 거래/시그널 기록
- `bot/config.py` — 전략 파라미터, API 키 로드
- `bot/hl_executor.py` — Hyperliquid 실행기 (스팟, 현재 미사용)
- `bot/.env` — API 키 (gitignore됨)
- `bot/.env.example` — 키 템플릿

### 인프라
- `deploy.sh` — 서버 원클릭 배포 (systemd 서비스 등록)
- `bot/run.sh` — cron/launchd용 래퍼 스크립트

### 리서치 문서 (docs/research/)
- 00-master-evaluation.md — 전체 레벨 통합 랭킹
- 01~06 — Level 1 기본 전략
- level-02~10 — Level 2~10 고급 전략
- us-stock-perp-study.md — 미국 주식 Perp DEX 스터디
- small-capital-rotation.md — 소자본 고회전 전략
- fee-structure-reality.md — 수수료 현실 체크

## Context

- **사용자**: 소자본 ($100), 트레이딩 경험 적음, 자동화 선호
- **API 키 보안**: 바이낸스 출금 OFF + IP 제한 (159.65.6.136), ISOLATED 마진
- **서버**: 159.65.6.136 (DigitalOcean Singapore), root 접속은 콘솔만 (SSH 비번 직접 설정)
- **자동 배포**: 서버에 `/root/auto-deploy.sh` cron 1분마다 — git push하면 자동 pull + restart
- **텔레그램**: @Gapfadebot, chat_id=2107749008
- **바이낸스**: TradFi Perps 약관 동의 완료, 선물 계좌 $100.66
- **Hyperliquid**: 지갑 0xbBb7D077...Db9853, USDC $96.45 (현재 미사용)
- **Alpaca**: Paper 계좌 연결됨 (현재 미사용)
- **리포**: https://github.com/wkdgks150/krx-perp-arb-study (public)
- **DigitalOcean 콘솔 주의**: heredoc(<<) 안 먹힘, echo로 한 줄씩 써야 함
