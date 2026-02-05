-- https://dune.com/queries/6654738
select blockchain, block_date, sum(tx_fee_raw/1e18) as tx_fee_eth
from gas.fees
where blockchain IN ('arbitrum','optimism','base')
and block_date >= date '2025-01-01'
and block_date < date '2026-01-01'
group by blockchain, block_date
order by block_date asc, blockchain asc;