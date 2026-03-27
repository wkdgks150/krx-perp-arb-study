# Level 6 — Weekend Effect & Overnight Drift Exploitation

> Last modified: 2026-03-27

---

## Overview

학술 연구로 검증된 두 가지 시장 이상 현상(anomaly)을 KRX-Perp DEX 구조에서 체계적으로 수익화:
1. **Weekend Effect**: 주말 크립토 움직임이 월요일 주식 수익률을 예측
2. **Overnight Drift**: 미국 주식 프리미엄의 100%가 야간 세션에서 발생

---

## Strategy 6-A: Weekend Effect Arbitrage

### Academic Foundation
> "Weekend cryptocurrency returns significantly predict Monday stock returns, especially for altcoins, with higher Sharpe ratios and lower maximum drawdowns than weekday strategies."
> — ScienceDirect, 2025

### Mechanism
주말 동안 기관 마켓메이커가 활동을 줄이면서 수급 불균형이 발생. 크립토 시장의 주말 움직임이 월요일 주식시장 방향을 선행한다.

```
[금 15:30 KRX 폐장] → [주말 크립토 거래 65시간] → [월 09:00 KRX 개장]

주말 크립토 하락 → 월요일 KOSPI 하락 확률 높음
주말 크립토 상승 → 월요일 KOSPI 상승 확률 높음
```

### Execution
```
토요일~일요일: 크립토 시장 모니터링

Signal: BTC 주말 수익률 < -3%

Action (일요일 저녁):
1. Lighter KOSPI 200 Perp 숏 진입
2. 또는 삼성전자 Perp 숏 진입
3. 월요일 KRX 개장 직후 갭다운 확인
4. 수렴 시 청산

Stop-loss: BTC 반등 시 즉시 청산
```

### Return Profile
| 항목 | 수치 |
|------|------|
| 주말 시그널 정확도 | 60~70% (학술 연구) |
| 이벤트당 기대 수익 | 0.5~3% |
| 연간 주말 | 52회 |
| 의미 있는 시그널 | 15~25회/년 |
| **연간 기대 수익** | **10~25%** |

---

## Strategy 6-B: Overnight Drift Capture

### Academic Foundation
> "Nearly 100% of the U.S. equity premium is earned between 2:00 AM and 3:00 AM ET. Inventory management by intermediaries creates overnight returns."
> — Federal Reserve Bank of New York, Staff Reports

### The Korean Connection
- 한국 개인투자자가 미국 야간 거래의 **40% 차지** (2025 데이터)
- 한국 투자자의 레버리지 ETF 활동이 야간 프리미엄에 기여
- KST 기준으로 미국 야간 세션 = 한국 비즈니스 시간

```
Timeline (KST):
07:00-09:00: 미국 야간 세션 (overnight drift 발생)
09:00-15:30: KRX 장중
15:30-23:30: 미국 프리마켓 + 정규장 개장
23:30-07:00: 미국 정규장 (overnight drift 시작)
```

### Execution
```
Pattern: 미국 야간 세션에 주식 프리미엄 발생

Action (한국 시간 기준):
1. 23:00 KST: 미국 시장 마감 → 야간 세션 시작
2. Lighter 삼성/KOSPI Perp: 미국 야간 동안 관찰
3. 상승 drift 감지 시: KRX 관련 Perp 롱 진입
4. 07:00~09:00 KST: Drift peak → 청산 또는 KRX 개장 연계

Variant: KOSPI-연동 야간 전략
- 미국 반도체 지수(SOX) 야간 움직임 → 삼성/하이닉스 Perp에 선반영
- SOX +1% 야간 → 삼성 Perp 롱 → KRX 개장 시 수렴
```

### Return Profile
| 항목 | 수치 |
|------|------|
| 야간 drift 크기 | 0.2~1.0% (일일) |
| 연간 거래일 | ~250일 |
| 유효 시그널 비율 | 40~50% |
| **연간 기대 수익** | **12~30%** |

---

## Strategy 6-C: Asian Gap Trading

### Mechanism
아시아 시장 개장 시 전일 미국/유럽 세션의 가격 변동을 "갭"으로 반영. 이 갭은 Perp에서 이미 반영되었으나, KRX 현물은 아직 반영되지 않은 경우 차익 발생.

### Execution
```
미국 장 마감 (06:00 KST): S&P 500 -2%
Lighter KOSPI 200 Perp: 이미 -1.5% 반영
KRX 개장 (09:00 KST): KOSPI 200 현물 -1.8% 갭다운 예상

Case A: Perp < KRX 예상 → Perp 롱 (저평가)
Case B: Perp > KRX 예상 → Perp 숏 (고평가)
```

### Return Profile
| 항목 | 수치 |
|------|------|
| 갭 괴리 | 0.2~1.5% |
| 연간 유효 기회 | 80~120회 |
| 승률 | 55~60% |
| **연간 기대 수익** | **10~20%** |

---

## Combined Evaluation (Level 6)

| 기준 | 6-A (Weekend) | 6-B (Overnight) | 6-C (Asian Gap) |
|------|-------------|-----------------|----------------|
| 실현가능성 | 8 | 7 | 8 |
| 수익성 | 7 | 8 | 7 |
| 리스크 수준 | 5 | 6 | 6 |
| 자본 효율성 | 8 | 7 | 8 |
| 확장성 | 5 | 5 | 5 |
| 규제 리스크 | 7 | 7 | 7 |
| **총점** | **40/60 (B+)** | **40/60 (B+)** | **41/60 (B+)** |

### Verdict
**수익성 > 리스크**: YES
- 학술 연구로 **통계적 유의성 검증**된 전략들
- 방향성 베팅이나, 확률적 우위(edge)가 존재
- 한국 개인투자자의 높은 해외 야간 거래 비중 → 구조적 기회
- **자동화 적합**: 시간 기반 시그널 → 봇으로 실행 최적
- KRX 타임 갭이 핵심 수익원 — 갭이 존재하는 한 엣지 지속
