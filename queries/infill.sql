-- =============================================================================
-- INFILL QUERIES
-- Backfill missing data from Dune outages
-- =============================================================================

-- =============================================================================
-- DEX TRADES INFILL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Arbitrum DEX: Jan 7-8, 2025 (all tokens)
-- -----------------------------------------------------------------------------
SELECT
    blockchain as chain,
    block_date,
    token_bought_address,
    token_bought_symbol,
    sum(token_bought_amount) as token_buy_volume,
    sum(amount_usd) as amount_usd
FROM dex.trades
WHERE blockchain = 'arbitrum'
    AND block_date >= DATE '2025-01-07'
    AND block_date <= DATE '2025-01-08'
    AND token_bought_address IN (
        0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f,  -- wbtc
        0x82af49447d8a07e3bd95bd0d56f35241523fbab1,  -- weth
        0xaf88d065e77c8cc2239327c5edb3a432268e5831,  -- usdc
        0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9   -- usdt
    )
GROUP BY blockchain, block_date, token_bought_address, token_bought_symbol;

-- -----------------------------------------------------------------------------
-- Base DEX: Jan 7-8, 2025 (all tokens)
-- -----------------------------------------------------------------------------
SELECT
    blockchain as chain,
    block_date,
    token_bought_address,
    token_bought_symbol,
    sum(token_bought_amount) as token_buy_volume,
    sum(amount_usd) as amount_usd
FROM dex.trades
WHERE blockchain = 'base'
    AND block_date >= DATE '2025-01-07'
    AND block_date <= DATE '2025-01-08'
    AND token_bought_address IN (
        0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf,  -- cbbtc
        0x4200000000000000000000000000000000000006,  -- weth
        0x833589fcd6edb6e08f4c7c32d4f71b54bda02913,  -- usdc
        0xfde4c96c8593536e31f229ea8f37b2ada2699bb2   -- usdt
    )
GROUP BY blockchain, block_date, token_bought_address, token_bought_symbol;

-- -----------------------------------------------------------------------------
-- Optimism DEX: Jan 6-7, 2025 (WETH, WBTC, USDT)
-- Note: USDC only missing Jan 7
-- -----------------------------------------------------------------------------
SELECT
    blockchain as chain,
    block_date,
    token_bought_address,
    token_bought_symbol,
    sum(token_bought_amount) as token_buy_volume,
    sum(amount_usd) as amount_usd
FROM dex.trades
WHERE blockchain = 'optimism'
    AND block_date >= DATE '2025-01-06'
    AND block_date <= DATE '2025-01-07'
    AND token_bought_address IN (
        0x68f180fcce6836688e9084f035309e29bf0a2095,  -- wbtc
        0x4200000000000000000000000000000000000006,  -- weth
        0x0b2c639c533813f4aa9d7837caf62653d097ff85,  -- usdc
        0x94b008aa00579c1307b0ef2c499ad98a8ce58e58   -- usdt
    )
GROUP BY blockchain, block_date, token_bought_address, token_bought_symbol;


-- =============================================================================
-- BORROW VOLUME INFILL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Arbitrum Borrow: Feb 18-19, 2025
-- -----------------------------------------------------------------------------
SELECT
    blockchain as chain,
    block_date,
    token_address,
    symbol as token_symbol,
    sum(amount) as token_amount_borrowed,
    sum(amount_usd) as amount_usd
FROM lending.borrow
WHERE blockchain = 'arbitrum'
    AND block_date >= DATE '2025-02-18'
    AND block_date <= DATE '2025-02-19'
    AND transaction_type = 'borrow'
    AND token_address IN (
        0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f,  -- wbtc
        0x82af49447d8a07e3bd95bd0d56f35241523fbab1,  -- weth
        0xaf88d065e77c8cc2239327c5edb3a432268e5831,  -- usdc
        0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9   -- usdt
    )
GROUP BY blockchain, block_date, token_address, symbol;

-- -----------------------------------------------------------------------------
-- Arbitrum Borrow: Mar 10-12, 2025
-- -----------------------------------------------------------------------------
SELECT
    blockchain as chain,
    block_date,
    token_address,
    symbol as token_symbol,
    sum(amount) as token_amount_borrowed,
    sum(amount_usd) as amount_usd
FROM lending.borrow
WHERE blockchain = 'arbitrum'
    AND block_date >= DATE '2025-03-10'
    AND block_date <= DATE '2025-03-12'
    AND transaction_type = 'borrow'
    AND token_address IN (
        0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f,  -- wbtc
        0x82af49447d8a07e3bd95bd0d56f35241523fbab1,  -- weth
        0xaf88d065e77c8cc2239327c5edb3a432268e5831,  -- usdc
        0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9   -- usdt
    )
GROUP BY blockchain, block_date, token_address, symbol;

-- -----------------------------------------------------------------------------
-- Base Borrow: Feb 18-19, 2025
-- -----------------------------------------------------------------------------
SELECT
    blockchain as chain,
    block_date,
    token_address,
    symbol as token_symbol,
    sum(amount) as token_amount_borrowed,
    sum(amount_usd) as amount_usd
