# Technical Report: Revenue-TVL Study Pipeline

## Overview

This report documents the data pipeline, model specification, and results for the Revenue-TVL Study analyzing L2 sequencer fee drivers.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAW DATA                                  │
│  fees.csv, tvl.csv, dex.csv, borrow.csv, stables.csv, ohlc.csv  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   01_load_and_clean.py                          │
│  - Token classification (btc/eth/stable)                        │
│  - Merge on (chain, date)                                       │
│  - Log transforms                                                │
│  - Compute differences within chain                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    panel_model_ready.csv
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   02_estimate_model.py                          │
│  - Split: Base+Arb (train) / OP (holdout)                       │
│  - Estimate fee model with HAC SE                               │
│  - VIF, Durbin-Watson diagnostics                               │
│  - Out-of-sample validation on OP                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     Model coefficients
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               03_monte_carlo_simulation.py                      │
│  - Re-estimate model for coefficients + residuals               │
│  - Create weekly blocks from training data                      │
│  - 100k simulations, 365-day horizon                            │
│  - TVL accumulates, fees fluctuate around baseline              │
│  - Bucket by ending TVL -> fee distributions                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
           simulation_results.csv, simulation_summary.csv
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      viz/data_swap.py                           │
│  - Read CSV data                                                 │
│  - Transform to JSON                                             │
│  - Inject into HTML templates                                    │
│  - Output standalone Highcharts visualizations                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    13 interactive HTML charts
```

---

## Script 01: Data Loading and Cleaning

**Purpose:** Load raw data files and produce model-ready panel dataset.

### Input Files

| File | Description |
|------|-------------|
| `arb_op_base_tx_fees_eth_2025.csv` | Sequencer fees by chain |
| `*_tvl_no_inclusions.csv` | TVL by chain (DeFiLlama) |
| `dex_trades_2025.csv` | DEX trade volumes |
| `lending_borrow_2025.csv` | Borrow volumes |
| `*_stablecoin_marketcaps.csv` | Stablecoin supply |
| `eth_ohlc.csv` | ETH price data |
| `arb_op_base_n_tx_2025.csv` | Transaction counts |
| `tokenlist.json` | Token address classification |

### Processing Steps

1. Load each data source with date parsing
2. Classify DEX/borrow tokens into buckets (btc, eth, stable) using `tokenlist.json`
3. Merge all sources on (chain, date)
4. Compute derived columns:
   - `eth_volatility` = (high - low) / open
   - Composition shares (dex_btc_share, etc.)
5. Compute log-differences within each chain

### Output Columns

| Column | Description |
|--------|-------------|
| `d_log_fees` | Δlog(fees_eth) |
| `d_log_tvl` | Δlog(tvl_usd) |
| `d_log_dex_vol_btc` | Δlog(DEX BTC volume) |
| `d_log_dex_vol_eth` | Δlog(DEX ETH volume) |
| `d_log_dex_vol_stable` | Δlog(DEX stablecoin volume) |
| `d_log_borrow_vol_stable` | Δlog(stablecoin borrow volume) |
| `d_log_stablecoin_supply` | Δlog(stablecoin supply) |
| `d_log_n_tx` | Δlog(transaction count) |
| `eth_volatility` | (high - low) / open (level, not differenced) |

### Output Files

- `data/processed/panel_raw.csv` - Intermediate merged panel
- `data/processed/panel_model_ready.csv` - Log-differenced features

---

## Script 02: Model Estimation

**Purpose:** Estimate panel regression model with HAC standard errors.

### Model Specification

```
d_log(fees) ~ d_log(dex_vol_btc) + d_log(dex_vol_eth) + d_log(dex_vol_stable)
            + d_log(borrow_vol_stable) + d_log(stablecoin_supply) + d_log(n_tx)
            + eth_volatility + chain_fe
