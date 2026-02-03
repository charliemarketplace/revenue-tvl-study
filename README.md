# Revenue-TVL Study

Econometric analysis linking L2 DeFi ecosystem characteristics to sequencer fee revenue.

## Objective

Project OP Mainnet sequencer fee revenue at TVL targets ($500M, $750M, $1B) using Base and Arbitrum as benchmarks.

## Data

**Daily observations, full year 2025**

| Variable | Type | Source |
|----------|------|--------|
| Sequencer fees (ETH) | Flow | Dune |
| DEX volume (BTC, ETH, stablecoin sells) | Flow | Dune / DefiLlama |
| Stablecoin borrow volume | Flow | Dune / DefiLlama |
| TVL | Stock | DefiLlama |
| Stablecoin supply | Stock | DefiLlama |
| ETH price (high, low, close) | Exogenous | CoinGecko |

**Panel structure:**
- Estimation: Base + Arbitrum (~730 obs)
- Validation: OP Mainnet (held out)

## Why Panel Design?

1. **Pool information** — Learn from two chains, not one
2. **Fixed effects** — Absorb chain-specific factors (gas pricing, user base)
3. **Out-of-sample validation** — Test model on OP before projecting

## Model Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PROJECTION FLOW                               │
└─────────────────────────────────────────────────────────────────────────┘

     TVL Target                Stablecoin Supply
     (scenario)                   (scenario)
          │                            │
          ▼                            ▼
    ┌───────────┐                ┌───────────┐
    │ Capacity  │                │ Capacity  │
    │  Model A  │                │  Model B  │
    └─────┬─────┘                └─────┬─────┘
          │                            │
          ▼                            ▼
     DEX Volume ─────────┬────── Borrow Volume
       (flow)            │         (flow)
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        ┌───────────┐         ┌──────────┐
        │           │         │   ETH    │
        │ Fee Model │◀────────│Volatility│
        │           │         │(exogenous)│
        └─────┬─────┘         └──────────┘
              │
              ▼
         Fee Revenue
         (projected)
```

## Stage 1: Fee Model

**Flows explain flows.** No stock/flow mismatch.

```
log(fees_it) = αᵢ + β₁ log(dex_vol)ᵢₜ + β₂ log(borrow_vol)ᵢₜ + β₃(volatility)ₜ + ρ log(fees)ᵢ,ₜ₋₁ + εᵢₜ
```

| Term | Interpretation |
|------|----------------|
| αᵢ | Chain fixed effect |
| β₁, β₂ | Activity elasticities |
| β₃ | Volatility sensitivity |
| ρ | Fee persistence |

**Steady-state solution** (for projection, where fees_t = fees_{t-1}):

```
log(fees*) = (α + β₁X₁ + β₂X₂ + β₃X₃) / (1 - ρ)
```

## Stage 2: Capacity Models

**Stocks enable flows.** Volatility activates capacity.

```
log(dex_vol)ᵢₜ    = γᵢ + δ₁ log(tvl)ᵢₜ           + δ₂(volatility)ₜ + ηᵢₜ
log(borrow_vol)ᵢₜ = κᵢ + λ₁ log(stablecoin_supply)ᵢₜ + λ₂(volatility)ₜ + νᵢₜ
```

**Fallback (if Stage 2 regressions unstable):** Use utilization ratios directly.

```
dex_utilization    = mean(dex_vol) / mean(tvl)
borrow_utilization = mean(borrow_vol) / mean(stablecoin_supply)
```

## Projection Logic

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│  TVL = $500M   │     │  TVL = $750M   │     │  TVL = $1B     │
└───────┬────────┘     └───────┬────────┘     └───────┬────────┘
        │                      │                      │
        ▼                      ▼                      ▼
   Stage 2: Implied       Stage 2: Implied       Stage 2: Implied
   activity levels        activity levels        activity levels
        │                      │                      │
        ▼                      ▼                      ▼
   Stage 1: Projected     Stage 1: Projected     Stage 1: Projected
   fees (± CI)            fees (± CI)            fees (± CI)
```

**Uncertainty sources:**
- Parameter uncertainty → coefficient standard errors → confidence intervals
- Scenario uncertainty → vary activity ratios, volatility assumptions

## Validation

Before projection, test model on held-out OP data:

```
OP_predicted = model(OP_activity_data)
OP_residual  = OP_actual - OP_predicted
```

If residual is large, investigate why before trusting projections.

## Directory Structure

```
revenue-tvl-study/
├── data/
│   ├── raw/                    # Original exports
│   └── processed/              # Cleaned panel
├── queries/                    # Dune SQL
├── scripts/
│   ├── 01_load_and_clean.py
│   ├── 02_diagnostics.py
│   ├── 03_fee_model.py
│   ├── 04_capacity_model.py
│   ├── 05_project_scenarios.py
│   └── generate_report.py
├── models/                     # Reusable estimation code
├── visuals/                    # Highcharts HTML
├── tests/
└── report.html
```
