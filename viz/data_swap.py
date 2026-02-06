"""
data_swap.py

Reads HTML templates with {{PLACEHOLDER}} and injects JSON data from CSV files.

Usage:
    python data_swap.py                    # Process all templates
    python data_swap.py template_name      # Process specific template

Templates are in viz/templates/
Output goes to viz/
"""

import json
import sys
from pathlib import Path

import pandas as pd
import numpy as np

# Paths
VIZ_DIR = Path(__file__).parent
TEMPLATE_DIR = VIZ_DIR / "templates"
DATA_DIR = VIZ_DIR.parent / "data" / "processed"


def load_panel_data():
    """Load the model-ready panel data."""
    df = pd.read_csv(DATA_DIR / "panel_model_ready.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_simulation_results():
    """Load Monte Carlo simulation results."""
    df = pd.read_csv(DATA_DIR / "simulation_results.csv")
    return df


def load_simulation_summary():
    """Load simulation summary by TVL bucket."""
    df = pd.read_csv(DATA_DIR / "simulation_summary.csv")
    return df


# ============================================================================
# DATA TRANSFORMERS - One per template
# ============================================================================

def transform_00a_tvl_raw():
    """Raw TVL over time by chain."""
    df = load_panel_data()
    df = df[df["chain"].isin(["arbitrum", "base"])].copy()

    result = []
    for _, row in df.iterrows():
        result.append({
            "date": row["date"].strftime("%Y-%m-%dT00:00:00.000Z"),
            "chain": row["chain"],
            "tvl_usd": round(row["tvl_usd"], 2) if pd.notna(row["tvl_usd"]) else None
        })
    return result


def transform_00b_fees_raw():
    """Raw fees (ETH) over time by chain."""
    df = load_panel_data()
    df = df[df["chain"].isin(["arbitrum", "base"])].copy()

    result = []
    for _, row in df.iterrows():
        result.append({
            "date": row["date"].strftime("%Y-%m-%dT00:00:00.000Z"),
            "chain": row["chain"],
            "fees_eth": round(row["fees_eth"], 4) if pd.notna(row["fees_eth"]) else None
        })
    return result


def transform_01_tvl_diffs():
    """TVL diffs over time by chain."""
    df = load_panel_data()
    df = df[df["chain"].isin(["arbitrum", "base"])].copy()

    result = []
    for _, row in df.iterrows():
        result.append({
            "date": row["date"].strftime("%Y-%m-%dT00:00:00.000Z"),
            "chain": row["chain"],
            "d_log_tvl": round(row["d_log_tvl"], 6) if pd.notna(row["d_log_tvl"]) else None
        })
    return result


def transform_02_fees_diffs():
    """Fee diffs over time by chain."""
    df = load_panel_data()
    df = df[df["chain"].isin(["arbitrum", "base"])].copy()

    result = []
    for _, row in df.iterrows():
        result.append({
            "date": row["date"].strftime("%Y-%m-%dT00:00:00.000Z"),
            "chain": row["chain"],
            "d_log_fees": round(row["d_log_fees"], 6) if pd.notna(row["d_log_fees"]) else None
        })
    return result


def transform_03_ntx_vs_fees():
    """Scatter: d_log_n_tx vs d_log_fees."""
    df = load_panel_data()
    df = df[df["chain"].isin(["arbitrum", "base"])].copy()
    df = df.dropna(subset=["d_log_n_tx", "d_log_fees"])

    result = []
    for _, row in df.iterrows():
        result.append({
            "chain": row["chain"],
            "d_log_n_tx": round(row["d_log_n_tx"], 6),
            "d_log_fees": round(row["d_log_fees"], 6),
            "date": row["date"].strftime("%Y-%m-%d")
        })
    return result


def transform_04_volatility_vs_fees():
    """Scatter: eth_volatility vs d_log_fees."""
    df = load_panel_data()
    df = df[df["chain"].isin(["arbitrum", "base"])].copy()
    df = df.dropna(subset=["eth_volatility", "d_log_fees"])

    result = []
    for _, row in df.iterrows():
        result.append({
            "chain": row["chain"],
            "eth_volatility": round(row["eth_volatility"], 6),
            "d_log_fees": round(row["d_log_fees"], 6),
            "date": row["date"].strftime("%Y-%m-%d")
        })
    return result


def transform_05_dex_eth_vs_fees():
    """Scatter: d_log_dex_vol_eth vs d_log_fees."""
    df = load_panel_data()
    df = df[df["chain"].isin(["arbitrum", "base"])].copy()
    df = df.dropna(subset=["d_log_dex_vol_eth", "d_log_fees"])

    result = []
    for _, row in df.iterrows():
        result.append({
            "chain": row["chain"],
            "d_log_dex_vol_eth": round(row["d_log_dex_vol_eth"], 6),
            "d_log_fees": round(row["d_log_fees"], 6),
            "date": row["date"].strftime("%Y-%m-%d")
        })
    return result


def transform_06_fee_distributions():
    """Fee distributions by TVL bucket for box plot."""
    df = load_simulation_results()

    # Get percentiles for each bucket
    buckets = ["<$400M", "$400-500M", "$500-750M", "$750M-1B", ">$1B"]
    result = []

    for bucket in buckets:
        bucket_df = df[df["tvl_bucket"] == bucket]
        if len(bucket_df) == 0:
            continue

        fees = bucket_df["cumulative_fees_eth"]
        result.append({
            "bucket": bucket,
            "n": len(bucket_df),
            "min": round(fees.min(), 1),
            "p10": round(fees.quantile(0.10), 1),
            "p25": round(fees.quantile(0.25), 1),
            "median": round(fees.quantile(0.50), 1),
            "p75": round(fees.quantile(0.75), 1),
            "p90": round(fees.quantile(0.90), 1),
            "max": round(fees.max(), 1),
            "mean": round(fees.mean(), 1)
        })

    return result


def transform_07_tvl_distributions():
    """TVL ending distributions by bucket."""
    df = load_simulation_results()

    buckets = ["<$400M", "$400-500M", "$500-750M", "$750M-1B", ">$1B"]
    result = []

    for bucket in buckets:
        bucket_df = df[df["tvl_bucket"] == bucket]
        if len(bucket_df) == 0:
            continue

        tvl = bucket_df["ending_tvl_usd"] / 1e6  # Convert to millions
        result.append({
            "bucket": bucket,
            "n": len(bucket_df),
            "pct": round(len(bucket_df) / len(df) * 100, 1),
            "median_tvl": round(tvl.median(), 0),
            "p10_tvl": round(tvl.quantile(0.10), 0),
            "p90_tvl": round(tvl.quantile(0.90), 0)
        })

    return result


def transform_08_model_coefficients():
    """Model coefficients from estimation."""
    # These are from the model run - hardcoded since they come from stdout
    return [
        {"feature": "d_log_n_tx", "coef": 1.8313, "pvalue": 0.0001, "significant": True},
        {"feature": "d_log_dex_vol_eth", "coef": 0.6110, "pvalue": 0.001, "significant": True},
        {"feature": "eth_volatility", "coef": 2.9881, "pvalue": 0.0001, "significant": True},
        {"feature": "d_log_dex_vol_stable", "coef": 0.1011, "pvalue": 0.425, "significant": False},
        {"feature": "d_log_borrow_vol_stable", "coef": 0.0859, "pvalue": 0.145, "significant": False},
        {"feature": "d_log_dex_vol_btc", "coef": 0.0568, "pvalue": 0.747, "significant": False},
        {"feature": "d_log_stablecoin_supply", "coef": 0.0013, "pvalue": 0.997, "significant": False},
    ]


def transform_09_incremental_r2():
    """Incremental R-squared for feature importance."""
    return [
        {"feature": "d_log_dex_vol_eth", "r2": 0.5051},
        {"feature": "d_log_dex_vol_btc", "r2": 0.4709},
        {"feature": "d_log_n_tx", "r2": 0.4026},
        {"feature": "d_log_dex_vol_stable", "r2": 0.3477},
        {"feature": "d_log_borrow_vol_stable", "r2": 0.2059},
        {"feature": "eth_volatility", "r2": 0.1422},
        {"feature": "d_log_stablecoin_supply", "r2": 0.0005},
    ]


def transform_10_sample_paths():
    """Sample simulation paths that reached $500M+ TVL."""
    df = load_simulation_results()

    # Filter to paths that reached $500M+
    high_tvl = df[df["ending_tvl_usd"] >= 500_000_000].copy()

    # Sample up to 50 paths for visualization
    if len(high_tvl) > 50:
        high_tvl = high_tvl.sample(50, random_state=42)

    result = []
    for _, row in high_tvl.iterrows():
        result.append({
            "sim_id": int(row["sim_id"]),
            "ending_tvl_m": round(row["ending_tvl_usd"] / 1e6, 1),
            "cumulative_fees": round(row["cumulative_fees_eth"], 1),
            "tvl_bucket": row["tvl_bucket"]
        })

    return result


def transform_11_summary_table():
    """Summary statistics table."""
    df = load_simulation_summary()
    result = df.to_dict(orient="records")
    return result


def load_activity_patterns():
    """Load activity patterns comparison data."""
    df = pd.read_csv(DATA_DIR / "activity_patterns.csv")
    return df


def transform_12_activity_patterns():
    """Activity patterns: successful paths vs all paths (log scale)."""
    df = load_activity_patterns()
    result = df.to_dict(orient="records")
    return result


def transform_12b_activity_patterns_mult():
    """Activity patterns as human-readable multipliers."""
    df = load_activity_patterns()

    result = []
    for _, row in df.iterrows():
        success_log = row["Paths_750M+"]
        all_log = row["All_Paths"]

        result.append({
            "Metric": row["Metric"],
            "Success_Mult": round(np.exp(success_log), 2),
            "All_Mult": round(np.exp(all_log), 2),
            "Success_Log": round(success_log, 2),
            "All_Log": round(all_log, 2),
        })
    return result


def transform_13_success_vs_all_scatter():
    """Scatter plot of ending TVL vs cumulative activity changes."""
    df = load_simulation_results()

    # Sample for visualization (too many points otherwise)
    if len(df) > 5000:
        df = df.sample(5000, random_state=42)

    result = []
    for _, row in df.iterrows():
        result.append({
            "ending_tvl_m": round(row["ending_tvl_usd"] / 1e6, 1),
            "cum_d_log_dex_vol_eth": round(row["cum_d_log_dex_vol_eth"], 3),
            "cum_d_log_n_tx": round(row["cum_d_log_n_tx"], 3),
            "cumulative_fees": round(row["cumulative_fees_eth"], 1),
            "reached_750m": row["ending_tvl_usd"] >= 750_000_000
        })
    return result


def transform_13b_tvl_vs_growth_mult():
    """Scatter plot with multipliers (human readable)."""
    df = load_simulation_results()

    # Sample for visualization
    if len(df) > 5000:
        df = df.sample(5000, random_state=42)

    result = []
    for _, row in df.iterrows():
        eth_mult = np.exp(row["cum_d_log_dex_vol_eth"])
        ntx_mult = np.exp(row["cum_d_log_n_tx"])

        result.append({
            "ending_tvl_m": round(row["ending_tvl_usd"] / 1e6, 1),
            "eth_dex_mult": round(eth_mult, 2),
            "n_tx_mult": round(ntx_mult, 2),
            "cumulative_fees": round(row["cumulative_fees_eth"], 1),
            "reached_750m": row["ending_tvl_usd"] >= 750_000_000
        })
    return result


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

TEMPLATES = {
    "00a_tvl_raw": transform_00a_tvl_raw,
    "00b_fees_raw": transform_00b_fees_raw,
    "01_tvl_diffs_over_time": transform_01_tvl_diffs,
    "02_fees_diffs_over_time": transform_02_fees_diffs,
    "03_ntx_vs_fees_scatter": transform_03_ntx_vs_fees,
    "04_volatility_vs_fees_scatter": transform_04_volatility_vs_fees,
    "05_dex_eth_vs_fees_scatter": transform_05_dex_eth_vs_fees,
    "06_fee_distributions_boxplot": transform_06_fee_distributions,
    "07_tvl_bucket_summary": transform_07_tvl_distributions,
    "08_model_coefficients": transform_08_model_coefficients,
    "09_feature_importance": transform_09_incremental_r2,
    "10_sample_paths_500m": transform_10_sample_paths,
    "11_summary_table": transform_11_summary_table,
    "12_activity_patterns": transform_12_activity_patterns,
    "12b_activity_patterns_mult": transform_12b_activity_patterns_mult,
    "13_success_vs_all_scatter": transform_13_success_vs_all_scatter,
    "13b_tvl_vs_growth_mult": transform_13b_tvl_vs_growth_mult,
}


def process_template(name: str):
    """Process a single template."""
    template_path = TEMPLATE_DIR / f"{name}.html"
    output_path = VIZ_DIR / f"{name}.html"

    if not template_path.exists():
        print(f"Template not found: {template_path}")
        return False

    if name not in TEMPLATES:
        print(f"No transformer for: {name}")
        return False

    # Load template
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Get data
    transformer = TEMPLATES[name]
    data = transformer()
    json_data = json.dumps(data, indent=2)

    # Replace placeholder
    html = html.replace("{{PLACEHOLDER}}", json_data)

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Created: {output_path}")
    return True


def main():
    # Ensure template directory exists
    TEMPLATE_DIR.mkdir(exist_ok=True)

    if len(sys.argv) > 1:
        # Process specific template
        name = sys.argv[1]
        process_template(name)
    else:
        # Process all templates
        for name in TEMPLATES:
            template_path = TEMPLATE_DIR / f"{name}.html"
            if template_path.exists():
                process_template(name)
            else:
                print(f"Skipping {name} - template not found")


if __name__ == "__main__":
    main()
