# 01 — RWA Perp-DEX Market Landscape

> Last modified: 2026-03-27

## Overview

RWA(Real World Assets) perpetual DEX는 전통 자산(주식, 채권, 원자재, FX)을 기초자산으로 하는 무기한 선물을 탈중앙화 거래소에서 거래할 수 있게 한다. 2024년 월 $1B 미만이던 시장이 2025년 Q4 기준 월 $1.7B(주식 perp만)으로 급성장했다.

---

## Tier 1: Market Leaders

### Lighter DEX

| 항목 | 내용 |
|------|------|
| **체인** | Ethereum L2 (ZK-rollup) |
| **한국 주식** | Samsung (005930), SK Hynix (000660), Hyundai (005380), KOSPI 200 |
| **레버리지** | 최대 10x |
| **24h 거래량** | $8.85B (2025) |
| **수수료** | 제로 (maker/taker 모두 0%) |
| **오라클** | Chainlink Data Streams + Stork |
| **특징** | RWA OI 95% 이상, 한국 주식 지원 유일 플랫폼 |

**차익거래자에게 중요한 이유:**
- 제로 수수료 → 타이트한 스프레드에서도 수익 가능
- 한국 주식 직접 지원 → KRX와의 직접 차익거래 가능
- ZK-rollup → 빠른 결제, 낮은 가스비

### Hyperliquid

| 항목 | 내용 |
|------|------|
| **체인** | 자체 L1 |
| **RWA 자산** | S&P 500, 원자재, ETF, FX 등 |
| **활성 트레이더** | 231,000명 (2026.03 기록) |
| **OI** | $6.84B |
| **수수료** | 티어별 maker/taker |
| **특징** | 2026.03 S&P 500 perp 출시 → $100M+ 일일 거래량 |

### Ostium Protocol

| 항목 | 내용 |
|------|------|
| **체인** | Arbitrum (Ethereum L2) |
| **자산** | 주식, 통화, 원자재, 글로벌 지수 |
| **레버리지** | 최대 200x |
| **누적 거래량** | $25B |
| **펀딩** | $24M Series A (General Catalyst + Jump Crypto) |
| **한국 주식** | 미지원 |

### Drift Protocol

| 항목 | 내용 |
|------|------|
| **체인** | Solana |
| **자산** | 100+ (최대 101x 레버리지) |
| **일일 거래량** | $1.089B (2025.07 기록, 230% 급증) |
| **RWA** | Drift Institutional (Securitize 파트너십) |
| **한국 주식** | 미지원 |

---

## Tier 2: Emerging Platforms

| 플랫폼 | 체인 | 특징 | 한국 주식 |
|---------|------|------|-----------|
| **Aster DEX** | - | maker 0.005% / taker 0.04% | 미확인 |
| **Parcl** | Solana | 부동산 RWA 전문 | N/A |
| **Synthetix/Kwenta** | Optimism | 선구자이나 RWA 축소 중 | 미지원 |
| **Paradex** | - | 저지연 오라클 인프라 | 미확인 |

---

## Oracle Infrastructure

### Chainlink Data Streams (업계 표준)
- 복수 거래소 데이터 수집 (Coinbase, Binance, Kraken 등)
- TWAP(Time-Weighted Average Price) 계산 → 플래시론 조작 방지
- Pull-based 모델 → 초 단위 온체인 가격 업데이트
- 청산, 마진 계산, 주문 처리에 사용

### Stork Network
- 저지연 특화 오라클
- Lighter DEX 원래 오라클 솔루션
- 급격한 시장 변동 시 빠른 결제 지원

### Mark Price vs Oracle Price
- **Mark Price**: Perp 계약 내 거래에서 산출
- **Oracle Price**: 외부 시장 데이터 온체인 피드
- **Funding Rate**: Mark ↔ Oracle 수렴 인센티브 메커니즘

---

## Fee Structure Comparison

| 플랫폼 | Maker | Taker | 비고 |
|---------|-------|-------|------|
| Lighter | 0% | 0% | 업계 유일 완전 무료 |
| Aster | 0.005% | 0.04% | ASTER 토큰 5% 할인 |
| Hyperliquid | 티어별 | 티어별 | 볼륨 기반 할인 |
| Drift | 경쟁적 | 경쟁적 | ETH perp 제로피 프로모션 |

**트렌드:** 업계 전반 수수료 하락 추세 → 차익거래자에게 유리

---

## Market Size & Growth

| 지표 | 수치 |
|------|------|
| 2024 RWA perp 월 거래량 | < $1B |
| 2025 Q4 주식 perp 월 거래량 | $1.7B |
| 2026.01 총 DEX 월 거래량 | $739B (전년 대비 800% 증가) |
| DEX 글로벌 파생상품 점유율 | 10.2% (2024 2%에서 상승) |
| 토큰화 RWA 시장 전망 (2030) | $2T~$16T (McKinsey~BCG) |

---

## Key Takeaway

**한국 주식 RWA perp 거래는 현재 Lighter DEX에서만 가능하다.** 단일 플랫폼 의존은 리스크이자 기회 — 경쟁 플랫폼이 한국 주식을 추가하면 크로스마켓 차익거래 기회가 열린다.
