# Revenue-TVL Study

Econometric analysis linking L2 DeFi ecosystem characteristics to sequencer fee revenue.

## The Core Question

> If OP Mainnet reaches $500M / $750M / $1B in TVL, what fee revenue should we expect?

## Key Finding

**TVL doesn't cause fees. Activity does.**

TVL is a stock variable—it changes slowly, mostly from price effects. Fees are a flow—they spike with trading, borrowing, on-chain activity. The model shows that transaction count and ETH DEX volume are the primary drivers of fee changes, not TVL levels.

## Model Results

Single reduced-form panel regression on Base + Arbitrum (2025):

```
d_log(fees) ~ d_log(dex_vol_btc) + d_log(dex_vol_eth) + d_log(dex_vol_stable)
            + d_log(borrow_vol_stable) + d_log(stablecoin_supply) + d_log(n_tx)
            + eth_volatility + chain_fe
```

| Predictor | Coefficient | Significant? | Interpretation |
|-----------|-------------|--------------|----------------|
| d_log_n_tx | **1.83** | Yes (p<0.001) | 1% more txs → 1.8% more fees |
| d_log_dex_vol_eth | **0.61** | Yes (p=0.001) | 1% more ETH trading → 0.6% more fees |
| eth_volatility | **2.99** | Yes (p<0.001) | Volatile days = more fees |
| d_log_dex_vol_btc | 0.06 | No | Absorbed by ETH volume |
| d_log_dex_vol_stable | 0.10 | No | Not a driver |
| d_log_borrow_vol_stable | 0.09 | No | Not a driver |
| d_log_stablecoin_supply | 0.00 | No | Stock, not flow |
| chain_base | 0.00 | No | No fixed effects |

**R-squared = 0.589** — Model explains 59% of daily fee variation.

### Validation on OP Mainnet (Held Out)

| Metric | Value |
|--------|-------|
| Correlation (pred vs actual) | 0.72 |
| Within 1 std | 79% |
| Within 2 std | 96% |

## Monte Carlo Projections

100,000 simulations over 365 days, starting from OP current state ($292M TVL, 0.65 ETH/day):

| TVL Bucket | % of Paths | Median Annual Fees | Daily Avg |
|------------|------------|-------------------|-----------|
| <$400M | 62% | 334 ETH | 0.9 ETH |
| $400-500M | 16% | 337 ETH | 0.9 ETH |
| $500-750M | 17% | 343 ETH | 0.9 ETH |
| $750M-1B | 4% | 351 ETH | 1.0 ETH |
| >$1B | 1.5% | 362 ETH | 1.0 ETH |

**Key insight:** Paths reaching >$1B TVL only have 8% higher fees than paths staying at <$400M. TVL growth correlates with activity growth, but doesn't cause it.

## Business Recommendations

1. **Prioritize transaction count over TVL** — Transaction count has 1.83x elasticity vs 0.61x for DEX volume. More users doing more transactions = more fees.

2. **ETH trading is the DEX driver** — ETH DEX volume is the only significant trading predictor. Prioritize ETH liquidity depth and pairs.

3. **TVL growth is an outcome, not a lever** — Growing "idle" TVL won't increase fees. Focus on *active* TVL that generates transactions.

4. **Volatility is exogenous but important** — Coefficient of 3.0. Can't control but can prepare. Ensure infrastructure handles vol spikes.

## Data

**Daily observations, 2025**

| Source | Variables |
|--------|-----------|
| DeFiLlama | TVL (USD), Stablecoin supply (USDC + USDT) |
| Dune | DEX volumes (BTC/ETH/Stable), Borrow volumes, Transaction counts, Sequencer fees (ETH), ETH OHLC |

**Panel structure:**
- Estimation: Base + Arbitrum
- Validation: OP Mainnet (held out)

## Directory Structure

```
revenue-tvl-study/
├── data/
│   ├── raw/                     # Dune exports, DefiLlama pulls
│   └── processed/               # Cleaned panel, simulation results
│       ├── panel_model_ready.csv
│       ├── simulation_results.csv
│       └── simulation_summary.csv
├── queries/                     # Dune SQL
├── scripts/
│   ├── 01_load_and_clean.py     # Build panel, compute d_log features
│   ├── 02_estimate_model.py     # Panel regression with HAC SE
│   └── 03_monte_carlo_simulation.py  # 100k simulations
├── viz/
│   ├── templates/               # HTML templates with {{PLACEHOLDER}}
│   ├── data_swap.py             # Injects CSV data into templates
│   ├── 00a_tvl_raw.html         # Raw TVL over time
│   ├── 00b_fees_raw.html        # Raw fees over time
│   ├── 01_tvl_diffs_over_time.html
│   ├── 02_fees_diffs_over_time.html
│   ├── 03_ntx_vs_fees_scatter.html
│   ├── 04_volatility_vs_fees_scatter.html
│   ├── 05_dex_eth_vs_fees_scatter.html
│   ├── 06_fee_distributions_boxplot.html
│   ├── 07_tvl_bucket_summary.html
│   ├── 08_model_coefficients.html
│   ├── 09_feature_importance.html
│   ├── 10_sample_paths_500m.html
│   └── 11_summary_table.html
├── notes.md                     # Research notes
├── presentation.md              # Slide deck content
└── technical_report.md          # Pipeline documentation
```

## Running the Pipeline

```bash
# 1. Load and clean data
uv run python scripts/01_load_and_clean.py

# 2. Estimate model
uv run python scripts/02_estimate_model.py

# 3. Run Monte Carlo simulations
uv run python scripts/03_monte_carlo_simulation.py

# 4. Generate visualizations
uv run python viz/data_swap.py
```

## Summary

```
Finding:    TVL doesn't drive fees — transactions and ETH trading do
Model:      R² = 0.589, validated on held-out OP (r=0.72)
Key drivers: d_log(n_tx) = 1.83, d_log(dex_vol_eth) = 0.61, volatility = 2.99
Projection: Reaching $1B TVL yields ~362 ETH/year (~1.0 ETH/day)
Reality:    Only 5.5% of simulated paths reach $750M+ TVL
```
