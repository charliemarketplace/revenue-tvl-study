"""
01_load_and_clean.py

Load raw data files and produce model-ready panel dataset.

Input files:
    - data/arb_op_base_tx_fees_eth_2025.csv
    - data/*_tvl_no_inclusions.csv
    - data/dex_trades_2025.csv
    - data/lending_borrow_2025.csv
    - data/*_stablecoin_marketcaps.csv
    - data/eth_ohlc.csv
    - data/tokenlist.json

Output:
    - data/processed/panel_raw.csv (intermediate)
    - data/processed/panel_model_ready.csv (differenced, model-ready)
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path("data")
OUTPUT_DIR = DATA_DIR / "processed"
OUTPUT_DIR.mkdir(exist_ok=True)

# Token classification by chain
with open(DATA_DIR / "tokenlist.json") as f:
    TOKENS = json.load(f)


def classify_token(chain: str, address: str) -> str:
    """Classify token address into btc/eth/stable bucket."""
    address = address.lower()
    chain_tokens = TOKENS.get(chain, {})

    # Reverse lookup: address -> symbol
    for symbol, addr in chain_tokens.items():
        if addr.lower() == address:
            if symbol in ("wbtc", "cbbtc"):
                return "btc"
            elif symbol == "weth":
                return "eth"
            elif symbol in ("usdc", "usdt"):
                return "stable"
    return "other"


def parse_date(date_str):
    """Parse various date formats in the data."""
    if pd.isna(date_str):
        return pd.NaT
    date_str = str(date_str)
    # Try different formats
    for fmt in ["%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y"]:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except ValueError:
            continue
    # Fallback to pandas parser
    return pd.to_datetime(date_str)


def load_fees() -> pd.DataFrame:
    """Load transaction fees data."""
    df = pd.read_csv(DATA_DIR / "arb_op_base_tx_fees_eth_2025.csv")
    df["date"] = df["block_date"].apply(parse_date)
    df = df.rename(columns={"blockchain": "chain", "tx_fee_eth": "fees_eth"})
    return df[["chain", "date", "fees_eth"]]


def load_tvl() -> pd.DataFrame:
    """Load TVL data from per-chain files."""
    dfs = []
    chain_files = {
        "arbitrum": "arbitrum_tvl_no_inclusions.csv",
        "base": "base_tvl_no_inclusions.csv",
        "optimism": "op_tvl_no_inclusions.csv",
    }

    for chain, filename in chain_files.items():
        df = pd.read_csv(DATA_DIR / filename)
        df["chain"] = chain
        df["date"] = df["Date"].apply(parse_date)
        df = df.rename(columns={"TVL": "tvl_usd"})
        dfs.append(df[["chain", "date", "tvl_usd"]])

    return pd.concat(dfs, ignore_index=True)


def load_dex_trades() -> pd.DataFrame:
    """Load DEX trades and aggregate by token bucket."""
    df = pd.read_csv(DATA_DIR / "dex_trades_2025.csv")
    df["date"] = df["block_date"].apply(parse_date)

    # Classify each token
    df["token_class"] = df.apply(
        lambda r: classify_token(r["chain"], r["token_bought_address"]), axis=1
    )

    # Aggregate by chain/date/class
    agg = (
        df.groupby(["chain", "date", "token_class"])["amount_usd"].sum().unstack(fill_value=0)
    )

    # Rename columns
    agg = agg.rename(
        columns={"btc": "dex_vol_btc", "eth": "dex_vol_eth", "stable": "dex_vol_stable"}
    )

    # Ensure all columns exist
    for col in ["dex_vol_btc", "dex_vol_eth", "dex_vol_stable"]:
        if col not in agg.columns:
            agg[col] = 0.0

    return agg[["dex_vol_btc", "dex_vol_eth", "dex_vol_stable"]].reset_index()


def load_borrow() -> pd.DataFrame:
    """Load borrow volume data and aggregate by token bucket."""
    df = pd.read_csv(DATA_DIR / "lending_borrow_2025.csv")
    df["date"] = df["block_date"].apply(parse_date)

    # Classify each token
    df["token_class"] = df.apply(
        lambda r: classify_token(r["chain"], r["token_address"]), axis=1
    )

    # Aggregate by chain/date/class
    agg = (
        df.groupby(["chain", "date", "token_class"])["amount_usd"].sum().unstack(fill_value=0)
    )

    # Rename columns
    agg = agg.rename(
        columns={"btc": "borrow_vol_btc", "eth": "borrow_vol_eth", "stable": "borrow_vol_stable"}
    )

    # Ensure all columns exist
    for col in ["borrow_vol_btc", "borrow_vol_eth", "borrow_vol_stable"]:
        if col not in agg.columns:
            agg[col] = 0.0

    return agg[["borrow_vol_btc", "borrow_vol_eth", "borrow_vol_stable"]].reset_index()


def load_stablecoin_supply() -> pd.DataFrame:
    """Load stablecoin market caps and sum USDC + USDT."""
    dfs = []
    chain_files = {
        "arbitrum": "arbitrum_stablecoin_marketcaps.csv",
        "base": "base_stablecoin_marketcaps.csv",
        "optimism": "op_stablecoin_marketcaps.csv",
    }

    for chain, filename in chain_files.items():
        df = pd.read_csv(DATA_DIR / filename, usecols=["Date", "USDC", "USDT"])

        # Sum USDC + USDT (handle missing columns)
        usdc = pd.to_numeric(df.get("USDC", 0), errors="coerce").fillna(0)
        usdt = pd.to_numeric(df.get("USDT", 0), errors="coerce").fillna(0)

        result = pd.DataFrame(
            {
                "chain": chain,
                "date": df["Date"].apply(parse_date),
                "stablecoin_supply": usdc + usdt,
            }
        )
        dfs.append(result)

    return pd.concat(dfs, ignore_index=True)


def load_eth_ohlc() -> pd.DataFrame:
    """Load ETH OHLC data."""
    df = pd.read_csv(DATA_DIR / "eth_ohlc.csv")
    df["date"] = df["block_date"].apply(parse_date)
    df = df.rename(columns={"open": "eth_open", "high": "eth_high", "low": "eth_low"})
    # ETH OHLC is from Base, applies to all chains
    return df[["date", "eth_open", "eth_high", "eth_low"]]


def load_transaction_counts() -> pd.DataFrame:
    """Load daily transaction count data."""
    df = pd.read_csv(DATA_DIR / "arb_op_base_n_tx_2025.csv")
    df["date"] = df["block_date"].apply(parse_date)
    df = df.rename(columns={"chain": "chain_raw"})
    # Normalize chain names to match other data sources
    chain_map = {"arbitrum": "arbitrum", "base": "base", "optimism": "optimism"}
    df["chain"] = df["chain_raw"].map(chain_map)
    return df[["chain", "date", "n_tx"]]


def build_panel() -> pd.DataFrame:
    """Build raw panel by joining all data sources."""
    print("Loading fees...")
    fees = load_fees()

    print("Loading TVL...")
    tvl = load_tvl()

    print("Loading DEX trades...")
    dex = load_dex_trades()

    print("Loading borrow volume...")
    borrow = load_borrow()

    print("Loading stablecoin supply...")
    stables = load_stablecoin_supply()

    print("Loading ETH OHLC...")
    eth_ohlc = load_eth_ohlc()

    print("Loading transaction counts...")
    n_tx = load_transaction_counts()

    # Start with fees as base (defines our date range)
    panel = fees.copy()

    # Merge TVL
    panel = panel.merge(tvl, on=["chain", "date"], how="left")

    # Merge DEX volumes
    panel = panel.merge(dex, on=["chain", "date"], how="left")

    # Merge borrow volume
    panel = panel.merge(borrow, on=["chain", "date"], how="left")

    # Merge stablecoin supply
    panel = panel.merge(stables, on=["chain", "date"], how="left")

    # Merge ETH OHLC (same for all chains)
    panel = panel.merge(eth_ohlc, on=["date"], how="left")

    # Merge transaction counts
    panel = panel.merge(n_tx, on=["chain", "date"], how="left")

    # Sort
    panel = panel.sort_values(["chain", "date"]).reset_index(drop=True)

    return panel


def compute_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived columns: totals, shares, volatility."""
    df = df.copy()

    # Total DEX volume
    df["total_dex_vol"] = df["dex_vol_btc"] + df["dex_vol_eth"] + df["dex_vol_stable"]

    # Total borrow volume
    df["total_borrow_vol"] = df["borrow_vol_btc"] + df["borrow_vol_eth"] + df["borrow_vol_stable"]

    # DEX composition shares (handle division by zero)
    df["dex_btc_share"] = np.where(
        df["total_dex_vol"] > 0, df["dex_vol_btc"] / df["total_dex_vol"], 0
    )
    df["dex_eth_share"] = np.where(
        df["total_dex_vol"] > 0, df["dex_vol_eth"] / df["total_dex_vol"], 0
    )

    # Borrow composition shares
    df["borrow_btc_share"] = np.where(
        df["total_borrow_vol"] > 0, df["borrow_vol_btc"] / df["total_borrow_vol"], 0
    )
    df["borrow_eth_share"] = np.where(
        df["total_borrow_vol"] > 0, df["borrow_vol_eth"] / df["total_borrow_vol"], 0
    )

    # ETH volatility: (high - low) / open
    df["eth_volatility"] = np.where(
        df["eth_open"] > 0, (df["eth_high"] - df["eth_low"]) / df["eth_open"], 0
    )

    return df