```

### Feature Columns

```python
FEATURE_COLS = [
    "d_log_dex_vol_btc",
    "d_log_dex_vol_eth",
    "d_log_dex_vol_stable",
    "d_log_borrow_vol_stable",
    "d_log_stablecoin_supply",
    "d_log_n_tx",
    "eth_volatility",
]
```

### Estimation Method

- OLS with HAC standard errors (Newey-West, 5 lags)
- VIF checks for multicollinearity
- Durbin-Watson test for autocorrelation

### Training/Validation Split

- Training: Base + Arbitrum (728 observations)
- Holdout: Optimism (364 observations)

### Results

| Predictor | Coefficient | Std Error | p-value | Significant |
|-----------|-------------|-----------|---------|-------------|
| const | -0.0091 | 0.024 | 0.703 | No |
| d_log_dex_vol_btc | 0.0568 | 0.176 | 0.747 | No |
| d_log_dex_vol_eth | **0.6110** | 0.182 | 0.001 | **Yes** |
| d_log_dex_vol_stable | 0.1011 | 0.127 | 0.425 | No |
| d_log_borrow_vol_stable | 0.0859 | 0.059 | 0.145 | No |
| d_log_stablecoin_supply | 0.0013 | 0.329 | 0.997 | No |
| d_log_n_tx | **1.8313** | 0.442 | <0.001 | **Yes** |
| eth_volatility | **2.9881** | 0.622 | <0.001 | **Yes** |
| chain_base | 0.0043 | 0.031 | 0.891 | No |

**R-squared:** 0.589
**Durbin-Watson:** 2.03 (no significant autocorrelation)

### VIF Analysis

| Feature | VIF |
|---------|-----|
| d_log_dex_vol_btc | 11.09 |
| d_log_dex_vol_eth | 11.52 |
| d_log_dex_vol_stable | 3.20 |
| d_log_borrow_vol_stable | 1.59 |
| d_log_stablecoin_supply | 1.21 |
| d_log_n_tx | 2.35 |
| eth_volatility | 1.41 |

Note: BTC and ETH DEX volumes show high multicollinearity (VIF > 10), but this is acceptable since ETH volume absorbs the effect and BTC coefficient is not significant.

### Holdout Validation (OP Mainnet)

| Metric | Value |
|--------|-------|
| Correlation | 0.72 |
| RMSE | 0.44 |
| MAE | 0.35 |
| Within 1 std | 79% |
| Within 2 std | 96% |

---

## Script 03: Monte Carlo Simulation

**Purpose:** Project fee distributions conditional on TVL outcomes.

### Configuration

| Parameter | Value |
|-----------|-------|
| Number of simulations | 100,000 |
| Time horizon | 365 days |
| Block size | 7 days (weekly) |
| Starting TVL | $292M (OP current) |
| Starting daily fees | 0.65 ETH (OP current) |
| ETH price | $3,500 |

### Block Bootstrap Method

1. Create weekly blocks from Base + Arbitrum training data
2. For each simulation:
   - Sample 52 random weekly blocks
   - TVL accumulates as stock variable (sum of d_log_tvl)
   - Fees computed as: baseline + model_prediction + residual_sample
   - Fees don't drift (mean-reverting around baseline)
3. Bucket results by ending TVL

### Shock Columns (per block)

```python
shock_cols = [
    "d_log_tvl",               # For TVL accumulation
    "d_log_dex_vol_btc",
    "d_log_dex_vol_eth",
    "d_log_dex_vol_stable",
    "d_log_borrow_vol_stable",
    "d_log_stablecoin_supply",
    "d_log_n_tx",
    "eth_volatility",
]
```

### Results by TVL Bucket

| TVL Bucket | N Sims | % | Median TVL ($M) | Median Fees (ETH) | P10 | P90 | Daily Avg |
|------------|--------|---|-----------------|-------------------|-----|-----|-----------|
| <$400M | 62,068 | 62.1% | 271 | 334 | 307 | 389 | 0.9 |
| $400-500M | 15,597 | 15.6% | 444 | 337 | 306 | 401 | 0.9 |
| $500-750M | 16,917 | 16.9% | 583 | 343 | 307 | 411 | 0.9 |
| $750M-1B | 3,968 | 4.0% | 834 | 351 | 307 | 427 | 1.0 |
| >$1B | 1,450 | 1.5% | 1,130 | 362 | 312 | 443 | 1.0 |

### Key Insights

1. **TVL outcomes are skewed:** 62% of paths stay below $400M; only 5.5% reach $750M+
2. **Fees don't scale with TVL:** Paths reaching >$1B have only 8% higher fees than <$400M paths
3. **Activity drives the difference:** The paths that reach high TVL do so because of sustained activity growth, which also drives fees

### Activity Patterns in Successful Paths

Simulations reaching $750M+ TVL had fundamentally different activity patterns:

| Metric | Paths → $750M+ | All Paths | Multiplier |
|--------|----------------|-----------|------------|
| ETH DEX Volume | +0.56 log | -0.66 log | 1.76x vs 0.52x |
| Transaction Count | +0.43 log | +0.15 log | 1.53x vs 1.16x |
| BTC DEX Volume | +0.70 log | -0.18 log | 2.02x vs 0.84x |
| Stable DEX Volume | +0.83 log | -0.05 log | 2.30x vs 0.95x |

**Key insight:** The average path has *shrinking* DEX volume (ETH down 48%). Paths reaching $750M+ require flipping from contraction to ~1.8x growth.

---

## Visualization System

### Architecture

Templates in `viz/templates/` contain `{{PLACEHOLDER}}` markers. The `data_swap.py` script:

1. Reads CSV data from `data/processed/`
2. Transforms to JSON via per-template transformer functions
3. Replaces `{{PLACEHOLDER}}` with JSON data
4. Writes standalone HTML files to `viz/`

### Available Visualizations

| File | Description | Data Source |
|------|-------------|-------------|
| `00a_tvl_raw.html` | Raw TVL over time | panel_model_ready.csv |
| `00b_fees_raw.html` | Raw fees over time | panel_model_ready.csv |
| `01_tvl_diffs_over_time.html` | d_log(TVL) time series | panel_model_ready.csv |
| `02_fees_diffs_over_time.html` | d_log(fees) time series | panel_model_ready.csv |
| `03_ntx_vs_fees_scatter.html` | n_tx vs fees scatter | panel_model_ready.csv |
| `04_volatility_vs_fees_scatter.html` | Volatility vs fees scatter | panel_model_ready.csv |
| `05_dex_eth_vs_fees_scatter.html` | DEX ETH vol vs fees scatter | panel_model_ready.csv |
| `06_fee_distributions_boxplot.html` | Fee distributions by TVL bucket | simulation_results.csv |
| `07_tvl_bucket_summary.html` | TVL bucket outcomes | simulation_results.csv |
| `08_model_coefficients.html` | Coefficient bar chart | Hardcoded from model |
| `09_feature_importance.html` | Incremental R² | Hardcoded from model |
| `10_sample_paths_500m.html` | Sample paths $500M+ | simulation_results.csv |
| `11_summary_table.html` | Summary statistics table | simulation_summary.csv |
| `12_activity_patterns.html` | Successful vs all paths (log scale) | activity_patterns.csv |
| `12b_activity_patterns_mult.html` | Successful vs all paths (multipliers) | activity_patterns.csv |
| `13_success_vs_all_scatter.html` | TVL vs DEX growth (log scale) | simulation_results.csv |
| `13b_tvl_vs_growth_mult.html` | TVL vs DEX growth (multipliers) | simulation_results.csv |

### Regenerating Visualizations

```bash
# All visualizations
uv run python viz/data_swap.py

