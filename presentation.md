This file is structured for conversion into a presentation format. Headers, Byline, Bullets, {Image/Chart/Table Placeholder}, [Layout and/or other Commentary NOT to be used as literal text]

----------------------

# DeFi Data Scientist Case Study [Title Slide]
Carlos Mercado // @charliemarketplace

# Intro to Me [Text left, Image Right Slide]
Hi all! A brief note on my relevant experience
* 10+ years across industries using data to grow businesses (freight brokerage, startups, consulting, crypto)
* 8+ years in data science/AI (back when it was called "big data" and natural language processing)
* Raised, hired, architected, audited, deployed True Freeze on eth mainnet (primitive still live today!)
* 3+ years at Flipside Crypto developing AI to scale crypto research, advising major L1/L2s on incentives design, data-driven growth, product development (Avalanche, NEAR, Aptos, Solana, and others.)
{Image: Headshot pic}

# The Case Study Goals [Title + Text Only Slide]
1. Identify measurable characteristics of a DeFi ecosystem
2. Tie those characteristics to sequencer fee revenue
3. Build a projection framework that can model upside/downside scenarios
4. Project sequencer fee revenue on OP Mainnet assuming different growth targets are hit (e.g. $500M, $750M, or $1B TVL)
5. Make recommendations to our growth, product, and executive teams based on your findings

# Agenda [Title + Text Only Slide]
* My Thesis/Prior on characteristics most tied to revenue (growth)
* Data Collected & Sources
* Key Takeaways
* Pre-Exploration Model Design & Hypotheses Tested
* Data Exploration & Caveats
* Model Results & Interpretation
* Application to OP / Validation
* Projection of Fees (Upside/Downside)
* Business Recommendations
* Conclusion / Key Takeaways

# My Priors on Growth for L1/L2 Chains [Table Slide]
I always try to bring an intenational-trade/macro economics lens to crypto. Trade is good - specialization is good. Different categories of activity have different impacts. Directionality of effect is important for understanding where specific decisions can change outcomes.

* Users: Most externally owned accounts (EOAs) are one-and-done. It is important to capture users early, point them to protocols, and retain them.
* Transactions: Most transactions are simple p2p transfers of the native asset, among smart contract interactions dex swaps significantly lead over more complex transactions (adding liquidity, borrowing from a lending market, minting NFTs, etc.)
* Tokens: The more high value tokens (Majors) available the more optionality there is for onboarding and more complex interaction; more stablecoins is critical for enabling users to risk-off without capital flight (exiting the chain entirely).
* Whales, Bots, and Sharps: Sophisticated users drive most arbitrage flows, pay a disproportionate share of fees, and submit a disproportionate share of transactions.
* Stocks vs Flows: Volume pays fees, Total Value Locked (TVL) is an outcome not an input. People make large deposits and keep them deposited because other users will pay (protocol) fees to swap/borrow against the deposits. The Mechanism of Action is critical for growing fee revenue.

# Data Collected [Title + Two Text Slide]
[Left] 
DeFiLlama: 
* TVL: Daily level in USD EXCLUDING: Staking, Pool2, Borrows, Double Count, Liquid Staking, Vesting These are the DeFiLlama defaults.
* Stablecoin Supply: Daily Level USDC Market Cap and USDT Market Cap (if USDT is on the chain). DefiLlama Chain Stats Stablecoin Token-Market Cap.
[Right]
Dune: 
* Daily Level DEX Buy Volume of BTC, ETH, and Stablecoins 
* Daily Level Lending Market Borrow Volume of BTC, ETH, and Stablecoins
* Daily Level count of transaction hashes
* Daily Level Tx Fees paid (in ETH)
* Daily Level ETH Price Open-Low-High-Close

