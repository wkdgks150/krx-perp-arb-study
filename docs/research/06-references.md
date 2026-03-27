# 06 — References & Sources

> Last modified: 2026-03-27

---

## Academic Papers

### Perpetual Futures Pricing & Mechanics
1. **Ackerer, Hugonnier & Jermann** — "Perpetual Futures Pricing"
   - Wharton School, University of Pennsylvania
   - No-arbitrage pricing framework for perpetual contracts
   - Key finding: Funding specifications must match spot to ensure futures = expected spot

2. **Dai, Li & Yang** — "Arbitrage in Perpetual Contracts"
   - SSRN Working Paper
   - Persistent price discrepancies beyond transaction fees
   - Clamping function creates model-free no-arbitrage bounds

3. **He et al.** — "Fundamentals of Perpetual Futures"
   - arXiv: 2212.06888
   - Early years showed frequent arbitrage deviations; trend toward efficiency
   - Markets more efficient in 2025 vs 2020-2021

### Market Structure & Efficiency
4. **MDPI (Mathematics)** — "The Two-Tiered Structure of Cryptocurrency Funding Rate Markets"
   - CEXs dominate price discovery (61% higher integration than DEXs)
   - Information flows CEX → DEX (zero reverse causality)
   - Transaction costs prevent full arbitrage elimination

5. **He, Yang & Zhou** — "Arbitrage on Decentralized Exchanges"
   - arXiv: 2507.08302
   - Cross-exchange arbitrage mechanics and limitations

### Risk & Return Analysis
6. **ScienceDirect (2025)** — "Exploring Risk and Return Profiles of Funding Rate Arbitrage on CEX and DEX"
   - Maximum return: 115.9% over 6 months (low-volatility conditions)
   - Maximum loss: 1.92% in worst scenarios
   - 2025 average annualized: 19.26%

7. **BIS Working Paper 1087** — "Crypto Carry"
   - Bank for International Settlements
   - Basis trading and carry in crypto markets

---

## Industry Reports & Analysis

### Market Landscape
- [RWA.io — Best RWA Perps Exchange in 2026](https://www.rwa.io)
- [Perpetual DEX 2026: 3 Trends Reshaping Crypto Trading](https://blog.ju.com)
- [CoinDesk — S&P 500 Perpetual Futures on Hyperliquid](https://www.coindesk.com)
- [CryptoTimes — Hyperliquid Record 231K Active Traders](https://www.cryptotimes.io)

### Funding Rate & Arbitrage
- [Bitcoin.com — How Funding Rates Work on Perp DEXs (2026)](https://www.bitcoin.com)
- [CoinCryptoRank — Funding Rate Arbitrage Complete Guide](https://coincryptorank.com)
- [AmberData — Ultimate Guide to Funding Rate Arbitrage](https://blog.amberdata.io)
- [DEM Exchange — Delta-Neutral Approach for Steady Returns](https://blog.dem.exchange)
- [27Sphere — Funding Rate Arbitrage Technical Deep Dive](https://dev.to/27sphere)
- [BSIC (Bocconi) — Perpetual Complexity: Arbitrage Mechanics Part 1](https://bsic.it)

### Korean Market
- [TradingHours — KRX Market Hours](https://www.tradinghours.com/markets/krx)
- [Clearstream — Settlement Process South Korea](https://www.clearstream.com)
- [CFI — Kimchi Premium History](https://corporatefinanceinstitute.com)
- [AInvest — South Korea Stablecoin Surge](https://www.ainvest.com)
- [Yahoo Finance — South Korea Tokenized Securities Bill](https://finance.yahoo.com)
- [Law.Asia — Korea Stablecoin Regulation Framework](https://law.asia)

### Platform-Specific
- [Lighter Protocol — ZK-Rollup Perp DEX](https://www.lighter.xyz)
- [Lighter + Chainlink Partnership](https://bitcoinethereumnews.com)
- [Ostium — $24M Funding Round (The Block)](https://www.theblock.co)
- [Hyperliquid — S&P 500 Licensed Trading](https://www.buildix.trade)
- [Drift Protocol — Institutional RWA](https://www.drift.trade)

### Security & Architecture
- [QuillAudits — Perp DEX Architecture and Security](https://www.quillaudits.com)
- [Nansen — Arbitrage on Decentralized Exchanges](https://www.nansen.ai)
- [Chainlink — State Pricing for DEX-Traded Assets](https://blog.chain.link)
- [CoinDeFi — 12 Best DEXs for Perpetual Futures (Feb 2026)](https://coingape.com)

### Market Trends
- [Signals — Perp DEX Fee Comparison (Dec 2025)](https://signals.coincodecap.com)
- [Blockhead — 2026 Crypto Stack: RWA Perpetuals](https://www.blockhead.co)
- [Traders Magazine — 24/7 Trading Price Discovery](https://www.tradersmagazine.com)

---

## Data Sources (for future backtesting)

| Source | Data Type | Access |
|--------|-----------|--------|
| Lighter DEX API | Perp prices, funding rates, OI | Public API |
| KRX Open API | Korean stock prices, volumes | 공공데이터포털 |
| Chainlink Data Feeds | Oracle prices | On-chain |
| CoinGecko/CoinGlass | Funding rate aggregation | API (free tier) |
| Yahoo Finance | KRX stock historical data | yfinance Python |

---

## Glossary

| 용어 | 영문 | 설명 |
|------|------|------|
| 무기한 선물 | Perpetual Futures | 만기 없는 선물 계약 |
| 펀딩레이트 | Funding Rate | Perp 가격을 현물에 수렴시키는 주기적 지불 |
| 베이시스 | Basis | 선물과 현물의 가격 차이 |
| 오라클 | Oracle | 외부 데이터를 블록체인에 공급하는 서비스 |
| 델타뉴트럴 | Delta-Neutral | 시장 방향성 무관한 포지션 |
| 김치프리미엄 | Kimchi Premium | 한국 크립토 거래소의 글로벌 대비 가격 프리미엄 |
| RWA | Real World Assets | 실물 자산 (주식, 채권, 부동산 등) |
| ZK-rollup | Zero-Knowledge Rollup | 영지식 증명 기반 L2 확장 솔루션 |
| TWAP | Time-Weighted Average Price | 시간 가중 평균 가격 |
| OI | Open Interest | 미결제 약정 |
