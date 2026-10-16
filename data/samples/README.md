# Replay samples

These CSVs contain the first 800 timestamps from day 0 of the local Round 1 and Round 2 competition archives, with public trades at those timestamps. TradeTell uses them to run its built-in Traders in the Replay lab. The samples are deterministic and small enough to ship with the Streamlit app.

The results cover only these samples. They do not represent a full competition day or final strategy performance. The replay also cannot model queue priority, conversions, or Round 2 market-access bidding.

Some archive rows have no bid or ask and record a zero mid price. The replay treats those rows as unavailable quotes and carries forward the last valid mid price when valuing open inventory.
