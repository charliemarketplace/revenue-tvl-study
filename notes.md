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

## Model Estimation Results

### Link 1 Breaks: ΔTVL Does NOT Predict Δactivity

The two-link model assumption failed at Link 1:

| Model | R² | d_log_tvl coef | p-value |
|-------|-----|----------------|---------|
| ΔTVL → ΔDEX vol | 0.11 | -0.73 | 0.56 |
| ΔTVL → ΔBorrow vol | 0.06 | 0.38 | 0.71 |

**TVL changes don't predict activity changes.** Volatility drives activity (coef ~5.5, p<0.001), not TVL.

### Link 2 Works: Δactivity → Δfees (R² = 0.51)

| Predictor | Coef | p-value | Interpretation |
|-----------|------|---------|----------------|
| d_log_total_dex_vol | **0.95** | <0.001 | 1% ↑ DEX vol → 0.95% ↑ fees |
| d_log_total_borrow_vol | 0.13 | 0.12 | Not significant |
| d_dex_eth_share | **2.97** | 0.003 | ETH-heavy trading → more fees |
| eth_volatility | **3.46** | <0.001 | Volatile days = more fees |

**DEX volume dominates fee variance** (41% of R² alone via Shapley-lite).

### Fixed Effects Are Zero

Chain FE coefficient ≈ 0 (p > 0.9) across all models. Base and Arbitrum behave identically after controlling for activity and volatility. Good for generalization to OP.

### Autocorrelation: Fees Mean-Revert

Durbin-Watson = 2.65 (negative autocorrelation). Adding AR(1) term:
- Lagged fees coef = **-0.22** (p<0.001)
- Fees partially correct after spikes
- DW improves to 2.33

Core finding (DEX vol dominates) robust to AR(1) specification.

### TVL Trajectories Are Divergent

| Chain | 2025 TVL Change | Activity Intensity (DEX/TVL) |
|-------|-----------------|------------------------------|
| Arbitrum | -1.6% | 22% daily |
| Base | +40.1% | 32% daily |
| Optimism | **-62.9%** | **10% daily** |

OP's problem isn't fee capture—it's **low activity intensity**. OP captures 0.077 ETH per $1M DEX (highest!), but only turns over 10% of TVL daily (half of peers).

## Key Insight: TVL Is an Outcome, Not a Driver

The original framing "conditional on TVL, what fees?" is flawed because:

1. **TVL doesn't cause activity** — both respond to market conditions
2. **Activity intensity varies** — same TVL can mean very different DEX volumes
3. **TVL trajectories diverge** — OP shrinking, Base growing, but fee dynamics are the same

### Reframed Question

> "If OP reaches $750M TVL **with peer-like activity intensity**, what fees?"

This requires assuming an activity intensity scenario, not just a TVL target.

### Scenario Analysis Approach

Instead of Monte Carlo on TVL paths, use:

```
Daily fees = TVL × activity_intensity × fee_yield_per_dex
```

| Scenario | TVL | Intensity | DEX Vol | Fees (ETH/day) |
|----------|-----|-----------|---------|----------------|
| Current OP | $440M | 10% | $44M | 3.4 |
| OP at $750M (same) | $750M | 10% | $75M | 5.8 |
| OP at $750M (Base-like) | $750M | 32% | $240M | 18.5 |
| OP at $750M (Arb-like) | $750M | 22% | $165M | 12.7 |

### Presentation Implication

The "link break" is a finding, not a failure. Present it as:

1. **Hypothesis:** TVL drives activity drives fees
2. **Finding:** Link 1 doesn't hold — TVL and activity co-move with volatility but TVL doesn't predict activity
3. **Implication:** Growing TVL alone won't increase fees; need to grow *active* TVL
4. **Recommendation:** Prioritize DEX liquidity depth (POL), not idle capital accumulation

## Modeling Challenge: TVL as Outcome

### Monte Carlo Still Needed

Monte Carlo remains important for modeling upside/downside uncertainty. The question is what to simulate.

### Bayesian Framing Considered

Proposed structure:
- **Prior:** P(activity | TVL level) from empirical data
- **Likelihood:** fees = f(activity) from Link 2 model
- **Posterior:** P(fees | TVL target)

Problem: Need to define what "conditioning on TVL" means when TVL is an outcome.

### Activity Intensity Rejected

"Activity intensity" (DEX vol / TVL) is too simple—it mostly measures memecoin/altcoin churn. OP isn't "low intensity"; it's **conservative** (disproportionately BTC/ETH/stables which naturally have lower turnover).

