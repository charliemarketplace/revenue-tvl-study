# Revenue-TVL Study

Econometric analysis linking L2 DeFi ecosystem growth to sequencer fee revenue.

## The Core Question

> If OP Mainnet reaches $500M / $750M / $1B in TVL, what fee revenue should we expect?

## The Theory

**TVL doesn't cause fees. Activity does.**

TVL is a stock variable—it changes slowly, mostly from price effects. Fees are a flow—they spike with trading, borrowing, on-chain activity. Regressing fees on TVL directly would be spurious.

The causal chain is:

```
ΔTVL → Δactivity → Δfees
```

- **TVL enables activity:** Deeper liquidity allows larger trades, more collateral enables more borrowing
- **Activity generates fees:** Swaps, borrows, liquidations consume gas

To project fees, we need to understand both links.

## The Model

### Link 1: TVL Changes → Activity Changes

```
Δlog(dex_vol)ᵢₜ    = αᵢ + β₁ Δlog(tvl)ᵢₜ + β₂(volatility)ₜ + εᵢₜ
Δlog(borrow_vol)ᵢₜ = αᵢ + γ₁ Δlog(stable_supply)ᵢₜ + γ₂(volatility)ₜ + εᵢₜ
```

**Interpretation:** When TVL grows 1%, DEX volume grows β₁%. Volatility amplifies activity regardless of TVL.

### Link 2: Activity Changes → Fee Changes

```
Δlog(fees)ᵢₜ = αᵢ + δ₁ Δlog(dex_vol)ᵢₜ + δ₂ Δlog(borrow_vol)ᵢₜ + δ₃(volatility)ₜ + εᵢₜ
```

**Interpretation:** Activity elasticities tell us which flows drive fees most.

### Why Panel? Why Differences?

| Design Choice | Reason |
|---------------|--------|
| Panel (Base + Arb) | Pool data, estimate chain fixed effects, more statistical power |
| Differences (Δlog) | Avoid spurious regression, capture causal claim about *changes* |
| Hold out OP | Validate model before projecting |

## Data

**Daily observations, 2025**

| Variable | Type | Description |
|----------|------|-------------|
| fees | Flow | Sequencer fee revenue (ETH) |
| dex_vol | Flow | DEX sell volume (BTC + ETH + stablecoins) |
| borrow_vol | Flow | Stablecoin borrow volume |
| tvl | Stock | Total value locked |
| stable_supply | Stock | Stablecoin supply |
| eth_volatility | Exogenous | Daily price range (high - low) / open |

**Panel structure:**
- Estimation: Base + Arbitrum
- Validation: OP Mainnet (held out)

## Projection via Monte Carlo

Point estimates at TVL targets are incomplete. The *path* to $1B TVL matters—fast growth in a volatile market differs from slow growth in a calm one.

```
┌─────────────────────────────────────────────────────────────┐
│                    MONTE CARLO SIMULATION                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Define TVL target (e.g., $750M)                        │
│  2. Sample N growth paths (ΔTVL sequences)                 │
│  3. For each path:                                         │
│       Apply Link 1 coefficients → Δactivity sequence       │
│       Apply Link 2 coefficients → Δfees sequence           │
│       Sum to cumulative fee revenue                        │
│  4. Output: distribution of outcomes (P10 / P50 / P90)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Uncertainty sources:**
- Parameter uncertainty: coefficient standard errors
- Path uncertainty: many ΔTVL sequences reach the same endpoint
- Volatility scenarios: calm vs turbulent markets

## From Coefficients to Recommendations

The estimated coefficients reveal which levers matter most:

```
If β₁ (TVL → DEX vol) > γ₁ (stable supply → borrow vol):
    → DEX liquidity drives more activity per dollar than lending
    → Prioritize POL, DEX incentives

If δ₁ (DEX vol → fees) > δ₂ (borrow vol → fees):
    → Trading is more fee-generative than borrowing
    → Target high-volume trading protocols
```

| Coefficient Finding | Potential Recommendation |
|--------------------|--------------------------|
| High DEX-TVL elasticity | Protocol-owned liquidity in key pairs |
| High stable-borrow elasticity | Incentivize stablecoin supply growth |
| Low activity/TVL vs benchmark | DevX investment to increase utilization |
| Missing TVL categories vs peers | Target specific protocol types (BTC, perps) |

## Directory Structure

```
revenue-tvl-study/
├── data/
│   ├── raw/                    # Dune exports, DefiLlama pulls
│   └── processed/              # Cleaned panel in differences
├── queries/                    # Dune SQL
├── scripts/
│   ├── 01_load_and_clean.py    # Build panel, compute Δlog features
│   ├── 02_diagnostics.py       # Stationarity, correlation checks
│   ├── 03_estimate_model.py    # Panel regressions (Link 1 + Link 2)
│   ├── 04_validate_op.py       # Out-of-sample test on OP
│   ├── 05_monte_carlo.py       # Simulate fee projections
│   └── generate_report.py      # Charts + findings
├── models/                     # Reusable estimation code
├── visuals/                    # Highcharts HTML
├── tests/
└── report.html
```

## Summary

```
Theory:     ΔTVL → Δactivity → Δfees
Method:     Panel model in differences (Base + Arb)
Validation: Hold-out test on OP
Projection: Monte Carlo simulation of growth paths
Output:     Fee distributions at TVL targets + actionable recommendations
```
