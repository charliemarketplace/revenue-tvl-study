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