### DEX Volume Data Clarification

- Our Dune data: ETH volume includes ETH leg of MEME/ETH swaps (captures speculation indirectly)
- DefiLlama filtered view: More restrictive token allowlist
- Decision: Focus on BTC/ETH/stable buy volumes, not DefiLlama totals

Composition tells the story:
- **ETH buy volume** = includes speculation demand
- **Stable buy volume** = risk-off flows
- **BTC buy volume** = long-term holding

### TVL Distribution Problem

Target TVL levels vs. observed data:

| Target | Base Coverage | Arb Coverage | OP Coverage |
|--------|---------------|--------------|-------------|
| $500M | Never (min $2.2B) | Never (min $1.9B) | 295 days |
| $750M | Never | Never | 18 days |
| $1B | Never | Never | 0 days |

**Base and Arbitrum have never operated at target TVL levels.** Can't directly sample "what did Base look like at $750M?"—it never happened.

### The Core Conceptual Problem

Original idea: Use diffs to simulate paths, accumulate to TVL targets via Brownian bridge.

But if TVL is an outcome (not a driver), **what does it mean to accumulate changes to TVL?**

TVL, activity, and fees all respond to underlying market conditions. Simulating a "path to $750M TVL" implies TVL is controllable or targeted, but it's actually an emergent outcome of:
- Market conditions (volatility, sentiment)
- Protocol decisions (incentives, liquidity programs)
- User behavior (speculation vs. holding)

### Open Question

How to build a projection framework that:
1. Conditions on TVL targets (per task requirements)
2. Acknowledges TVL is non-causal
3. Captures upside/downside via Monte Carlo
4. Uses the diffs-based model we've estimated

Possible directions:
- Model fees directly with TVL as a covariate (not causal, just correlated)
- Simulate activity paths, let TVL be a derived outcome
- Use separate volume elasticities (ETH, BTC, stable) instead of aggregate intensity

## Block Bootstrap Monte Carlo

### Chosen Approach

Sample daily diffs from Base/Arb joint distribution, apply to OP starting state, let TVL be an **outcome** of each simulation (not a target). Then filter simulations by ending TVL to answer "if TVL reached $750M, what fees?"

```
for sim in range(N_sims):
    state = op_current  # (log_tvl, log_eth_vol, log_btc_vol, log_stable_vol, log_fees)
    for week in range(horizon // 7):
        week_shocks = sample_week(base_arb_diffs)
        for shock in week_shocks:
            state = state + shock
    # Record ending (tvl, cumulative_fees)
# Group by ending TVL bucket → fee distribution per bucket
```

### Why Weekly Blocks

i.i.d. day sampling breaks temporal structure:
- Fees mean-revert (AR(1) = -0.22) — **not weak**
- Half-life of a fee shock ≈ 3 days: `log(0.5) / log(0.78) ≈ 2.8 days`
- A week captures most of the mean-reversion dynamics
- Volatility also clusters (high vol days come in runs)

Weekly blocks preserve within-week AR structure. ~104 non-overlapping weeks available (52 per chain).

### Block Boundary Issue

The transition between sampled weeks won't perfectly respect cross-week AR. Acceptable because:
- Most mean-reversion happens within 3 days (captured by the block)
- We're modeling shocks to a different chain anyway (not exact replication)
- Alternative (parametric VAR) adds complexity without clear benefit

### Interpretation

This approach answers: "If OP experienced Base/Arb-like market dynamics, where might TVL and fees end up?"

TVL outcomes will vary across simulations. Filtering by ending TVL bucket gives:
- P(fees | TVL ended near $500M)
- P(fees | TVL ended near $750M)
- P(fees | TVL ended near $1B)

The width of each distribution reflects genuine uncertainty—same TVL can come from different paths with different fee outcomes.

### Model-Based vs Pure Bootstrap

**Pure bootstrap** samples (Δtvl, Δactivity, Δfees) tuples directly—doesn't use estimated coefficients.

**Model-based simulation** (chosen approach):
1. Sample weekly blocks of (Δlog_tvl, Δlog_eth_vol, Δlog_btc_vol, Δlog_stable_vol, volatility)
2. Apply Link 2 coefficients to compute predicted Δlog_fees
3. Add residual noise (sampled from model residuals, block-sampled to preserve AR)
4. Accumulate paths

**Why model-based is better:**
- Actually uses the estimated elasticities (the whole point of the panel model)
- Enables counterfactuals: "what if OP had Base-like composition?"
- Separates signal (coefficients) from noise (residuals)
- Residuals can be block-sampled independently to preserve their AR structure