# Single visualization
uv run python viz/data_swap.py 01_tvl_diffs_over_time
```

---

## Variable Selection Rationale

### Included Variables

| Variable | Reason |
|----------|--------|
| d_log_dex_vol_btc | Decomposed DEX volume - BTC trading activity |
| d_log_dex_vol_eth | Decomposed DEX volume - ETH trading activity |
| d_log_dex_vol_stable | Decomposed DEX volume - stablecoin trading |
| d_log_borrow_vol_stable | Stablecoin borrowing is dominant lending activity |
| d_log_stablecoin_supply | Captures lending capacity |
| d_log_n_tx | General chain activity |
| eth_volatility | Exogenous market condition |

### Excluded Variables

| Variable | Reason |
|----------|--------|
| d_log_tvl | Highly correlated with activity; stock variable that doesn't cause fees |
| d_log_borrow_vol_btc | Minor volume; collinear with DEX volumes |
| d_log_borrow_vol_eth | Minor volume; collinear with DEX volumes |

---

## Verification Checklist

- [x] Script 01 produces all required d_log columns
- [x] Script 02 uses consistent FEATURE_COLS
- [x] Script 02 validation uses same FEATURE_COLS
- [x] Script 03 uses matching FEATURE_COLS
- [x] Script 03 shock_cols includes all required columns
- [x] Coefficient ordering consistent between estimation and simulation
- [x] Visualization templates match transformer output schemas
- [x] All 13 visualizations generate successfully

---

## Reproducibility

### Environment

```bash
# Python environment managed by uv
uv sync
```

### Full Pipeline

```bash
uv run python scripts/01_load_and_clean.py
uv run python scripts/02_estimate_model.py
uv run python scripts/03_monte_carlo_simulation.py
uv run python viz/data_swap.py
```

### Expected Outputs

| File | Records |
|------|---------|
| panel_model_ready.csv | 1,092 rows (3 chains × 364 days) |
| simulation_results.csv | 100,000 rows |
| simulation_summary.csv | 5 rows (TVL buckets) |
| activity_patterns.csv | 5 rows (metrics comparison) |
| viz/*.html | 17 files |
