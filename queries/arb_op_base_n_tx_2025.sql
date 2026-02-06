select blockchain, block_date, count(tx_hash) as n_tx
from gas.fees
where blockchain IN ('arbitrum','optimism','base')
and block_date >= date '2025-01-01'
and block_date < date '2026-01-01'
group by blockchain, block_date
order by block_date asc, blockchain asc;