**Simulation flow:**
```
Sample weekly block of activity shocks (Δtvl, Δeth_vol, Δbtc_vol, Δstable_vol, vol)
    ↓
predicted_Δlog_fees = β₁·Δlog_eth_vol + β₂·Δlog_btc_vol + β₃·Δlog_stable_vol + β₄·vol + ...
    ↓
simulated_Δlog_fees = predicted + sampled_residual
    ↓
Accumulate: log_fees_t = log_fees_{t-1} + simulated_Δlog_fees
    ↓
After horizon: record (ending_tvl, cumulative_fees)
```

Sampling with replacement makes sense—some weeks have multi-day TVL growth, others chaotic mean-zero changes, others multi-day drops. The variety of "regimes" creates the distribution of outcomes.

### Stock vs Flow in Simulation

**Critical distinction:**
- **TVL (stock):** Accumulates diffs. `log_tvl_t = log_tvl_{t-1} + d_log_tvl`. Path-dependent.
- **Fees (flow):** Do NOT accumulate diffs. Each day's fee = `exp(baseline + deviation)`. Path-independent.

**Why fees don't accumulate:**
- Fees are earned fresh each day from that day's activity
- AR(1) = -0.22 means fees mean-revert, but this doesn't mean we chain fee levels
- If we accumulated: `log_fees_t = log_fees_{t-1} + d_log_fees`, the path would drift explosively (std grows as sqrt(T))
- Instead: `daily_fee_t = exp(baseline_log_fees + predicted_deviation_t + residual_t)`

The model coefficients tell us **how fees respond to activity shocks**, not how fees evolve as a persistent state.

**Annual fees = sum of 365 independent daily fees**, each computed from that day's sampled activity.

### Simulation Logic Summary

1. **Use Base/Arb diffs** to understand how Δactivity relates to Δfees (model coefficients)
2. **Start from OP's current state** (TVL, baseline fees)
3. **Draw weekly blocks** (with replacement) of (Δlog_tvl, Δlog_dex, Δlog_borrow, volatility, composition)
4. **For each day:**
   - TVL accumulates: `log_tvl += d_log_tvl`
   - Fees computed fresh: `daily_fee = exp(baseline + β·activity_shock + residual)`
5. **After 365 days:** Record (ending_tvl, cumulative_fees)
6. **Filter by TVL bucket:** "In paths where TVL reached $750M, what was the fee distribution?"

### Reverse Inference: Activity Patterns → TVL Growth

The simulation enables a second question beyond fees:

> "In simulations where TVL hit $750M+, what activity patterns were sampled?"

This is **reverse inference**:
- Were growth paths dominated by high-ETH-volume weeks? → Prioritize speculation/meme activity
- Were growth paths dominated by low-volatility accumulation? → Prioritize sticky capital
- Were growth paths correlated with BTC-heavy composition? → Focus on BTC integrations

**Product/business implications:**
- The activity regimes that produce TVL growth inform where to allocate resources
- If "high ETH churn" weeks drive growth, prioritize DEX liquidity programs
- If "stable accumulation" weeks drive growth, prioritize yield opportunities

This turns Monte Carlo from a forecasting tool into a **strategy discovery** tool.

### TVL vs Fees: The Asymmetry

**TVL: Raw accumulation (no model)**
```
log_tvl_t = log_tvl_{t-1} + d_log_tvl_from_block
ending_tvl = exp(Σ d_log_tvl over 365 days)
```
- `d_log_tvl` sampled directly from Base/Arb blocks
- No coefficients, no transformation
- Preserves raw historical TVL dynamics and correlation with activity

**Fees: Model-based computation**
```
features = [d_log_dex, d_log_borrow, composition, volatility]
deviation = β·features + residual
daily_fee = exp(baseline_log_fees + deviation)
annual_fees = Σ daily_fee over 365 days
```
- Uses estimated coefficients from panel regression
- Model transforms activity → fee deviation
- Baseline prevents drift; fees fluctuate, don't accumulate

**Why no TVL model?**
1. TVL is the **conditioning variable** — we filter by where it ends up
2. Preserves **joint distribution** of (TVL, activity) as observed
3. A TVL model would impose structure that might not transfer to OP
4. The correlation between TVL and activity is preserved by sampling them together in blocks

**Key implication:** When a simulation reaches $750M TVL, it's because it sampled blocks with net positive TVL growth. Those same blocks also had specific activity patterns. This is the "reverse inference" — we learn what activity regimes produce TVL growth.
