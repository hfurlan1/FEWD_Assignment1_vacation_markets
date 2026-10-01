"""Data loading: a Census CSV snapshot plus the live, no-key Open-Meteo API, both cached."""
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from markets import MARKETS

# ---------------------------------------------------------------- Census ACS
# Census data is a saved snapshot (the Census API now requires a key).
# Rebuild it with scripts/fetch_census.py.
ACS_CSV = Path(__file__).resolve().parent / "data" / "acs_counties.csv"
ACS_VARS = {
    "B25001_001E": "housing_units",            # total housing units
    "B25004_001E": "vacant_units",             # total vacant units
    "B25004_006E": "seasonal_units",           # vacant: seasonal, recreational, or occasional use
    "B25077_001E": "median_home_value",        # median value, owner-occupied units
    "B19013_001E": "median_household_income",  # median household income
}

METRICS = {
    "seasonal_share": {
        "label": "Vacation homes, % of all housing", "fmt": "{:.1f}%", "axis": ".1f", "benchmark": True,
        "help": "Homes held for seasonal, recreational, or occasional use, divided by all housing units.",
    },
    "seasonal_units": {
        "label": "Vacation homes (count)", "fmt": "{:,.0f}", "axis": ",.0f", "benchmark": False,
        "help": "Homes held for seasonal, recreational, or occasional use.",
    },
    "seasonal_of_vacant": {
        "label": "Vacation homes, % of vacant housing", "fmt": "{:.1f}%", "axis": ".1f", "benchmark": True,
        "help": "How much of the empty-on-survey-day housing is empty because it is a vacation home.",
    },
    "median_home_value": {
        "label": "Median home value", "fmt": "${:,.0f}", "axis": "$,.0f", "benchmark": False,
        "help": "Median value of owner-occupied homes.",
    },
    "value_to_income": {
        "label": "Home value to income ratio", "fmt": "{:.1f}x", "axis": ".1f", "benchmark": False,
        "help": "Median home value divided by median household income. Higher means less affordable for locals.",
    },
}


class DataUnavailable(Exception):
    pass


@st.cache_data(show_spinner=False)
def load_acs_panel() -> pd.DataFrame:
    if not ACS_CSV.exists():
        raise DataUnavailable(f"{ACS_CSV.name} not found")
    df = pd.read_csv(ACS_CSV, dtype={"state": str, "county": str}).rename(columns=ACS_VARS)
    for col in ACS_VARS.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].where(df[col] >= 0)  # Census uses large negative codes for "no estimate"
    df["fips"] = df["state"].str.zfill(2) + df["county"].str.zfill(3)
    df = df[df["state"] != "72"]  # 50 states + DC only
    df["seasonal_share"] = df["seasonal_units"] / df["housing_units"] * 100
    df["seasonal_of_vacant"] = df["seasonal_units"] / df["vacant_units"] * 100
    df["value_to_income"] = df["median_home_value"] / df["median_household_income"]
    df["share_percentile"] = df.groupby("year")["seasonal_share"].rank(pct=True) * 100
    return df


def get_panel_or_stop() -> pd.DataFrame:
    """Load the Census data for a page, or explain what's missing and stop the page."""
    try:
        return load_acs_panel()
    except DataUnavailable:
        st.error(
            "The Census housing data file is missing, so this page can't load. "
            "Run scripts/fetch_census.py to create data/acs_counties.csv."
        )
        st.stop()


def markets_only(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel[panel["fips"].isin(MARKETS)].copy()
    df["market"] = df["fips"].map(lambda f: MARKETS[f].short_name)
    df["group"] = df["fips"].map(lambda f: MARKETS[f].group)
    return df


def us_benchmark(panel: pd.DataFrame) -> pd.DataFrame:
    """National totals built by summing every county, so shares are true U.S. shares."""
    us = panel.groupby("year")[["housing_units", "vacant_units", "seasonal_units"]].sum().reset_index()
    us["seasonal_share"] = us["seasonal_units"] / us["housing_units"] * 100
    us["seasonal_of_vacant"] = us["seasonal_units"] / us["vacant_units"] * 100
    return us


# ---------------------------------------------------------------- Open-Meteo
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
WEATHER_START, WEATHER_END = "2016-01-01", "2025-12-31"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
def fetch_daily_weather(lat: float, lon: float) -> pd.DataFrame:
    resp = requests.get(
        WEATHER_URL,
        params={
            "latitude": lat, "longitude": lon,
            "start_date": WEATHER_START, "end_date": WEATHER_END,
            "daily": "temperature_2m_max,precipitation_sum",
            "temperature_unit": "fahrenheit", "precipitation_unit": "inch",
            "timezone": "auto",
        },
        timeout=30,
    )
    resp.raise_for_status()
    df = pd.DataFrame(resp.json()["daily"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def monthly_climate(fips_list: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Ten-year monthly normals per market: average daily high and average monthly rainfall."""
    frames, failed = [], []
    for fips in fips_list:
        m = MARKETS[fips]
        try:
            daily = fetch_daily_weather(m.lat, m.lon)
        except (requests.RequestException, ValueError, KeyError):
            failed.append(m.short_name)
            continue
        daily["year"] = daily["time"].dt.year
        daily["month"] = daily["time"].dt.month
        highs = daily.groupby("month")["temperature_2m_max"].mean()
        rain = daily.groupby(["year", "month"])["precipitation_sum"].sum().groupby("month").mean()
        out = pd.DataFrame({"avg_high_f": highs, "avg_rain_in": rain}).reset_index()
        out["month_name"] = out["month"].map(lambda i: MONTHS[i - 1])
        out["fips"], out["market"], out["group"] = fips, m.short_name, m.group
        frames.append(out)
    if not frames:
        return pd.DataFrame(), failed
    return pd.concat(frames, ignore_index=True), failed
