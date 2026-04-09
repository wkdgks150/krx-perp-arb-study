# Session Handoff — 2026-04-09 DEX↔전통시장 구조적 스프레드 연구

## Status

DEX(Hyperliquid) ↔ 해외선물(CME ES) / 나스닥(SPY) 간 "김치프리미엄"급 상시 갭 존재 여부를 조사하고, 실제 Hyperliquid API 데이터(500시간+)로 백테스트 완료.

**핵심 발견:**

| 비교 | 갭 | σ | 성격 |
|------|-----|---|------|
| HL vs CME ES | -74 bps (상시) | 8 bps | 금리 캐리 — 공정가치 차이 |
| HL vs SPY×10 | +33 bps (97% 시간) | 19 bps | **진짜 DEX 프리미엄** |
| 펀딩레이트 | -0.09 bps/h | — | 연 -8.3% (롱 수취) |

**결론:** 김치프리미엄(200-500bps, 일방향, 차익거래 불가)과는 규모·성격 모두 다름. DEX 프리미엄은 +33bps로 작고, 진동하며, 차익거래 가능하지만 수수료 후 margin 얇음. 가장 확실한 수익원은 펀딩레이트 수확(연 35-71%).

## Key Decisions

1. **HL vs ES 갭(-74bps)은 차익거래 대상 아님** — CME 선물의 금리 캐리 프리미엄(~86bps)이 원인. 공정가치 차이.
2. **HL vs SPY(현물) 갭(+33bps)이 진짜 DEX 프리미엄** — 참여자 편향(롱 과열)이 원인. 진동폭 작아 단독 전략으로는 약함.
3. **펀딩레이트 수확이 최적** — 연 35%(5x)~71%(10x), 델타뉴트럴, 패시브. 기존 Gap FADE 봇과 보완적 운영 가능.
4. **중간 산출물(v1, v2, compare) 삭제** — 최종 `dex_basis_v3.py`만 보존.

## Open Issues

1. **SPY 매칭 데이터 105개뿐** — yfinance 1h 데이터 제한(~30일). SPY는 정규장만 제공 → HL과 겹치는 시간 적음. 장기 검증에는 유료 데이터 소스 필요 (Polygon.io, EODHD 등).
2. **SP500 perp 역사 3주** — 2026-03-18 출시. 통계적 유의성 제한. 데이터 축적 후 재검증 필요.
3. **헤지 실행 미검증** — 펀딩 수확은 SPY/ES 숏 헤지 필수인데, 실제 동시 실행(HL+브로커) 인프라 미구축.
4. **리서치 문서 미정리** — 에이전트가 생성한 `docs/research/dex-perp-structural-premium-study.md` 내용 검증 및 정리 필요.

## Next Steps

1. **데이터 축적**: `dex_basis_v3.py`를 cron으로 주기적 실행하여 HL SP500 perp 가격/펀딩 데이터 로컬 저장 (SQLite or CSV). 3개월 이상 축적 후 통계 재검증.
2. **펀딩 수확 전략 상세 설계**: `us-stock-perp-study.md`의 Strategy A(주말갭)/B(실적갭)/C(야간드리프트)와 펀딩 수확을 결합한 복합 전략 설계.
3. **헤지 인프라**: HL API + 브로커(Alpaca/IBKR) 동시 실행 파이프라인 구축. `bot/hl_executor.py` 확장.
4. **리서치 문서 업데이트**: `00-master-evaluation.md`에 "DEX↔전통시장 스프레드" 전략 추가 (Level 7 또는 신규 레벨).
5. **Cleanup**: `dex-perp-structural-premium-study.md` 내용 검증 후 기존 리서치 체계에 통합 또는 삭제.

## Files Modified

| 파일 | 상태 | 설명 |
|------|------|------|
| `bot/dex_basis_v3.py` | **NEW** | 최종 분석+백테스트 스크립트 (HL API → ES/SPY 비교 → 펀딩수확 BT) |
| `docs/research/dex-perp-structural-premium-study.md` | **NEW** | 에이전트 생성 리서치 (검증 필요) |
| `bot/compare_dex_vs_existing.py` | 삭제됨 | 중간 산출물 (기존 전략 오해한 비교) |
| `bot/dex_basis_backtest.py` | 삭제됨 | v1 (SPY 매칭 실패) |
| `bot/dex_basis_v2.py` | 삭제됨 | v2 (SPY 단위 오류) |

## Context

- 유저 원래 질문: "DEX ↔ 해외선물, DEX ↔ 나스닥에 김치프리미엄 같은 상시 갭이 있는가? 있으면 백테스트."
- 초반에 기존 전략(31개 연구 + Gap FADE 봇)을 잘못 이해하여 엉뚱한 비교를 했다가 유저에게 지적받음. `us-stock-perp-study.md`가 핵심 컨텍스트였음.
- Hyperliquid API (`POST https://api.hyperliquid.xyz/info`)로 실시간 데이터 수집 가능 확인. `candleSnapshot`, `fundingHistory` 엔드포인트 사용.
- SP500 perp 티커: `xyz:SP500` (HIP-3 builder DEX, Trade[XYZ] 경유).
