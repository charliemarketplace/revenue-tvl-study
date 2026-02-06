"""
03_monte_carlo_simulation.py

Model-based Monte Carlo simulation using block bootstrap.

Approach:
1. Sample weekly blocks of activity shocks from Base/Arb
2. Apply fee model coefficients to compute predicted Δlog_fees
3. Add residual noise (block-sampled to preserve AR structure)
4. Accumulate paths, let TVL be an outcome
5. Group by ending TVL bucket → fee distributions

Uses estimated coefficients from panel model, not pure resampling.
Vectorized implementation for performance.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS

warnings.filterwarnings("ignore")

DATA_DIR = Path("data/processed")
BLOCK_SIZE = 7  # Weekly blocks
N_SIMULATIONS = 100000
HORIZON_DAYS = 365  # 1 year forward

# Feature columns (must match 02_estimate_model.py)
FEATURE_COLS = [
    "d_log_dex_vol_btc",
    "d_log_dex_vol_eth",
    "d_log_dex_vol_stable",
    "d_log_borrow_vol_stable",
    "d_log_stablecoin_supply",
    "d_log_n_tx",
    "eth_volatility",
]

# TVL buckets for conditioning (in millions USD)
TVL_BUCKETS = [
    (0, 400, "<$400M"),
    (400, 500, "$400-500M"),
    (500, 750, "$500-750M"),
    (750, 1000, "$750M-1B"),
    (1000, float("inf"), ">$1B"),
]


def load_data():
    """Load model-ready panel data."""
    df = pd.read_csv(DATA_DIR / "panel_model_ready.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


def estimate_fee_model(train_df):
    """
    Estimate fee model and return coefficients + residuals.

    Returns model, coefficients as array, and residuals.
    """
    train_df = train_df.copy()
    train_df["chain_base"] = (train_df["chain"] == "base").astype(int)

    X = train_df[FEATURE_COLS + ["chain_base"]].copy()
    X = sm.add_constant(X)
    y = train_df["d_log_fees"]

    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]

    model = OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})

    # Extract coefficients in order: const, features, chain_base
    coef_order = ["const"] + FEATURE_COLS + ["chain_base"]
    coefficients = np.array([model.params[c] for c in coef_order])

    return model, coefficients, model.resid.values


def prepare_block_arrays(df, block_size=BLOCK_SIZE):
    """
    Prepare block data as numpy arrays for fast simulation.

    Returns:
        blocks: list of (n_days, n_features) arrays
    """
    # Columns needed for simulation
    # Order: d_log_tvl (for TVL accumulation), then model features
    shock_cols = [
        "d_log_tvl",              # index 0 - for TVL accumulation
        "d_log_dex_vol_btc",      # index 1
        "d_log_dex_vol_eth",      # index 2
        "d_log_dex_vol_stable",   # index 3
        "d_log_borrow_vol_stable",# index 4
        "d_log_stablecoin_supply",# index 5
        "d_log_n_tx",             # index 6
        "eth_volatility",         # index 7
    ]

    blocks = []

    for chain in df["chain"].unique():
        chain_df = df[df["chain"] == chain].sort_values("date").reset_index(drop=True)

        n_blocks = len(chain_df) // block_size
        for i in range(n_blocks):
            start_idx = i * block_size
            end_idx = start_idx + block_size
            block_data = chain_df.iloc[start_idx:end_idx][shock_cols].values
            # Fill NaN with 0
            block_data = np.nan_to_num(block_data, nan=0.0)
            blocks.append(block_data)

    return blocks


def get_op_starting_state(df):
    """Get OP's state as simulation starting point."""
    op_df = df[df["chain"] == "optimism"].sort_values("date")
    op_df["date"] = pd.to_datetime(op_df["date"])
    last_row = op_df.iloc[-1]

    # Use December 2025 median as baseline (recent, out-of-sample)
    dec_2025 = op_df[op_df["date"].dt.month == 12]
    baseline_log_fees = dec_2025["log_fees"].median()

    return {
        "log_tvl": last_row["log_tvl"],
        "log_fees": last_row["log_fees"],
        "baseline_log_fees": baseline_log_fees,
        "baseline_fee_eth": np.exp(baseline_log_fees),
        "tvl_usd": last_row["tvl_usd"],
        "fees_eth": last_row["fees_eth"],
    }