def compute_model_ready(df: pd.DataFrame) -> pd.DataFrame:
    """Compute log-differences for model-ready dataset."""
    df = df.copy()

    # Forward-fill missing values within each chain for activity metrics
    # (handles gaps like Jan 7-8 in source data)
    fill_cols = [
        "dex_vol_btc",
        "dex_vol_eth",
        "dex_vol_stable",
        "total_dex_vol",
        "borrow_vol_btc",
        "borrow_vol_eth",
        "borrow_vol_stable",
        "total_borrow_vol",
        "n_tx",
    ]
    for col in fill_cols:
        df[col] = df.groupby("chain")[col].ffill()

    # Log transforms (add small constant to handle zeros)
    eps = 1e-6
    df["log_tvl"] = np.log(df["tvl_usd"] + eps)
    df["log_fees"] = np.log(df["fees_eth"] + eps)
    df["log_total_dex_vol"] = np.log(df["total_dex_vol"] + eps)
    df["log_total_borrow_vol"] = np.log(df["total_borrow_vol"] + eps)
    df["log_stablecoin_supply"] = np.log(df["stablecoin_supply"] + eps)
    df["log_n_tx"] = np.log(df["n_tx"] + eps)
    # Decomposed DEX volumes
    df["log_dex_vol_btc"] = np.log(df["dex_vol_btc"] + eps)
    df["log_dex_vol_eth"] = np.log(df["dex_vol_eth"] + eps)
    df["log_dex_vol_stable"] = np.log(df["dex_vol_stable"] + eps)
    # Decomposed borrow volumes
    df["log_borrow_vol_stable"] = np.log(df["borrow_vol_stable"] + eps)

    # Compute differences within each chain
    diff_cols = {
        "d_log_tvl": "log_tvl",
        "d_log_fees": "log_fees",
        "d_log_total_dex_vol": "log_total_dex_vol",
        "d_log_total_borrow_vol": "log_total_borrow_vol",
        "d_log_stablecoin_supply": "log_stablecoin_supply",
        "d_dex_btc_share": "dex_btc_share",
        "d_dex_eth_share": "dex_eth_share",
        "d_borrow_btc_share": "borrow_btc_share",
        "d_borrow_eth_share": "borrow_eth_share",
        "d_log_n_tx": "log_n_tx",
        # Decomposed DEX volumes
        "d_log_dex_vol_btc": "log_dex_vol_btc",
        "d_log_dex_vol_eth": "log_dex_vol_eth",
        "d_log_dex_vol_stable": "log_dex_vol_stable",
        # Decomposed borrow volumes
        "d_log_borrow_vol_stable": "log_borrow_vol_stable",
    }

    for new_col, src_col in diff_cols.items():
        df[new_col] = df.groupby("chain")[src_col].diff()

    # Drop first row per chain (no diff available)
    df = df.dropna(subset=["d_log_fees"])

    return df


