# Technical Report: Pipeline Flow Analysis

## Overview

This report documents the data pipeline flow across the three main scripts and identifies consistency issues for the new model specification.

---

## Current Pipeline Flow

### Script 01: `01_load_and_clean.py`

**Purpose:** Load raw data files and produce model-ready panel dataset.

**Input Files:**
- `data/arb_op_base_tx_fees_eth_2025.csv` - Sequencer fees
- `data/*_tvl_no_inclusions.csv` - TVL by chain
- `data/dex_trades_2025.csv` - DEX trade volumes
- `data/lending_borrow_2025.csv` - Borrow volumes
- `data/*_stablecoin_marketcaps.csv` - Stablecoin supply
- `data/eth_ohlc.csv` - ETH price data
- `data/arb_op_base_n_tx_2025.csv` - Transaction counts
- `data/tokenlist.json` - Token address classification

**Processing Steps:**
1. Load each data source with date parsing
2. Classify DEX/borrow tokens into buckets (btc, eth, stable) using `tokenlist.json`
3. Merge all sources on (chain, date)
4. Compute derived columns:
   - `total_dex_vol` = sum of btc + eth + stable DEX volumes
   - `total_borrow_vol` = sum of btc + eth + stable borrow volumes
   - Composition shares (dex_btc_share, etc.)
   - `eth_volatility` = (high - low) / open
5. Compute log-differences within each chain

**Output Columns (model-ready):**

| Column | Description |
|--------|-------------|
| `d_log_fees` | Δlog(fees_eth) |
| `d_log_tvl` | Δlog(tvl_usd) |
| `d_log_total_dex_vol` | Δlog(total DEX volume) |
| `d_log_total_borrow_vol` | Δlog(total borrow volume) |
| `d_log_stablecoin_supply` | Δlog(stablecoin supply) |
| `d_log_n_tx` | Δlog(transaction count) |
| `d_log_dex_vol_btc` | Δlog(DEX BTC volume) |
| `d_log_dex_vol_eth` | Δlog(DEX ETH volume) |
| `d_log_dex_vol_stable` | Δlog(DEX stablecoin volume) |
| `d_dex_btc_share` | Δ(DEX BTC share) |
| `d_dex_eth_share` | Δ(DEX ETH share) |
| `d_borrow_btc_share` | Δ(borrow BTC share) |
| `d_borrow_eth_share` | Δ(borrow ETH share) |
| `eth_volatility` | (high - low) / open (level, not differenced) |

**Output Files:**
- `data/processed/panel_raw.csv` - Intermediate merged panel
- `data/processed/panel_model_ready.csv` - Log-differenced features

---

### Script 02: `02_estimate_model.py`

**Purpose:** Estimate panel regression models.

**Current Structure (two-link model):**

1. **Link 1a:** ΔTVL → ΔDEX volume
   ```
   d_log_total_dex_vol ~ d_log_tvl + eth_volatility + chain_fe
   ```

2. **Link 1b:** ΔTVL → ΔBorrow volume
   ```
   d_log_total_borrow_vol ~ d_log_tvl + eth_volatility + chain_fe
   ```

3. **Link 2:** Δactivity → Δfees
   ```
   d_log_fees ~ d_log_total_dex_vol + d_log_total_borrow_vol + d_log_n_tx
              + d_dex_btc_share + d_dex_eth_share
              + d_borrow_btc_share + d_borrow_eth_share
              + eth_volatility + chain_fe
   ```

4. **Direct Model:** All predictors together (for comparison)

**Training/Validation Split:**
- Training: Base + Arbitrum
- Holdout: Optimism

**Estimation Method:**
- OLS with HAC standard errors (Newey-West, 5 lags)
- VIF checks for multicollinearity
- Durbin-Watson for autocorrelation

---

### Script 03: `03_monte_carlo_simulation.py`

**Purpose:** Run Monte Carlo simulations using block bootstrap.

