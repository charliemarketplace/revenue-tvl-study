-- https://dune.com/queries/6655853
with hourly_price AS (
SELECT 
    blockchain, 
    date_trunc('hour', block_time) as block_hour,
    block_date,
    token_bought_address,
    token_bought_symbol,
    sum(token_bought_amount) as token_buy_volume,
    sum(amount_usd) as token_buy_volume_usd,
    (sum(amount_usd) / sum(token_bought_amount)) as hourly_price_usd
FROM dex.trades
WHERE blockchain IN ('base')
    AND block_date >= DATE '2025-01-01'
    AND block_date < DATE '2026-01-01'
    AND token_bought_address IN (
        0x4200000000000000000000000000000000000006  -- weth (base & optimism)
    )
GROUP BY blockchain, date_trunc('hour', block_time), block_date, token_bought_address, token_bought_symbol
)
SELECT 
    blockchain,
    block_date,
    token_bought_address,
    token_bought_symbol,
    -- Open: price associated with the earliest block_hour
    min_by(hourly_price_usd, block_hour) as open_price,
    -- High: maximum hourly price
    MAX(hourly_price_usd) as high_price,
    -- Low: minimum hourly price
    MIN(hourly_price_usd) as low_price,
    -- Close: price associated with the latest block_hour
    max_by(hourly_price_usd, block_hour) as close_price,
    -- Daily volume aggregates
    SUM(token_buy_volume) as daily_volume,
    SUM(token_buy_volume_usd) as daily_volume_usd
FROM hourly_price
GROUP BY blockchain, block_date, token_bought_address, token_bought_symbol
ORDER BY block_date DESC, blockchain, token_bought_symbol
