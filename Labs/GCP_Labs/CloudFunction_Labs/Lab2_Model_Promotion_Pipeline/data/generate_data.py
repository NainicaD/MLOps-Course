"""Generate three synthetic daily bike-rental batches for the lab.

batch_01: baseline demand (400 rows)
batch_02: demand has grown by ~1500 rentals/day (1200 rows, a few dirty rows)
batch_03: same demand level as batch_02, but from a noisy new counter (250 rows)
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent


def make_batch(n, base, seed, start, noise=300):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=n, freq="D")
    season = np.asarray((dates.month % 12) // 3 + 1, dtype=int)
    temp = np.clip(0.15 + 0.15 * season + rng.normal(0, 0.08, n), 0, 1)
    humidity = np.clip(rng.normal(0.6, 0.15, n), 0, 1)
    windspeed = np.clip(rng.normal(0.2, 0.08, n), 0, 0.6)
    workingday = np.asarray(dates.dayofweek < 5, dtype=int)
    rentals = (
        base + 5000 * temp - 1500 * humidity - 2000 * windspeed
        + 300 * workingday + rng.normal(0, noise, n)
    ).round().astype(int)
    rentals = np.clip(rentals, 0, None)
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"), "season": season,
        "temp": temp.round(3), "humidity": humidity.round(3),
        "windspeed": windspeed.round(3), "workingday": workingday,
        "rentals": rentals,
    })


b1 = make_batch(400, base=1500, seed=1, start="2024-01-01")
b2 = make_batch(1200, base=3000, seed=2, start="2025-02-05")
b2 = b2.astype({"humidity": "object", "rentals": "object"})
b2.loc[b2.sample(15, random_state=2).index, "humidity"] = ""
b2.loc[b2.sample(5, random_state=3).index, "rentals"] = -1
b3 = make_batch(250, base=3000, seed=3, start="2028-05-20", noise=900)

for name, df in [("batch_01", b1), ("batch_02", b2), ("batch_03", b3)]:
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"{name}.csv: {len(df)} rows")
