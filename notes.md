# Design Notes

Feedback and reasoning from project scoping.

## Initial Over-Scoping

First attempt proposed a 6-script pipeline with comprehensive data engineering. User pushed back:

> "Realistically this scope you outline is like 2-3 full time days... the key goal is discussion and technical communication."

**Lesson:** This is an interview exercise (2-3 hours). Optimize for clear thinking, not comprehensive coverage.

## Stock vs Flow Problem

Initial model proposed regressing fees on TVL directly. User identified the core issue:

> "TVL is a stock variable that changes more from price effects than anything super fundamental while fees is explicitly activity."

**The fix:** Work in differences. Model the causal chain:
```
ΔTVL → Δactivity → Δfees
```

Fees (flow) should be explained by activity (flows), not TVL (stock). TVL *enables* activity but doesn't *cause* fees directly.

## Why Panel Design?

User confirmed panel approach (Base + Arbitrum) makes sense for:
- Pooling information across chains
- Fixed effects absorb chain-specific factors
- More statistical power than single-chain regression

OP held out for validation—don't train on what you're projecting.

## Sticky Variables

User clarified variable behavior:

| Variable | Behavior |
|----------|----------|
| TVL | Sticky, price-driven changes |
| Stablecoin supply | Sticky |
| Fees | Spiky, correlated with volatility |
| DEX volume | Spiky, activity-driven |
| Borrow volume | **Flow** (daily borrows, not outstanding) |

Initial draft incorrectly listed borrow volume as stock. Corrected.

## Monte Carlo Rationale

User suggested Monte Carlo simulation instead of point estimates:

> "We can use monte carlo distributions to simulate"

**Why it's better:**
- Point estimates at $500M/$750M/$1B ignore path uncertainty
- Many ΔTVL sequences reach the same endpoint
- Monte Carlo captures distribution of outcomes (P10/P50/P90)
- Can vary volatility scenarios (calm vs turbulent)

## Connecting to Recommendations

User emphasized recommendations must be tied to evidence:

> "The types of business recommendations I would make (protocol owned liquidity, investment in stablecoins, more major tokens like BTC, better DevX) must be tied to some view into how TVL changes have correlated with changes in metrics."

**The link:** Estimated coefficients tell us which levers matter:
- If DEX-TVL elasticity is high → prioritize POL
- If stable-borrow elasticity is high → incentivize stablecoin growth
- If activity/TVL lags peers → DevX problem

Recommendations flow from coefficient comparisons, not hand-waving.

## Key Terminology

| Acronym | Meaning |
|---------|---------|
| DV | Dependent variable (fees) |
| RHS | Right-hand side (predictors) |
| FE | Fixed effects (chain-specific intercepts) |
| HAC | Heteroskedasticity and autocorrelation consistent (robust SEs) |
| ADF | Augmented Dickey-Fuller (stationarity test) |
| I(1) | Integrated order 1 (non-stationary, needs differencing) |
| VIF | Variance inflation factor (multicollinearity check) |
| POL | Protocol-owned liquidity |

## Final Model Structure

**Link 1:** ΔTVL → Δactivity (capacity/activation relationship)
**Link 2:** Δactivity → Δfees (fee generation)

Both estimated on Base + Arbitrum panel in log-differences. Applied via Monte Carlo to project OP fee distributions at TVL targets.

## Multicollinearity and Shapley Decomposition

**The problem:** Crypto metrics move together. Hot market = more DEX volume, more borrows, higher TVL. Raw coefficients become unstable when predictors are correlated.

**Diagnosis:** Compute VIF (variance inflation factor) for each predictor. VIF > 5-10 signals concern.

**Why it matters for recommendations:** We want to say "DEX volume matters more than borrow volume" to inform product decisions. With multicollinearity, raw β comparisons are unreliable.

**Solution: Shapley value decomposition**

Shapley values (from cooperative game theory) attribute explained variance to each predictor, averaging over all possible orderings. This accounts for correlations and gives a principled answer to "what share of R² does each metric explain?"

```
Example output:
  total_dex_vol explains 45% of fee variance
  borrow_vol explains 25%
  composition (btc/eth share) explains 15%
  volatility explains 15%

→ Product implication: Prioritize DEX liquidity over lending incentives
```

**Variable restructuring to reduce collinearity:**

Instead of correlated raw volumes:
```
dex_vol_btc, dex_vol_eth, dex_vol_stable  (correlated)
```

Use total + composition:
```
log(total_dex_vol) + btc_share + eth_share
```

This separates "how much activity" from "what kind of activity." Composition coefficients answer: "Holding total volume constant, is BTC-heavy volume more fee-generative?"

## Brownian Bridge Assumption

Monte Carlo paths use a Brownian bridge to hit TVL targets. This is scenario analysis, not forecasting.

**What we're answering:**
> "Given TVL reaches $X, what's the distribution of fee outcomes across plausible growth paths?"

**What we're NOT answering:**
> "What's the probability OP reaches $X?"

**Key assumption:** The ΔTVL → Δactivity relationship is path-independent. A 1% TVL increase has the same activity effect whether the path eventually hits $500M or $1B. This is defensible for conditional projection but should be stated explicitly.

