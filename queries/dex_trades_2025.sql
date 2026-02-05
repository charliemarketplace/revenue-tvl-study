SELECT 
    blockchain, 
    block_date, 
    token_bought_address,
    token_bought_symbol,
    sum(token_bought_amount) as token_buy_volume,
    sum(amount_usd) as token_buy_volume_usd
FROM dex.trades
WHERE blockchain IN ('arbitrum', 'optimism', 'base')
    AND block_date >= DATE '2025-01-01'
    AND block_date < DATE '2026-01-01'
    AND token_bought_address IN (
        -- Arbitrum
        0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f,  -- wbtc
        0x82af49447d8a07e3bd95bd0d56f35241523fbab1,  -- weth
        0xaf88d065e77c8cc2239327c5edb3a432268e5831,  -- usdc
        0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9,  -- usdt
        -- Base
        0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf,  -- cbbtc
        0x4200000000000000000000000000000000000006,  -- weth (base & optimism)
        0x833589fcd6edb6e08f4c7c32d4f71b54bda02913,  -- usdc
        0xfde4c96c8593536e31f229ea8f37b2ada2699bb2,  -- usdt
        -- Optimism
        0x68f180fcce6836688e9084f035309e29bf0a2095,  -- wbtc
        0x0b2c639c533813f4aa9d7837caf62653d097ff85,  -- usdc
        0x94b008aa00579c1307b0ef2c499ad98a8ce58e58   -- usdt
    )
    group by blockchain, block_date, token_bought_address, token_bought_symbol