def main():
    print("Building raw panel...")
    panel = build_panel()

    print("Computing derived columns...")
    panel = compute_derived_columns(panel)

    # Save intermediate
    panel.to_csv(OUTPUT_DIR / "panel_raw.csv", index=False)
    print(f"Saved: {OUTPUT_DIR / 'panel_raw.csv'}")

    print("Computing model-ready dataset...")
    model_ready = compute_model_ready(panel)

    # Save final
    model_ready.to_csv(OUTPUT_DIR / "panel_model_ready.csv", index=False)
    print(f"Saved: {OUTPUT_DIR / 'panel_model_ready.csv'}")

    # Summary stats
    print("\n--- Summary ---")
    print(f"Date range: {model_ready['date'].min()} to {model_ready['date'].max()}")
    print(f"Chains: {model_ready['chain'].unique().tolist()}")
    print(f"Total observations: {len(model_ready)}")
    print(f"\nObservations per chain:")
    print(model_ready["chain"].value_counts())

    print("\nMissing values in model-ready columns:")
    model_cols = [
        "d_log_tvl",
        "d_log_fees",
        "d_log_total_dex_vol",
        "d_log_total_borrow_vol",
        "d_dex_btc_share",
        "d_dex_eth_share",
        "d_borrow_btc_share",
        "d_borrow_eth_share",
        "eth_volatility",
        "d_log_n_tx",
    ]
    for col in model_cols:
        missing = model_ready[col].isna().sum()
        print(f"  {col}: {missing}")


if __name__ == "__main__":
    main()