def run_simulations_vectorized(n_sims, starting_state, blocks, coefficients, residuals, horizon_days, seed=42):
    """
    Run N Monte Carlo simulations using vectorized operations.

    Key insight: Don't let log_fees drift as a random walk. Instead:
    - TVL accumulates (stock variable)
    - Daily fees = baseline + predicted_deviation (not cumulative)

    This prevents explosive/collapsing fee paths while still using
    model coefficients to capture activity→fee relationship.
    """
    rng = np.random.default_rng(seed)

    n_blocks = len(blocks)
    n_weeks = horizon_days // BLOCK_SIZE
    remaining_days = horizon_days % BLOCK_SIZE

    # Pre-sample all block indices for all simulations
    block_indices = rng.integers(0, n_blocks, size=(n_sims, n_weeks + 1))

    # Pre-sample residuals
    residual_samples = rng.choice(residuals, size=(n_sims, horizon_days))

    # Baseline log_fees (fees fluctuate around this)
    baseline_log_fees = starting_state["baseline_log_fees"]

    # Initialize results
    ending_log_tvl = np.full(n_sims, starting_state["log_tvl"])
    cumulative_fees = np.zeros(n_sims)

    # Track cumulative activity changes for path analysis
    cum_d_log_tvl = np.zeros(n_sims)
    cum_d_log_dex_vol_btc = np.zeros(n_sims)
    cum_d_log_dex_vol_eth = np.zeros(n_sims)
    cum_d_log_dex_vol_stable = np.zeros(n_sims)
    cum_d_log_n_tx = np.zeros(n_sims)

    for sim_idx in range(n_sims):
        if (sim_idx + 1) % 2000 == 0:
            print(f"  Simulation {sim_idx + 1}/{n_sims}...")

        log_tvl = starting_state["log_tvl"]
        day_idx = 0

        # Track activity accumulation for this simulation
        sim_d_log_tvl = 0.0
        sim_d_log_dex_vol_btc = 0.0
        sim_d_log_dex_vol_eth = 0.0
        sim_d_log_dex_vol_stable = 0.0
        sim_d_log_n_tx = 0.0

        # Process full weeks
        for week_idx in range(n_weeks):
            block = blocks[block_indices[sim_idx, week_idx]]

            for day in range(BLOCK_SIZE):
                # Update TVL (accumulates - it's a stock variable)
                log_tvl += block[day, 0]  # d_log_tvl

                # Track activity changes
                sim_d_log_tvl += block[day, 0]
                sim_d_log_dex_vol_btc += block[day, 1]
                sim_d_log_dex_vol_eth += block[day, 2]
                sim_d_log_dex_vol_stable += block[day, 3]
                sim_d_log_n_tx += block[day, 6]

                # Build feature vector for fee prediction
                # Order: const, features (indices 1-7), chain_base
                features = np.array([
                    1.0,              # const
                    block[day, 1],    # d_log_dex_vol_btc
                    block[day, 2],    # d_log_dex_vol_eth
                    block[day, 3],    # d_log_dex_vol_stable
                    block[day, 4],    # d_log_borrow_vol_stable
                    block[day, 5],    # d_log_stablecoin_supply
                    block[day, 6],    # d_log_n_tx
                    block[day, 7],    # eth_volatility
                    0.0,              # chain_base (OP = 0)
                ])

                # Predicted fee deviation from baseline
                predicted_deviation = np.dot(features, coefficients)

                # Add residual
                total_deviation = predicted_deviation + residual_samples[sim_idx, day_idx]

                # Daily fee = exp(baseline + deviation)
                # This means fees fluctuate around the baseline, not drift
                daily_log_fees = baseline_log_fees + total_deviation
                daily_fee = np.exp(daily_log_fees)

                cumulative_fees[sim_idx] += daily_fee
                day_idx += 1

        # Process remaining days
        if remaining_days > 0:
            block = blocks[block_indices[sim_idx, n_weeks]]
            for day in range(remaining_days):
                log_tvl += block[day, 0]  # d_log_tvl

                # Track activity changes
                sim_d_log_tvl += block[day, 0]
                sim_d_log_dex_vol_btc += block[day, 1]
                sim_d_log_dex_vol_eth += block[day, 2]
                sim_d_log_dex_vol_stable += block[day, 3]
                sim_d_log_n_tx += block[day, 6]

                features = np.array([
                    1.0,              # const
                    block[day, 1],    # d_log_dex_vol_btc
                    block[day, 2],    # d_log_dex_vol_eth
                    block[day, 3],    # d_log_dex_vol_stable
                    block[day, 4],    # d_log_borrow_vol_stable
                    block[day, 5],    # d_log_stablecoin_supply
                    block[day, 6],    # d_log_n_tx
                    block[day, 7],    # eth_volatility
                    0.0,              # chain_base (OP = 0)
                ])

                predicted_deviation = np.dot(features, coefficients)
                total_deviation = predicted_deviation + residual_samples[sim_idx, day_idx]

                daily_log_fees = baseline_log_fees + total_deviation
                cumulative_fees[sim_idx] += np.exp(daily_log_fees)
                day_idx += 1

        ending_log_tvl[sim_idx] = log_tvl

        # Store cumulative activity
        cum_d_log_tvl[sim_idx] = sim_d_log_tvl
        cum_d_log_dex_vol_btc[sim_idx] = sim_d_log_dex_vol_btc
        cum_d_log_dex_vol_eth[sim_idx] = sim_d_log_dex_vol_eth
        cum_d_log_dex_vol_stable[sim_idx] = sim_d_log_dex_vol_stable
        cum_d_log_n_tx[sim_idx] = sim_d_log_n_tx

    # Convert to DataFrame
    results_df = pd.DataFrame({
        "sim_id": np.arange(n_sims),
        "ending_log_tvl": ending_log_tvl,
        "ending_tvl_usd": np.exp(ending_log_tvl),
        "cumulative_fees_eth": cumulative_fees,
        "mean_daily_fees": cumulative_fees / horizon_days,
        "cum_d_log_tvl": cum_d_log_tvl,
        "cum_d_log_dex_vol_btc": cum_d_log_dex_vol_btc,
        "cum_d_log_dex_vol_eth": cum_d_log_dex_vol_eth,
        "cum_d_log_dex_vol_stable": cum_d_log_dex_vol_stable,
        "cum_d_log_n_tx": cum_d_log_n_tx,
    })

    return results_df


