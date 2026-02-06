"""
02_estimate_model.py

Estimate reduced-form fee model:
    Δlog(fees) ~ Δlog(dex_vol_btc) + Δlog(dex_vol_eth) + Δlog(dex_vol_stable)
               + Δlog(borrow_vol_stable) + Δlog(stablecoin_supply) + Δlog(n_tx)
               + eth_volatility + chain_fe

Uses Base + Arbitrum for training, holds out Optimism for validation.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson

warnings.filterwarnings("ignore")

DATA_DIR = Path("data/processed")

# Feature columns for the fee model
FEATURE_COLS = [
    "d_log_dex_vol_btc",
    "d_log_dex_vol_eth",
    "d_log_dex_vol_stable",
    "d_log_borrow_vol_stable",
    "d_log_stablecoin_supply",
    "d_log_n_tx",
    "eth_volatility",
]


def load_panel():
    """Load model-ready panel data."""
    df = pd.read_csv(DATA_DIR / "panel_model_ready.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


def split_train_holdout(df):
    """Split into training (Base + Arbitrum) and holdout (Optimism)."""
    train = df[df["chain"].isin(["base", "arbitrum"])].copy()
    holdout = df[df["chain"] == "optimism"].copy()
    return train, holdout


def compute_vif(X):
    """Compute variance inflation factors."""
    vif_data = pd.DataFrame()
    vif_data["feature"] = X.columns
    vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
    return vif_data


def estimate_fee_model(train_df):
    """
    Estimate reduced-form fee model.

    d_log_fees ~ d_log_dex_vol_btc + d_log_dex_vol_eth + d_log_dex_vol_stable
               + d_log_borrow_vol_stable + d_log_stablecoin_supply + d_log_n_tx
               + eth_volatility + chain_fe
    """
    print("=" * 60)
    print("FEE MODEL: d(activity) -> d(fees)")
    print("=" * 60)

    # Add chain fixed effect (dummy for base, arbitrum is reference)
    train_df = train_df.copy()
    train_df["chain_base"] = (train_df["chain"] == "base").astype(int)

    X = train_df[FEATURE_COLS + ["chain_base"]].copy()
    X = sm.add_constant(X)
    y = train_df["d_log_fees"]

    # Drop any remaining NaN
    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]

    print(f"\nObservations: {len(y)}")
    print(f"Features: {FEATURE_COLS}")

    # VIF check (exclude constant and FE)
    print("\n--- VIF (multicollinearity check) ---")
    vif = compute_vif(X[FEATURE_COLS])
    print(vif.to_string(index=False))

    # Flag high VIF
    high_vif = vif[vif["VIF"] > 10]
    if len(high_vif) > 0:
        print("\nWARNING: High VIF detected (>10):")
        print(high_vif.to_string(index=False))

    # Estimate with HAC standard errors (Newey-West)
    model = OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})

    print("\n--- Regression Results ---")
    print(model.summary())

    # Diagnostics
    print("\n--- Diagnostics ---")
    print(f"R-squared: {model.rsquared:.4f}")
    print(f"Adj R-squared: {model.rsquared_adj:.4f}")
    print(f"Durbin-Watson: {durbin_watson(model.resid):.4f} (2.0 = no autocorrelation)")
    print(f"Residual std: {np.std(model.resid):.4f}")

    return model, X.columns.tolist()


def validate_on_holdout(holdout_df, model, feature_cols):
    """Apply model to Optimism holdout and evaluate."""
    print("\n" + "=" * 60)
    print("VALIDATION: Optimism holdout")
    print("=" * 60)

    holdout_df = holdout_df.copy()
    holdout_df["chain_base"] = 0  # Optimism uses arbitrum-like intercept

    # Prepare X with same columns as training
    X = holdout_df[FEATURE_COLS + ["chain_base"]].copy()
    X = sm.add_constant(X)
    y = holdout_df["d_log_fees"]

    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]

    # Predict
    y_pred = model.predict(X)

    # Metrics
    resid = y - y_pred
    mae = np.abs(resid).mean()
    rmse = np.sqrt((resid ** 2).mean())
    corr = np.corrcoef(y, y_pred)[0, 1]

    print(f"\nHoldout observations: {len(y)}")
    print(f"MAE: {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"Correlation (pred vs actual): {corr:.4f}")

    # Coverage
    pred_std = np.std(model.resid)  # Use training residual std
    within_1std = ((y >= y_pred - pred_std) & (y <= y_pred + pred_std)).mean()
    within_2std = ((y >= y_pred - 2*pred_std) & (y <= y_pred + 2*pred_std)).mean()
    print(f"Within ±1 std: {within_1std:.1%}")
    print(f"Within ±2 std: {within_2std:.1%}")

    return y, y_pred


def compute_incremental_r2(train_df, mask, y):
    """Compute incremental R-squared for each feature alone."""
    print("\n--- Incremental R-squared (feature importance) ---")

    train_df = train_df.copy()
    train_df["chain_base"] = (train_df["chain"] == "base").astype(int)

    for col in FEATURE_COLS:
        X_partial = sm.add_constant(train_df[[col, "chain_base"]][mask])
        partial_model = OLS(y, X_partial).fit()
        print(f"  {col} alone: R-sq = {partial_model.rsquared:.4f}")


def main():
    print("Loading data...")
    df = load_panel()
    train, holdout = split_train_holdout(df)

    print(f"Training: {len(train)} obs (Base + Arbitrum)")
    print(f"Holdout: {len(holdout)} obs (Optimism)")

    # Estimate model
    model, feature_cols = estimate_fee_model(train)

    # Compute incremental R² for each feature
    train_copy = train.copy()
    train_copy["chain_base"] = (train_copy["chain"] == "base").astype(int)
    X_temp = train_copy[FEATURE_COLS + ["chain_base"]].copy()
    y_temp = train_copy["d_log_fees"]
    mask = ~(X_temp.isna().any(axis=1) | y_temp.isna())
    compute_incremental_r2(train, mask, y_temp[mask])

    # Validate
    y_actual, y_pred = validate_on_holdout(holdout, model, feature_cols)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Model: d_log(fees) ~ activity changes + volatility + chain FE

Features:
- d_log_dex_vol_btc/eth/stable: DEX volume changes by asset class
- d_log_borrow_vol_stable: Stablecoin borrow volume changes
- d_log_stablecoin_supply: Stablecoin supply changes
- d_log_n_tx: Transaction count changes
- eth_volatility: ETH price volatility (level)

Interpretation:
- Coefficient of 0.5 on d_log_dex_vol_eth means 1% increase in ETH DEX volume
  is associated with 0.5% increase in fees (same day).
- Positive volatility coefficient: fees increase on volatile days.
    """)

    # Print key coefficients
    print("Key Coefficients:")
    for feat in FEATURE_COLS:
        coef = model.params.get(feat, 0)
        pval = model.pvalues.get(feat, 1)
        sig = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.1 else ""
        print(f"  {feat}: {coef:.4f} {sig}")


if __name__ == "__main__":
    main()