## Total + Composition Variable Construction

The total + composition restructuring (e.g., `log(total_dex_vol) + btc_share + eth_share`) is an **implementation detail in data prep**, not a change to the model structure.

Panel approach, differences, two-link model, Monte Carlo—all unchanged. This is just how we construct RHS variables in `01_load_and_clean.py`:

```
# Raw:     dex_vol_btc, dex_vol_eth, dex_vol_stable
# Derived: total_dex_vol = sum of above
#          btc_share = btc / total
#          eth_share = eth / total
# Model:   Δlog(total) + Δ(btc_share) + Δ(eth_share)
```

Separates scale ("how much volume") from composition ("what kind"). Reduces collinearity and enables cleaner interpretation of composition effects.

## Endogeneity Acknowledgment

ΔTVL → Δactivity is a simplification. Reality is likely:

```
Exogenous shock (bull market, narrative, macro)
    ├── → ΔTVL
    └── → Δactivity
```

Both are responses to underlying conditions, not causally linked. Acceptable for this analysis because:
- Goal is conditional projection ("if TVL reaches X, expect Y fees"), not causal inference
- Audience is crypto-native and understands "everything moves together"
- Stated assumption: OP's growth composition resembles Base/Arbitrum

## Data Specification

### Raw Data (per chain, per day)

| Column | Unit | Definition |
|--------|------|------------|
| `chain` | — | Chain identifier (base, arbitrum, op) |
| `date` | — | Calendar date |
| `tvl_usd` | USD | Total value locked |
| `fees_eth` | ETH | Sequencer fees collected (native unit) |
| `dex_vol_btc` | USD | DEX sell volume in BTC pairs |
| `dex_vol_eth` | USD | DEX sell volume in ETH pairs |
| `dex_vol_stable` | USD | DEX volume in stablecoin pairs |
| `borrow_vol_usd` | USD | Daily new borrows initiated (flow) |
| `stablecoin_supply` | USD | Total stablecoin supply on chain |
| `eth_high` | USD | ETH daily high price |
| `eth_low` | USD | ETH daily low price |
| `eth_open` | USD | ETH daily open price |

### Derived Columns

| Column | Definition |
|--------|------------|
| `total_dex_vol` | `dex_vol_btc + dex_vol_eth + dex_vol_stable` |
| `dex_btc_share` | `dex_vol_btc / total_dex_vol` |
| `dex_eth_share` | `dex_vol_eth / total_dex_vol` |
| `eth_volatility` | `(eth_high - eth_low) / eth_open` |
| `log_*` | Log-transformed versions of levels |

### Model-Ready Columns (differenced)

| Column | Definition |
|--------|------------|
| `d_log_tvl` | `Δlog(tvl_usd)` |
| `d_log_fees` | `Δlog(fees_eth)` — **dependent variable** |
| `d_log_total_dex_vol` | `Δlog(total_dex_vol)` |
| `d_log_borrow_vol` | `Δlog(borrow_vol_usd)` |
| `d_dex_btc_share` | `Δ(dex_btc_share)` |
| `d_dex_eth_share` | `Δ(dex_eth_share)` |
| `eth_volatility` | Level (already stationary) |

## Lag Structure Decision

**Question:** Should ΔTVL_t predict Δactivity_t (same-day) or Δactivity_{t+1} (lagged)?

**Decision:** Start same-day. For Monte Carlo over 180-day horizon, a 1-day lag doesn't materially change cumulative results. Path variance and coefficient variance dominate. Can check lagged spec as robustness if needed.

## Panel Regression Notes

- Fixed effects (FE) is correct—chain-specific unobservables likely correlated with regressors
- Two-way FE (chain + time) could absorb market-wide daily shocks
- N=2 chains is thin for clustering; use HAC standard errors instead
- Honest framing: "pooling two time series with shared slope and chain-specific intercepts"

## Presentation Structure

Preferred narrative flow:

1. **Title** — case study framing
2. **Intro to me** — credibility framing, context that this demonstrates skills for a role
3. **Context** — the case study goal
4. **Main takeaway** — upfront, before the journey
5. **Agenda** — roadmap of how we got to the takeaway
6. **Data collected** — sources, coverage, variables
7. **Model design choice & why** — two-link model, panel, differences
8. **Summary of data exploration** — distributions, stationarity, correlations
9. **Model results** — coefficients, R², Shapley output
10. **Interpreting results & deriving BI** — "DEX volume matters most, here's why"
11. **Validation & forecasting approach** — OP holdout, Monte Carlo setup (details TBD)
12. **Forecasting results** — P10/P50/P90 at TVL targets
13. **Benchmarking BI & recommendations** — tie to hands-on chain experience (POL, TVL composition curation, onboarding strategies)

**Presentation best practices:**
- Tell them what you'll tell them → tell them → tell them what you told them
- Slide titles state the point, not the topic ("DEX volume drives 50% of fee variance" not "Analysis")
- Visuals should be self-evident with title as the takeaway
- One-sentence and one-paragraph takeaways prepared upfront
