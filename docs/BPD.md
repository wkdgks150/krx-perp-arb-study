# BPD — KRX Perp-DEX Arbitrage Study

> **Project**: KRX Perp-DEX Arbitrage Study
> **Last modified**: 2026-03-27
> **Version**: v0.1
> **Author**: 장한

---

## 1. Problem Definition

한국 주식시장(KRX)은 평일 09:00~15:30 KST에만 운영된다 (주당 32.5시간, 전체의 19.4%). 반면 RWA 기반 perp-DEX에서는 한국 주식의 무기한 선물이 24/7 거래된다. 이 시간 비대칭이 만드는 구조적 가격 괴리에서 차익거래 기회를 체계적으로 분석한다.

---

## 2. Objective

1. KRX와 RWA perp-DEX 간 차익거래 전략 체계적 분류
2. 각 전략의 메커니즘, 수익 구조, 리스크 상세 분석
3. 한국 시장 특수 규제 반영 실현 가능성 평가
4. "무위험"의 학술적 정의 검토 + 현실적 등급 평가

---

## 3. Scope

### In Scope
- RWA perp-DEX 시장 현황 (Lighter, Hyperliquid, Ostium, Drift)
- 차익거래 전략 심층 분석 (Level 1~10)
- 한국 시장 제약 요인 (규제, 결제, 자본통제)
- 리스크 프레임워크 & 전략 평가 매트릭스

### Out of Scope (for now)
- 실제 트레이딩 봇 개발
- 백테스팅
- 세금/회계 처리 방안

---

## 4. Success Criteria

- 각 전략 레벨에 대한 Go/No-Go 판단 근거 확보
- 규제 리스크를 포함한 현실적 수익률 범위 추정
- 실행 단계 전환 시 Prerequisites 정리

---

## 5. Research Structure

| Level | Focus | Risk Profile |
|-------|-------|-------------|
| Level 1 | Basic strategies (funding rate, basis, off-hours) | Low-Medium |
| Level 2~10 | Advanced strategies (TBD — higher risk/reward) | Medium-High |

---

## 6. Roadmap

| Phase | Timeline | Goal |
|-------|----------|------|
| Phase 1 (Research) | 2026 Q1 | Level 1~10 strategy study & evaluation |
| Phase 2 (Validation) | TBD | Data collection & backtesting |
| Phase 3 (Execution) | TBD | Live strategy execution |