FROM lending.borrow
WHERE blockchain = 'base'
    AND block_date >= DATE '2025-02-18'
    AND block_date <= DATE '2025-02-19'
    AND transaction_type = 'borrow'
    AND token_address IN (
        0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf,  -- cbbtc
        0x4200000000000000000000000000000000000006,  -- weth
        0x833589fcd6edb6e08f4c7c32d4f71b54bda02913,  -- usdc
        0xfde4c96c8593536e31f229ea8f37b2ada2699bb2   -- usdt
    )
GROUP BY blockchain, block_date, token_address, symbol;

-- -----------------------------------------------------------------------------
-- Base Borrow: Mar 10-12, 2025
-- -----------------------------------------------------------------------------
SELECT
    blockchain as chain,
    block_date,
    token_address,
    symbol as token_symbol,
    sum(amount) as token_amount_borrowed,
    sum(amount_usd) as amount_usd
FROM lending.borrow
WHERE blockchain = 'base'
    AND block_date >= DATE '2025-03-10'
    AND block_date <= DATE '2025-03-12'
    AND transaction_type = 'borrow'
    AND token_address IN (
        0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf,  -- cbbtc
        0x4200000000000000000000000000000000000006,  -- weth
        0x833589fcd6edb6e08f4c7c32d4f71b54bda02913,  -- usdc
        0xfde4c96c8593536e31f229ea8f37b2ada2699bb2   -- usdt
    )
GROUP BY blockchain, block_date, token_address, symbol;

-- -----------------------------------------------------------------------------
-- Optimism Borrow: Feb 17-19, 2025
-- -----------------------------------------------------------------------------
SELECT
    blockchain as chain,
    block_date,
    token_address,
    symbol as token_symbol,
    sum(amount) as token_amount_borrowed,
    sum(amount_usd) as amount_usd
FROM lending.borrow
WHERE blockchain = 'optimism'
    AND block_date >= DATE '2025-02-17'
    AND block_date <= DATE '2025-02-19'
    AND transaction_type = 'borrow'
    AND token_address IN (
        0x68f180fcce6836688e9084f035309e29bf0a2095,  -- wbtc
        0x4200000000000000000000000000000000000006,  -- weth
        0x0b2c639c533813f4aa9d7837caf62653d097ff85,  -- usdc
        0x94b008aa00579c1307b0ef2c499ad98a8ce58e58   -- usdt
    )
GROUP BY blockchain, block_date, token_address, symbol;

-- -----------------------------------------------------------------------------
-- Optimism Borrow: Mar 10-11, 2025
-- -----------------------------------------------------------------------------
SELECT
    blockchain as chain,
    block_date,
    token_address,
    symbol as token_symbol,
    sum(amount) as token_amount_borrowed,
    sum(amount_usd) as amount_usd
FROM lending.borrow
WHERE blockchain = 'optimism'
    AND block_date >= DATE '2025-03-10'
    AND block_date <= DATE '2025-03-11'
    AND transaction_type = 'borrow'
    AND token_address IN (
        0x68f180fcce6836688e9084f035309e29bf0a2095,  -- wbtc
        0x4200000000000000000000000000000000000006,  -- weth
        0x0b2c639c533813f4aa9d7837caf62653d097ff85,  -- usdc
        0x94b008aa00579c1307b0ef2c499ad98a8ce58e58   -- usdt
    )
GROUP BY blockchain, block_date, token_address, symbol;

-- -----------------------------------------------------------------------------
-- Optimism Borrow: Dec 25-26, 2025 (WBTC only)
-- -----------------------------------------------------------------------------
SELECT
    blockchain as chain,
    block_date,
    token_address,
    symbol as token_symbol,
    sum(amount) as token_amount_borrowed,
    sum(amount_usd) as amount_usd
FROM lending.borrow
WHERE blockchain = 'optimism'
    AND block_date >= DATE '2025-12-25'
    AND block_date <= DATE '2025-12-26'
    AND transaction_type = 'borrow'
    AND token_address = 0x68f180fcce6836688e9084f035309e29bf0a2095  -- wbtc only
GROUP BY blockchain, block_date, token_address, symbol;


-- =============================================================================
-- SUMMARY OF GAPS TO FILL
-- =============================================================================
/*
DEX TRADES:
  - arbitrum: Jan 7-8 (all tokens: WBTC, WETH, USDC, USDT)
  - base:     Jan 7-8 (all tokens: cbBTC, WETH, USDC, USDT)
  - optimism: Jan 6-7 (all tokens: WBTC, WETH, USDC, USDT)

BORROW VOLUME:
  - arbitrum: Feb 18-19, Mar 10-12 (all tokens)
  - base:     Feb 18-19, Mar 10-12 (all tokens)
  - optimism: Feb 17-19, Mar 10-11 (all tokens), Dec 25-26 (WBTC only)
*/