**Current Approach:**
1. Re-estimate Link 2 model internally
2. Create weekly blocks from Base + Arbitrum data
3. For each simulation:
   - Sample random blocks
   - TVL accumulates (stock variable)
   - Fees = baseline + model prediction + residual (don't drift)
4. Bucket results by ending TVL

**Block Columns Used:**
```python
shock_cols = [
    "d_log_tvl",              # index 0
    "d_log_total_dex_vol",    # index 1
    "d_log_total_borrow_vol", # index 2
    "d_log_n_tx",             # index 3
    "d_dex_btc_share",        # index 4
    "d_dex_eth_share",        # index 5
    "d_borrow_btc_share",     # index 6
    "d_borrow_eth_share",     # index 7
    "eth_volatility",         # index 8
]
```

**Coefficient Order:**
```
const, d_log_total_dex_vol, d_log_total_borrow_vol, d_log_n_tx,
d_dex_btc_share, d_dex_eth_share, d_borrow_btc_share, d_borrow_eth_share,
eth_volatility, chain_base
```

---

## New Model Specification

**Requested model:**
```
Δlog(fees) ~ Δlog(dex_vol_btc) + Δlog(dex_vol_eth) + Δlog(dex_vol_stable)
           + Δlog(borrow_vol_stable) + Δlog(stablecoin_supply) + Δlog(n_tx)
           + eth_volatility + chain_fe
```

**Predictors (8 total + intercept + chain FE):**
1. `d_log_dex_vol_btc` - DEX BTC volume changes
2. `d_log_dex_vol_eth` - DEX ETH volume changes
3. `d_log_dex_vol_stable` - DEX stablecoin volume changes
4. `d_log_borrow_vol_stable` - Stablecoin borrow volume changes (**MISSING**)
5. `d_log_stablecoin_supply` - Stablecoin supply changes
6. `d_log_n_tx` - Transaction count changes
7. `eth_volatility` - ETH price volatility (level)
8. `chain_base` - Chain fixed effect (Base = 1, others = 0)

---

## Issues Identified

### Issue 1: Missing Column in Script 01

**Problem:** Script 01 does not compute `d_log_borrow_vol_stable`.

The script computes decomposed DEX volumes:
- `d_log_dex_vol_btc` ✓
- `d_log_dex_vol_eth` ✓
- `d_log_dex_vol_stable` ✓

But for borrow, it only computes the total:
- `d_log_total_borrow_vol` ✓
- `d_log_borrow_vol_stable` ✗ **MISSING**

**Fix Required:** Add log transform and differencing for `borrow_vol_stable`.

### Issue 2: Script 02 Uses Old Model Structure

**Problem:** Script 02 still estimates the two-link model (Link 1a, Link 1b, Link 2) instead of the new single reduced-form model.

**Fix Required:** Replace with single model using the new specification.

### Issue 3: Script 03 Uses Old Model Structure

**Problem:** Script 03 re-estimates Link 2 internally using the old feature set and coefficient ordering.

**Fix Required:** Update to match new specification.

### Issue 4: Validation Function Hardcoded Columns

**Problem:** `validate_on_holdout()` has hardcoded column names that don't match the new model.

**Fix Required:** Update to use new feature set.

---

## Changes Made

### Script 01 Changes (COMPLETED)

Added to `compute_model_ready()`:
```python
# Add decomposed borrow volume log transform
df["log_borrow_vol_stable"] = np.log(df["borrow_vol_stable"] + eps)

# Added to diff_cols dict:
"d_log_borrow_vol_stable": "log_borrow_vol_stable",
```

### Script 02 Changes (COMPLETED)

1. Removed `estimate_link1_dex()` and `estimate_link1_borrow()` - no longer using two-link model
2. Replaced `estimate_link2()` with `estimate_fee_model()` using new features
3. Removed `estimate_direct_model()` - redundant with new single model
4. Updated `validate_on_holdout()` to use new feature set
5. Updated `main()` flow and summary text
6. Added `FEATURE_COLS` constant for consistency

### Script 03 Changes (COMPLETED)

1. Renamed `estimate_link2()` to `estimate_fee_model()` with new feature set
2. Updated `prepare_block_arrays()` shock_cols to include new columns
3. Updated feature vector construction in `run_simulations_vectorized()`
4. Updated coefficient ordering to match new model
5. Added `FEATURE_COLS` constant matching script 02

---

## New Model Feature Order

For consistency across scripts:

```python
feature_cols = [
    "d_log_dex_vol_btc",
    "d_log_dex_vol_eth",
    "d_log_dex_vol_stable",
    "d_log_borrow_vol_stable",
    "d_log_stablecoin_supply",
    "d_log_n_tx",
    "eth_volatility",
]
```

Full coefficient order (for simulation):
```
const, d_log_dex_vol_btc, d_log_dex_vol_eth, d_log_dex_vol_stable,
d_log_borrow_vol_stable, d_log_stablecoin_supply, d_log_n_tx,
eth_volatility, chain_base
```

---

## Data Flow Diagram

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
│  - Bucket by ending TVL → fee distributions                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
           simulation_results.csv, simulation_summary.csv
```

---

## Final Model Specification

After changes, all three scripts now use a consistent reduced-form fee model:

```
Δlog(fees) ~ Δlog(dex_vol_btc) + Δlog(dex_vol_eth) + Δlog(dex_vol_stable)
           + Δlog(borrow_vol_stable) + Δlog(stablecoin_supply) + Δlog(n_tx)
           + eth_volatility + chain_fe
```

### Feature Columns (shared across scripts 02 and 03)

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

### Rationale for Variable Selection

| Included | Reason |
|----------|--------|
| DEX volumes (3) | Decomposed by asset class to capture composition effects |
| Borrow vol stable | Stablecoin borrowing is dominant lending activity |
| Stablecoin supply | Captures lending capacity |
| n_tx | General chain activity |
| eth_volatility | Exogenous market condition |

| Excluded | Reason |
|----------|--------|
| TVL | Highly correlated with activity; stock variable |
| Borrow vol BTC/ETH | Minor volume; collinear with DEX volumes |

---

## Verification Checklist

- [x] Script 01 produces `d_log_borrow_vol_stable` column
- [x] Script 02 uses `FEATURE_COLS` for model estimation
- [x] Script 02 validation uses same `FEATURE_COLS`
- [x] Script 03 uses same `FEATURE_COLS` for coefficient extraction
- [x] Script 03 `shock_cols` includes all required columns for simulation
- [x] Coefficient ordering consistent between estimation and simulation
