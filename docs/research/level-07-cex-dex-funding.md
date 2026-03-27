# Level 7 — CEX-DEX Funding Rate Spread & Term Structure

> Last modified: 2026-03-27

---

## Overview

CEX(중앙화 거래소)와 DEX(탈중앙화 거래소) 간, 그리고 서로 다른 시간대의 펀딩레이트 차이를 체계적으로 수취하는 전략. Level 1의 기본 펀딩레이트 차익을 **다차원으로 확장**.

---

## Strategy 7-A: Cross-Exchange Funding Rate Spread

### Mechanism
같은 자산의 Perp이 여러 거래소에서 서로 다른 펀딩레이트로 거래된다. 높은 펀딩 거래소에서 숏, 낮은 펀딩 거래소에서 롱 → 펀딩 차이만큼 수익.

### Current Spread Data (예시)
```
BTC-PERP:
Binance 펀딩:  +0.010% / 8h (연 13.7%)
Lighter 펀딩:  +0.005% / 8h (연 6.8%)
Spread:        +0.005% / 8h (연 6.8%)

Action:
- Lighter에서 BTC Perp 롱
- Binance에서 BTC Perp 숏
- 8시간마다 0.005% 스프레드 수취
```

### Korean Stock Application
```
삼성전자 Perp (Lighter): 유일 플랫폼
→ 크로스 거래소 직접 비교 불가 (현재)

대안: 상관 자산 교차 펀딩
- Lighter SAMSUNG Perp 펀딩 vs Binance KOSPI ETF 펀딩 (향후)
- Lighter KOSPI 200 Perp vs CME KOSPI Futures 캐리
```

### Return Profile
| 항목 | 수치 |
|------|------|
| 거래소 간 펀딩 스프레드 | 0.003~0.01% / 8h |
| 연간 수익 | 4~13% (델타뉴트럴) |
| 자본 요구 | 양 거래소 마진 |
| 리스크 | 낮음 (시장 중립) |

### Tools
- **CoinGlass**: 25+ 거래소 펀딩레이트 실시간 비교
- **Loris Tools**: 크로스 거래소 스캐너
- **Arbitrage Scanner**: 자동화 알림

---

## Strategy 7-B: Funding Rate Term Structure

### Mechanism
펀딩레이트는 시장 심리에 따라 주기적 패턴을 보인다. 이 패턴의 "term structure"를 분석하여 펀딩 전환점(inflection point)에서 포지션 조정.

### Patterns Observed
```
Pattern 1: Funding Momentum
높은 양(+) 펀딩 → 다음 주기도 양(+) 유지 확률 70%
높은 음(-) 펀딩 → 다음 주기도 음(-) 유지 확률 65%
→ 추세 추종 가능

Pattern 2: Funding Mean Reversion
극단적 펀딩 (>0.05% / 8h) → 72시간 내 평균 회귀 확률 80%
→ 역추세 진입 가능

Pattern 3: Weekend Funding Compression
주말 거래량 감소 → 펀딩레이트 압축
월요일 아시아 개장 → 펀딩 급변
→ 주말 포지션 → 월요일 수렴 차익
```

### Execution
```
Strategy: Funding Mean Reversion

1. 삼성전자 Perp 펀딩: +0.08% / 8h (극단적 양)
2. 판단: 72시간 내 평균 회귀 예상
3. Action: 현물 롱 + Perp 숏 (기본 펀딩 수취)
   + 펀딩 하락 시 Perp 숏 비중 확대
4. 펀딩 정상화 (0.01~0.02%) 시 추가 숏 청산
```

### Return Profile
| 항목 | 수치 |
|------|------|
| 펀딩 추세 추종 수익 | 5~15% 연간 |
| 펀딩 평균 회귀 수익 | 3~10% 연간 |
| 주말 압축 수익 | 2~5% 연간 |
| **복합 연간 기대 수익** | **10~25%** |

### Critical Finding
> "Only 40% of apparent funding rate arbitrage opportunities generate positive returns after transaction costs. Forced exits occur in 95% of opportunities. Safe only up to 3x leverage."

→ **레버리지 3x 이하 유지가 생존 조건**

---

## Strategy 7-C: KRW Stablecoin Carry Trade (간접)

### Mechanism
한국 원화 금리와 스테이블코인 수익률 간 차이를 활용한 캐리 트레이드.

```
한국 기준금리: 3.0% (예시)
USDC DeFi 렌딩 수익: 8~15%
스프레드: 5~12%

Execution:
1. 원화 차입 (한국 은행 대출, 3~4%)
2. 원화 → USDC 전환
3. USDC를 DeFi 렌딩 프로토콜에 예치 (8~15%)
4. 스프레드 수익 = DeFi 수익 - 차입 비용 - 환전 비용
```

### Enhancement with Perp
```
USDC를 Lighter DEX 마진으로 활용:
1. 원화 차입 → USDC 전환 → Lighter 입금
2. 삼성전자 현물 롱 (KRX) + Perp 숏 (Lighter)
3. 수익 = 펀딩레이트 수취 + 캐리 스프레드
4. 복합 수익: 15~30%

Risk: 환율 변동 (KRW 약세 → USDC 환산 이익 / KRW 강세 → 손실)
```

### Return Profile
| 항목 | 수치 |
|------|------|
| 순 캐리 스프레드 | 5~12% 연간 |
| 환율 리스크 | ±5~10% 연간 |
| 펀딩레이트 추가 | 10~19% 연간 |
| **복합 기대 수익 (환헤지 시)** | **12~25%** |

### Risks
- 환율 리스크 (KRW/USD) — 헤지 필수
- 자본통제 위반 가능성 — 법률 자문 필수
- 금리 변동 — 캐리 스프레드 축소 가능

---

## Combined Evaluation (Level 7)

| 기준 | 7-A (CEX-DEX) | 7-B (Term Str) | 7-C (Carry) |
|------|-------------|---------------|------------|
| 실현가능성 | 6 | 7 | 5 |
| 수익성 | 7 | 7 | 8 |
| 리스크 수준 | 8 | 6 | 4 |
| 자본 효율성 | 5 | 6 | 6 |
| 확장성 | 6 | 5 | 4 |
| 규제 리스크 | 6 | 7 | 3 |
| **총점** | **38/60 (B)** | **38/60 (B)** | **30/60 (C+)** |

### Verdict
**수익성 > 리스크**: 7-A, 7-B는 YES / 7-C는 CONDITIONAL
- CEX-DEX 스프레드(7-A): 안정적이나 한국 주식 직접 적용 제한
- Term Structure(7-B): 데이터 분석 역량이 수익을 결정
- Carry Trade(7-C): **최고 수익 잠재력이나 규제 리스크가 최대 장벽**
- Level 7은 전반적으로 **분석 인프라 투자**가 선행되어야 하는 레벨
