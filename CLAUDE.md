# Project Agent Guide

## Project Overview

- **Project name**: KRX Perp-DEX Arbitrage Study
- **Description**: Study risk-free/low-risk arbitrage strategies between Korean stock market (KRX) and RWA perpetual DEXes
- **Owner**: personal
- **Current phase**: Research & Study
- **Tech stack**: Research project (Python for data analysis if needed later)

---

## Session Startup Checklist

On every new session:
1. `git fetch --dry-run` → inform user of remote changes.
2. `git status` → inform user of uncommitted local changes.
3. Check `docs/` to understand current project progress.
4. Verify entry in `/Applications/GitHub/projects.yaml`.

---

## Project Structure

```
docs/
├── BPD.md                                # Project background & objectives
├── research/
│   ├── 00-master-evaluation.md           # Grand ranking (all levels)
│   ├── 01-market-landscape.md            # RWA perp-DEX market overview
│   ├── 02-strategies.md                  # Level 1: Basic strategies
│   ├── 03-korean-market-constraints.md   # KRX-specific constraints
│   ├── 04-risk-analysis.md               # Risk analysis framework
│   ├── 05-evaluation.md                  # Level 1 evaluation matrix
│   ├── 06-references.md                  # Academic papers & sources
│   ├── level-02-adr-cross-asset.md       # Level 2: ADR/GDR & cross-asset
│   ├── level-03-event-driven.md          # Level 3: Earnings & index rebalancing
│   ├── level-04-pairs-stat-arb.md        # Level 4: Pairs & statistical arb
│   ├── level-05-market-making.md         # Level 5: Korean stock perp MM
│   ├── level-06-weekend-overnight.md     # Level 6: Weekend & overnight drift
│   ├── level-07-cex-dex-funding.md       # Level 7: CEX-DEX funding spreads
│   ├── level-08-flash-loan-cross-chain.md # Level 8: Flash loan & cross-chain
│   ├── level-09-lp-insurance.md          # Level 9: LP vault & insurance mining
│   └── level-10-future-tokenized.md      # Level 10: 2027 tokenized securities
├── CHANGELOG.md
└── DECISIONS.md
```

---

## Research Scope

### Core Question
> 한국 주식시장(09:00-15:30 KST)과 24/7 RWA perp-DEX 사이에서 취할 수 있는 무위험/저위험 차익거래 전략은 무엇인가?

### Key Platforms
- **Lighter DEX**: Only platform with Korean stocks (Samsung, SK Hynix, Hyundai, KOSPI 200)
- **Hyperliquid**: S&P 500 perps, largest DEX by active traders
- **Ostium**: Dedicated RWA perp-DEX
- **Drift**: Solana-based, 100+ assets

### Strategies Under Study
1. Funding Rate Arbitrage
2. Basis Trading
3. Off-Hours Price Dislocation
4. Cross-Market Arbitrage
5. Delta-Neutral Volatility Strategy

---

## Commit Convention

- Format: `type: description` — Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Korean allowed in descriptions.

---

## Notes

1. This is a research-first project. Code comes later (if at all).
2. All research documents go in `docs/research/`.
3. Decisions and direction changes go in `docs/DECISIONS.md`.
4. If progressing to implementation: Python for data collection & backtesting.