# Key Takeaways [Title + Text Only Slide]
* TVL is an outcome, changes in TVL do not cause changes in activity or fees. This tracks, as chains have done numerous tricks to rent TVL (RWAs, points campaigns) and they don't cause activity. TVL does *enable* activity (you need liquidity to do swaps in size).
* Base and Arbitrum had very different growth trends in 2025 - but fundamentally the fees were a function of activity, the chains were not fundamentally different (enough) to have strong "fixed effects" (non-random structural effects on fees separate from activity/TVL assignable to the chain's unique proposition).
* A model on *changes* to activity causing *changes* to fees (relative to some baseline) is highly explanatory. Despite large TVL differences between Base, Arbitrum, and OP Mainnet - we do know what moves the needle on fees.
* High quality simulations, sampled from historical changes to TVL, Activity, and Fees, enable us to answer the following: *Conditional* (i.e., assuming) on OP hitting certain TVL targets - what *changes to activity* occur - and how does those changes cause *changes to fees*?

# Model Design & Hypotheses Tested [Title + Text Only Slide]
Before looking at the data I had the following priors & theory RE: the mechanism of action of TVL, Activity, and Fees.

I believed:

* Chains are Unique - they have different protocols (perps), connections (central exchanges, stablecoins), gas limit/throughput, tokens available, etc. So I wanted to measure Fixed Effects - (non-random structural effects assignable to its-the-chain.)
* TVL does not cause activity - despite TVL enabling activity (you need liquidity depth to do hard things), my experience told me that TVL is too high level a metric. It's too passive and chains have tried lots of hacks to rent TVL (RWAs, etc.) in hopes that it triggers activity. 
* DeFi is the primary driver of activity and thus fees - specifically swaps and lending; and in these Major tokens (BTC, ETH, Stablecoins) are disproportionate drivers (note: differences in memecoins/alts would be captured in ETH activity since these tokens nearly always pair against ETH when liquidity is seeded). 
* Lending is especially critical as on-chain leverage and de-leverage. This enables "credit expansion" (borrowing stablecoins to sell them and double down on BTC for example) and drives fees from sophisticated users.
* Stablecoin supply is critical defense - you need *native* stablecoins to allow for risk off behavior on-chain and prevent capital flight to central exchanges. Stablecoins allow prices to chain without activity crashing.
* Price Volatility is the primary driver of TVL changes (and activity!) in short-term (daily level) because of *price effects* (that is- TVL changes *mostly* because the price of the tokens inside contracts change not because of large deposits/withdrawals from contracts in response to prices changing.)
* The volatility in crypto is concentrated, autoregressive, and random - that is, crazy days happen without notice, they generate disproprtionate fees in a short time period, and they leave traces for days after. 


Δlog(DEX_vol)ᵢₜ = α + β₁·Δlog(TVL)ᵢₜ + β₂·volatilityₜ + γᵢ + εᵢₜ
Δlog(Borrow_vol)ᵢₜ = α + β₁·Δlog(TVL)ᵢₜ + β₂·volatilityₜ + γᵢ + εᵢₜ

# Model Results: What Actually Drives Fees [Title + Table Slide]

After testing the two-link model (TVL->Activity->Fees), the TVL->Activity link broke. Revised to a direct reduced-form model:

d_log(fees) ~ d_log(dex_vol_btc) + d_log(dex_vol_eth) + d_log(dex_vol_stable) + d_log(borrow_vol_stable) + d_log(stablecoin_supply) + d_log(n_tx) + eth_volatility + chain_fe

| Predictor | Coefficient | Significant? | Interpretation |
|-----------|-------------|--------------|----------------|
| d_log_n_tx | **1.83** | Yes (p<0.001) | 1% more txs -> 1.8% more fees |
| d_log_dex_vol_eth | **0.61** | Yes (p=0.001) | 1% more ETH trading -> 0.6% more fees |
| eth_volatility | **2.99** | Yes (p<0.001) | Volatile days = more fees |
| d_log_dex_vol_btc | 0.06 | No | Absorbed by ETH vol |
| d_log_dex_vol_stable | 0.10 | No | Not a driver |
| d_log_borrow_vol_stable | 0.09 | No | Not a driver |
| d_log_stablecoin_supply | 0.00 | No | Stock, not flow |
| chain_base | 0.00 | No | No fixed effects |

R-squared = 0.589. Model explains 59% of fee variation.

# Key Finding: Transaction Count is #1 [Title + Text Only Slide]

Transaction count has nearly 2x the elasticity of DEX volume (1.83 vs 0.61).

Why? Fees are paid per transaction, not per dollar traded. More transactions = more fees, regardless of trade size.

This explains Base vs Arbitrum:
* Base: 13.4M daily transactions, $15.5M monthly revenue
* Arbitrum: 1.6M daily transactions, $6.5M monthly revenue
* Base has 8x the transactions, 2.4x the revenue

# Validation: Model Generalizes to OP [Title + Text Only Slide]

Trained on Base + Arbitrum, validated on Optimism (held out):

| Metric | Value |
|--------|-------|
| Correlation (pred vs actual) | 0.72 |
| Within 1 std | 79% |
| Within 2 std | 96% |

Model predicts OP fee changes with 72% correlation despite OP being 10x smaller than training chains.

# Monte Carlo: 100,000 Simulations [Title + Text Only Slide]

Setup:
* Start: OP current state ($292M TVL, 0.65 ETH/day fees)
* Horizon: 365 days
* Method: Sample weekly blocks of activity from Base/Arb, apply model coefficients
* TVL accumulates as outcome (not target)

Filter simulations by ending TVL to answer: "If TVL reaches $X, what fees?"

# Simulation Results: TVL Doesn't Drive Fees [Title + Table Slide]

| TVL Bucket | % of Paths | Median Annual Fees | Daily Avg |
|------------|------------|-------------------|-----------|
| <$400M | 62% | 334 ETH | 0.9 ETH |
| $400-500M | 16% | 337 ETH | 0.9 ETH |
| $500-750M | 17% | 343 ETH | 0.9 ETH |
| $750M-1B | 4% | 351 ETH | 1.0 ETH |
| >$1B | 1.5% | 362 ETH | 1.0 ETH |

**Key insight:** Paths reaching >$1B TVL only have 8% higher fees than paths staying at <$400M.

TVL growth correlates with activity growth, but doesn't cause it.

# What Differentiates Successful Paths? [Title + Table Slide]

Simulations reaching $750M+ TVL had fundamentally different activity patterns:

| Metric | Paths → $750M+ | All Paths | Difference |
|--------|----------------|-----------|------------|
| ETH DEX Volume | **1.76x** | 0.52x | Growing vs shrinking |
| Transaction Count | **1.53x** | 1.16x | 32% more growth |
| BTC DEX Volume | **2.02x** | 0.84x | Growing vs shrinking |

The paths that reach $750M+ aren't just "lucky" — they sample weeks with sustained activity growth.

**The average path has shrinking DEX volume** (ETH vol down 48%). Reaching high TVL requires flipping from contraction to **~1.8x growth** in DEX activity.

# Fee Projections at TVL Targets [Title + Text Only Slide]

Conditional on reaching TVL targets (from 100k simulations):

| If TVL Reaches... | Expected Annual Fees | Daily Run Rate |
|-------------------|---------------------|----------------|
| $500-750M | ~343 ETH | ~0.9 ETH/day |
| $750M-1B | ~351 ETH | ~1.0 ETH/day |
| >$1B | ~362 ETH | ~1.0 ETH/day |

Reference: OP current = 0.65 ETH/day (Dec 2025)

Reaching $1B TVL would increase fees by ~50% over current baseline - but 62% of simulated paths stay below $400M TVL.

# Business Recommendations [Title + Text Only Slide]

Based on model findings:

1. **Prioritize transaction count over TVL**
   * Transaction count has 1.83x elasticity vs 0.61x for DEX volume
   * Paths reaching $750M+ grew transactions **1.53x** (vs 1.16x average)
   * Focus on retail/micro-transaction use cases (gaming, social, micropayments)

2. **ETH trading is the DEX driver**
   * ETH DEX volume is the only significant trading predictor
   * Successful paths grew ETH DEX volume **1.76x** (average path *shrank* to 0.52x)
   * Prioritize ETH liquidity depth and pairs

3. **TVL growth requires activity growth**
   * Paths reaching $750M+ grew DEX volumes ~2x and n_tx 1.5x
   * Average path has **shrinking DEX volume** — TVL growth requires reversing this
   * Focus on *active* TVL that generates transactions

4. **Volatility is exogenous but important**
   * Model coefficient of 3.0 - can't control but can prepare
   * High-vol periods are fee-generating opportunities
   * Ensure infrastructure handles vol spikes

# Conclusion [Title + Text Only Slide]

* TVL does not cause fees - activity does
* Transaction count is the strongest fee driver (1.83x elasticity)
* ETH trading volume is the key DEX metric (0.61x elasticity)
* Reaching $750M TVL requires: **1.8x DEX volume growth**, **1.5x transaction growth**
* Average path has **shrinking** DEX volume — growth requires reversing this trend
* Only 5.5% of simulated paths reach $750M+ TVL
* To grow fees: grow transactions and ETH trading activity, not idle TVL





