"""One-time download of Census ACS 5-year county data into data/acs_counties.csv.

The Census Data API requires a free key (https://api.census.gov/data/key_signup.html).
The key is read from an environment variable and never saved in the repo:

    CENSUS_API_KEY=your_key python scripts/fetch_census.py
"""
import os
import sys
from pathlib import Path

import pandas as pd
import requests

YEARS = range(2013, 2025)
VARS = ["B25001_001E", "B25004_001E", "B25004_006E", "B25077_001E", "B19013_001E"]
OUT = Path(__file__).resolve().parent.parent / "data" / "acs_counties.csv"

key = os.environ.get("CENSUS_API_KEY")
if not key:
    sys.exit("Set CENSUS_API_KEY first. Get a free key at https://api.census.gov/data/key_signup.html")

frames = []
for year in YEARS:
    resp = requests.get(
        f"https://api.census.gov/data/{year}/acs/acs5",
        params={"get": "NAME," + ",".join(VARS), "for": "county:*", "in": "state:*", "key": key},
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"{year}: skipped (HTTP {resp.status_code}: {resp.text[:120].strip()})")
        continue
    rows = resp.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["year"] = year
    frames.append(df)
    print(f"{year}: {len(df):,} counties")

if not frames:
    sys.exit("Nothing downloaded. Check that your key is active (it arrives by email and must be activated).")

OUT.parent.mkdir(exist_ok=True)
pd.concat(frames, ignore_index=True).to_csv(OUT, index=False)
print(f"Saved {OUT}")