def bucket_tvl(tvl_usd):
    """Assign TVL to a bucket."""
    tvl_m = tvl_usd / 1e6
    for low, high, label in TVL_BUCKETS:
        if low <= tvl_m < high:
            return label
    return "Unknown"


def analyze_activity_patterns(results_df):
    """
    Compare activity patterns in paths reaching $750M+ vs all paths.
    This answers: what activity changes characterize successful growth?
    """
    print("\n" + "=" * 70)
    print("ACTIVITY PATTERNS: PATHS REACHING $750M+ vs ALL PATHS")
    print("=" * 70)

    # Define success threshold
    success_threshold = 750_000_000

    successful = results_df[results_df["ending_tvl_usd"] >= success_threshold]
    all_paths = results_df

    metrics = [
        ("cum_d_log_dex_vol_eth", "ETH DEX Volume"),
        ("cum_d_log_n_tx", "Transaction Count"),
        ("cum_d_log_dex_vol_btc", "BTC DEX Volume"),
        ("cum_d_log_dex_vol_stable", "Stable DEX Volume"),
        ("cum_d_log_tvl", "TVL"),
    ]

    pattern_data = []
    for col, name in metrics:
        success_median = successful[col].median()
        all_median = all_paths[col].median()

        # Convert log change to approximate multiplier
        # e^x ≈ 1 + x for small x, but for larger x use actual exp
        success_mult = np.exp(success_median)
        all_mult = np.exp(all_median)

        pattern_data.append({
            "Metric": name,
            "Paths_750M+": round(success_median, 2),
            "All_Paths": round(all_median, 2),
            "Growth_Multiple": f"~{success_mult:.1f}x" if success_median > 0 else f"~{1/abs(all_mult):.1f}x shrink",
        })

        print(f"{name}:")
        print(f"  Paths -> $750M+: {success_median:+.2f} log ({success_mult:.2f}x)")
        print(f"  All paths:       {all_median:+.2f} log ({all_mult:.2f}x)")
        print()

    pattern_df = pd.DataFrame(pattern_data)

    # Save for visualization
    pattern_df.to_csv(DATA_DIR / "activity_patterns.csv", index=False)
    print(f"Activity patterns saved to {DATA_DIR}/activity_patterns.csv")

    return pattern_df


