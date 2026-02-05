"""
02_estimate_model.py

Estimate two-link panel model:
  Link 1: ΔTVL → Δactivity
  Link 2: Δactivity → Δfees

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


def estimate_link2(train_df):
    """
    Link 2: Δactivity → Δfees

    d_log_fees ~ d_log_total_dex_vol + d_log_total_borrow_vol
                 + d_dex_btc_share + d_dex_eth_share
                 + d_borrow_btc_share + d_borrow_eth_share
                 + eth_volatility + chain_fe
    """
    print("=" * 60)
    print("LINK 2: Δactivity → Δfees")
    print("=" * 60)

    # Prepare features
    feature_cols = [
        "d_log_total_dex_vol",
        "d_log_total_borrow_vol",
        "d_dex_btc_share",
        "d_dex_eth_share",
        "d_borrow_btc_share",
        "d_borrow_eth_share",
        "eth_volatility",
    ]

    # Add chain fixed effect (dummy for base, arbitrum is reference)
    train_df = train_df.copy()
    train_df["chain_base"] = (train_df["chain"] == "base").astype(int)

    X = train_df[feature_cols + ["chain_base"]].copy()
    X = sm.add_constant(X)
    y = train_df["d_log_fees"]

    # Drop any remaining NaN
    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]

    print(f"\nObservations: {len(y)}")
    print(f"Features: {feature_cols}")

    # VIF check (exclude constant and FE)
    print("\n--- VIF (multicollinearity check) ---")
    vif = compute_vif(X[feature_cols])
    print(vif.to_string(index=False))

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


def estimate_link1_dex(train_df):
    """
    Link 1a: ΔTVL → ΔDEX volume

    d_log_total_dex_vol ~ d_log_tvl + eth_volatility + chain_fe
    """
    print("\n" + "=" * 60)
    print("LINK 1a: ΔTVL → ΔDEX volume")
    print("=" * 60)

    train_df = train_df.copy()
    train_df["chain_base"] = (train_df["chain"] == "base").astype(int)

    feature_cols = ["d_log_tvl", "eth_volatility"]

    X = train_df[feature_cols + ["chain_base"]].copy()
    X = sm.add_constant(X)
    y = train_df["d_log_total_dex_vol"]

    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]

    print(f"\nObservations: {len(y)}")

    model = OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})

    print("\n--- Regression Results ---")
    print(model.summary())

    print("\n--- Diagnostics ---")
    print(f"R-squared: {model.rsquared:.4f}")
    print(f"Durbin-Watson: {durbin_watson(model.resid):.4f}")

    return model


def estimate_link1_borrow(train_df):
    """
    Link 1b: ΔTVL → ΔBorrow volume

    d_log_total_borrow_vol ~ d_log_tvl + eth_volatility + chain_fe
    """
    print("\n" + "=" * 60)
    print("LINK 1b: ΔTVL → ΔBorrow volume")
    print("=" * 60)

    train_df = train_df.copy()
    train_df["chain_base"] = (train_df["chain"] == "base").astype(int)

    feature_cols = ["d_log_tvl", "eth_volatility"]

    X = train_df[feature_cols + ["chain_base"]].copy()
    X = sm.add_constant(X)
    y = train_df["d_log_total_borrow_vol"]

    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]

    print(f"\nObservations: {len(y)}")

    model = OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})

    print("\n--- Regression Results ---")
    print(model.summary())

    print("\n--- Diagnostics ---")
    print(f"R-squared: {model.rsquared:.4f}")
    print(f"Durbin-Watson: {durbin_watson(model.resid):.4f}")

    return model


def estimate_direct_model(train_df):
    """
    Direct model: ΔTVL + Δactivity → Δfees (all at once)

    For comparison and Shapley decomposition.
    """
    print("\n" + "=" * 60)
    print("DIRECT MODEL: All predictors → Δfees")
    print("=" * 60)

    train_df = train_df.copy()
    train_df["chain_base"] = (train_df["chain"] == "base").astype(int)

    feature_cols = [
        "d_log_tvl",
        "d_log_total_dex_vol",
        "d_log_total_borrow_vol",
        "eth_volatility",
    ]

    X = train_df[feature_cols + ["chain_base"]].copy()
    X = sm.add_constant(X)
    y = train_df["d_log_fees"]

    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]

    print(f"\nObservations: {len(y)}")

    # VIF
    print("\n--- VIF ---")
    vif = compute_vif(X[feature_cols])
    print(vif.to_string(index=False))

    model = OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})

    print("\n--- Regression Results ---")
    print(model.summary())

    # Simple Shapley approximation via incremental R²
    print("\n--- Incremental R² (Shapley-lite) ---")
    base_r2 = 0
    for col in feature_cols:
        X_partial = sm.add_constant(train_df[[col, "chain_base"]][mask])
        partial_model = OLS(y, X_partial).fit()
        print(f"  {col} alone: R² = {partial_model.rsquared:.4f}")

    return model


def validate_on_holdout(holdout_df, link2_model, feature_cols):
    """Apply model to Optimism holdout and evaluate."""
    print("\n" + "=" * 60)
    print("VALIDATION: Optimism holdout")
    print("=" * 60)

    holdout_df = holdout_df.copy()
    holdout_df["chain_base"] = 0  # Optimism uses arbitrum-like intercept

    # Prepare X with same columns as training
    X = holdout_df[["d_log_total_dex_vol", "d_log_total_borrow_vol",
                    "d_dex_btc_share", "d_dex_eth_share",
                    "d_borrow_btc_share", "d_borrow_eth_share",
                    "eth_volatility", "chain_base"]].copy()
    X = sm.add_constant(X)
    y = holdout_df["d_log_fees"]

    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]

    # Predict
    y_pred = link2_model.predict(X)

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
    pred_std = np.std(link2_model.resid)  # Use training residual std
    within_1std = ((y >= y_pred - pred_std) & (y <= y_pred + pred_std)).mean()
    within_2std = ((y >= y_pred - 2*pred_std) & (y <= y_pred + 2*pred_std)).mean()
    print(f"Within ±1 std: {within_1std:.1%}")
    print(f"Within ±2 std: {within_2std:.1%}")

    return y, y_pred


def main():
    print("Loading data...")
    df = load_panel()
    train, holdout = split_train_holdout(df)

    print(f"Training: {len(train)} obs (Base + Arbitrum)")
    print(f"Holdout: {len(holdout)} obs (Optimism)")

    # Estimate models
    link1_dex = estimate_link1_dex(train)
    link1_borrow = estimate_link1_borrow(train)
    link2, feature_cols = estimate_link2(train)
    direct = estimate_direct_model(train)

    # Validate
    y_actual, y_pred = validate_on_holdout(holdout, link2, feature_cols)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Key coefficients from Link 2 (Δactivity → Δfees):
- d_log_total_dex_vol: elasticity of fees to DEX volume
- d_log_total_borrow_vol: elasticity of fees to borrow volume
- eth_volatility: fees increase on volatile days

Interpretation:
- Coefficient of 0.5 on d_log_total_dex_vol means 1% increase in DEX volume
  is associated with 0.5% increase in fees (same day).
    """)


if __name__ == "__main__":
    main()
