# Intara market record

Four full recorded days of the Prosperity 4 market for ASH_COATED_OSMIUM and INTARIAN_PEPPER_ROOT,
gzipped with `gzip -9 -n` from the competition data capsules:

| File day | Source |
|---|---|
| −2, −1, 0 | Round 1 capsule, `prices_round_1_day_*.csv` and `trades_round_1_day_*.csv` |
| 1 | Round 2 capsule, `prices_round_2_day_1.csv` and `trades_round_2_day_1.csv` |

The Round 2 capsule also has days −1 and 0. They cover the same stretch of the pepper root's
climb as Round 1 days −1 and 0 (about 11,000 to 13,000) with their own quotes, so they are left
out to keep one continuous record.

Streamlit serves this folder at `app/static/intara/`. The section in the browser fetches the files
and decompresses them itself, and `src/ui/workbench.py` replays the built-in Traders from the same
files, so the market you read and the market you replay are the same ticks.

Some rows have no bid or ask and record a zero mid price. The section leaves those ticks out of the
price line, and the replay carries forward the last valid mid price when valuing open inventory.
