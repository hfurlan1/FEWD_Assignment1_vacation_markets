# Vacation Home Markets

A multi-page Streamlit app that asks whether Central Florida's vacation-home resort model
(detached homes rented short-term inside gated, amenity-rich communities) is one of a kind,
by comparing Central Florida with other U.S. tourist markets.

## Problem statement

- **Who it's for:** real estate investors, developers, and researchers deciding whether the
  Central Florida vacation-home resort model could work in another U.S. tourist market.
- **The problem:** the evidence for comparing markets (how much housing is already used as
  vacation homes, what homes cost against local incomes, and how long the tourist season lasts)
  is spread across Census tables and weather records that are hard to line up side by side.
- **Why it matters:** these resorts are built at scale, with hundreds of homes and shared
  amenities financed up front. Choosing a market without the right demand conditions is an
  expensive mistake.

## Pages

| Page | Question it answers |
|---|---|
| Home | What is this app for, and how does my focus market look right now? |
| Market Explorer | What does one market's vacation-home stock look like over time? |
| Compare Markets | Where does Central Florida rank against other tourist markets in a given year? |
| Seasonality | How many months of warm weather does each market get? |

The split moves from depth (one market) to breadth (many markets) to explanation (a demand
condition the housing data can't show). The **focus market** chosen in the sidebar is stored in
`st.session_state` and carries across every page.

## Data

- **Open-Meteo historical weather API** (live, no key): daily highs and rainfall, 2016 to 2025,
  for one point per market, fetched with `requests.get()` and cached with `st.cache_data`.
- **U.S. Census Bureau ACS 5-year estimates** (saved CSV, `data/acs_counties.csv`): housing units,
  vacant units, units held for seasonal/recreational/occasional use, median home value, and
  median household income for every U.S. county, 2013 onward. The Census API has required a key
  since May 2026, so the data is downloaded once with `scripts/fetch_census.py` and stored as a
  file; the app itself uses no keys.

## Markets

Central Florida: Orange, Osceola, and Polk counties, FL.
Comparison tourist markets: Sevier County, TN; Horry County, SC; Baldwin County, AL;
Comal County, TX; Riverside County, CA.
Metro benchmark: Travis County, TX.

## Run locally

```bash
pip install -r requirements.txt
CENSUS_API_KEY=your_key python scripts/fetch_census.py   # one time, creates data/acs_counties.csv
streamlit run Home.py
```

Deploy on Streamlit Community Cloud with `Home.py` as the main file.