def summarize_by_bucket(results_df):
    """Summarize fee distributions by TVL bucket."""
    print("\n" + "=" * 70)
    print("FEE DISTRIBUTIONS BY ENDING TVL BUCKET (1-year horizon)")
    print("=" * 70)

    results_df["tvl_bucket"] = results_df["ending_tvl_usd"].apply(bucket_tvl)

    summary = []
    for _, _, label in TVL_BUCKETS:
        bucket_df = results_df[results_df["tvl_bucket"] == label]
        n = len(bucket_df)

        if n == 0:
            continue

        fees = bucket_df["cumulative_fees_eth"]
        daily = bucket_df["mean_daily_fees"]
        tvl = bucket_df["ending_tvl_usd"] / 1e6

        summary.append({
            "TVL Bucket": label,
            "N Sims": n,
            "Pct": f"{n/len(results_df)*100:.1f}%",
            "Median TVL ($M)": f"{tvl.median():.0f}",
            "Annual Fees (ETH)": f"{fees.median():.0f}",
            "P10": f"{fees.quantile(0.10):.0f}",
            "P90": f"{fees.quantile(0.90):.0f}",
            "Daily (ETH)": f"{daily.median():.1f}",
        })

    summary_df = pd.DataFrame(summary)
    print(summary_df.to_string(index=False))

    return summary_df


def main():
    print("Loading data...")
    df = load_data()

    # Split: train on Base + Arb
    train_df = df[df["chain"].isin(["base", "arbitrum"])].copy()
    print(f"Training data: {len(train_df)} observations")

    # Estimate model
    print("\nEstimating fee model...")
    model, coefficients, residuals = estimate_fee_model(train_df)
    print(f"Model R²: {model.rsquared:.4f}")
    print(f"Coefficients: {dict(zip(['const'] + FEATURE_COLS + ['chain_base'], coefficients))}")

    # Create weekly blocks as numpy arrays
    print("\nCreating weekly blocks...")
    blocks = prepare_block_arrays(train_df, BLOCK_SIZE)
    print(f"Created {len(blocks)} weekly blocks")

    # Get OP starting state
    starting_state = get_op_starting_state(df)
    print(f"\nOP starting state:")
    print(f"  TVL: ${starting_state['tvl_usd']/1e6:.0f}M")
    print(f"  Daily fees (last): {starting_state['fees_eth']:.2f} ETH")
    print(f"  Fee baseline (Dec 2025 median): {starting_state['baseline_fee_eth']:.2f} ETH/day")

    # Run simulations
    print(f"\nRunning {N_SIMULATIONS} simulations over {HORIZON_DAYS} days...")
    results_df = run_simulations_vectorized(
        N_SIMULATIONS, starting_state, blocks, coefficients, residuals, HORIZON_DAYS
    )

    # Summary statistics
    print("\n" + "=" * 70)
    print("OVERALL SIMULATION RESULTS (1-year horizon)")
    print("=" * 70)
    print(f"Ending TVL distribution:")
    print(f"  P10: ${results_df['ending_tvl_usd'].quantile(0.10)/1e6:.0f}M")
    print(f"  P25: ${results_df['ending_tvl_usd'].quantile(0.25)/1e6:.0f}M")
    print(f"  P50: ${results_df['ending_tvl_usd'].quantile(0.50)/1e6:.0f}M")
    print(f"  P75: ${results_df['ending_tvl_usd'].quantile(0.75)/1e6:.0f}M")
    print(f"  P90: ${results_df['ending_tvl_usd'].quantile(0.90)/1e6:.0f}M")

    print(f"\nAnnual cumulative fees distribution (ETH):")
    print(f"  P10: {results_df['cumulative_fees_eth'].quantile(0.10):.0f}")
    print(f"  P25: {results_df['cumulative_fees_eth'].quantile(0.25):.0f}")
    print(f"  P50: {results_df['cumulative_fees_eth'].quantile(0.50):.0f}")
    print(f"  P75: {results_df['cumulative_fees_eth'].quantile(0.75):.0f}")
    print(f"  P90: {results_df['cumulative_fees_eth'].quantile(0.90):.0f}")

    # Summarize by TVL bucket
    summary_df = summarize_by_bucket(results_df)

    # Analyze activity patterns (successful vs all paths)
    pattern_df = analyze_activity_patterns(results_df)

    # Save results
    results_df.to_csv(DATA_DIR / "simulation_results.csv", index=False)
    summary_df.to_csv(DATA_DIR / "simulation_summary.csv", index=False)
    print(f"\nResults saved to {DATA_DIR}/simulation_results.csv")
    print(f"Summary saved to {DATA_DIR}/simulation_summary.csv")


if __name__ == "__main__":
    main()
