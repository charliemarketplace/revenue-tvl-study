# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Econometric analysis linking L2 DeFi ecosystem growth (TVL) to sequencer fee revenue. Core question: "If OP Mainnet reaches $500M / $750M / $1B in TVL, what fee revenue should we expect?"

**Key insight:** TVL (stock) doesn't directly cause fees (flow). The causal chain is: ΔTVL → Δactivity → Δfees

## Commands

```bash
# Install dependencies
uv sync

# Run the full pipeline
python scripts/01_load_and_clean.py    # Build panel from raw CSVs
python scripts/02_estimate_model.py    # Estimate Link 1 & Link 2 models
python scripts/03_monte_carlo_simulation.py  # Run 100k simulations
```

## Architecture

### Data Flow
1. **Raw data** (`data/`): Dune SQL exports + DefiLlama CSVs
2. **Cleaning** (`01_load_and_clean.py`): Token classification, merges, log-differencing
3. **Modeling** (`02_estimate_model.py`): Panel OLS with HAC standard errors
4. **Simulation** (`03_monte_carlo_simulation.py`): Block bootstrap Monte Carlo

### Fee Model (Reduced Form)
```
Δlog(fees) ~ Δlog(dex_vol_btc) + Δlog(dex_vol_eth) + Δlog(dex_vol_stable)
           + Δlog(borrow_vol_stable) + Δlog(stablecoin_supply) + Δlog(n_tx)
           + eth_volatility + chain_fe
```

**Features (7 + chain FE):**
- DEX volumes by asset class (BTC, ETH, stablecoins)
- Stablecoin borrow volume
- Stablecoin supply changes
- Transaction count
- ETH price volatility

### Panel Design
- **Training**: Base + Arbitrum (pooled with chain fixed effects)
- **Validation**: Optimism (held out for out-of-sample testing)
- **Frequency**: Daily observations, 2025

### Key Files
- `data/tokenlist.json`: Token address → bucket mapping (btc/eth/stable)
- `queries/`: Dune SQL queries for data extraction
- `data/processed/panel_model_ready.csv`: Log-differenced features for regression

## Estimation Details

- Uses `statsmodels` OLS with HAC robust standard errors (Newey-West, 5-lag)
- VIF checks for multicollinearity
- Durbin-Watson for autocorrelation diagnostics
- Out-of-sample validation on Optimism: MAE, RMSE, correlation
- Incremental R² computed for each feature (feature importance)

## Monte Carlo Simulation

- Block bootstrap (weekly blocks) preserves correlation structure
- 100k simulations, 365-day horizon
- Fees fluctuate around baseline (Dec 2025 OP median)
- Output: fee distributions bucketed by ending TVL
