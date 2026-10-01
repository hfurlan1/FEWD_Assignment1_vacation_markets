import pandas as pd
import streamlit as st

from data import DataUnavailable, load_acs_panel, markets_only, us_benchmark
from markets import MARKETS, focus_market_picker

st.set_page_config(page_title="Vacation Home Markets", page_icon="🏡", layout="wide")
focus = focus_market_picker()

st.title("Is Central Florida's vacation-home model one of a kind?")
st.write(
    "Around Orlando, thousands of detached homes are built inside gated, amenity-rich resorts "
    "and rented to tourists by the night. This app compares Central Florida with other U.S. "
    "tourist markets to see whether the conditions behind that model show up anywhere else."
)

st.header("Problem statement")
who, problem, why = st.columns(3)
with who:
    st.subheader("Who it's for")
    st.write(
        "Real estate investors, developers, and researchers deciding whether the Central Florida "
        "vacation-home resort model could work in another U.S. tourist market."
    )
with problem:
    st.subheader("The problem")
    st.write(
        "The evidence for comparing markets (how much housing is already used as vacation homes, "
        "what homes cost against local incomes, and how long the tourist season lasts) is spread "
        "across Census tables and weather records that are hard to line up side by side."
    )
with why:
    st.subheader("Why it matters")
    st.write(
        "These resorts are built at scale, with hundreds of homes and shared amenities financed up "
        "front. Choosing a market without the right demand conditions is an expensive mistake."
    )

st.header("How the app is organized")
st.write("Each page answers one question, moving from depth to breadth to explanation.")
st.markdown(
    "- **Market Explorer**: what does one market's vacation-home stock look like, and is it growing?\n"
    "- **Compare Markets**: where does Central Florida rank against other tourist markets in a given year?\n"
    "- **Seasonality**: how many months of warm weather does each market get, a demand condition "
    "housing data can't show?"
)

st.header(f"Snapshot: {MARKETS[focus].short_name}")
st.caption("Change the focus market in the sidebar. It carries over to every page.")
try:
    panel = load_acs_panel()
except DataUnavailable:
    st.warning("The Census housing data file is missing, so the snapshot is unavailable. The Seasonality page still works.")
else:
    latest = int(panel["year"].max())
    row = markets_only(panel).query("fips == @focus and year == @latest")
    us_share = us_benchmark(panel).set_index("year").loc[latest, "seasonal_share"]
    if row.empty or pd.isna(row["seasonal_share"].iloc[0]):
        st.info(f"No Census estimate is available for this market in {latest}. Try another focus market.")
    else:
        r = row.iloc[0]
        a, b, c = st.columns(3)
        a.metric("Vacation homes", f"{r['seasonal_units']:,.0f}")
        b.metric("Share of all housing", f"{r['seasonal_share']:.1f}%",
                 delta=f"{r['seasonal_share'] - us_share:+.1f} pts vs. U.S.", delta_color="off")
        c.metric("Rank among U.S. counties", f"Top {100 - r['share_percentile']:.0f}%",
                 help="Share of vacation homes compared with every county in the country.")
        st.caption(f"Census American Community Survey, 5-year estimates ending in {latest}.")

with st.expander("About the data and its limits"):
    st.markdown(
        "- **Housing data** comes from the U.S. Census Bureau's American Community Survey "
        "(5-year estimates, county level), saved as a file with the app. A 'vacation home' here is a "
        "unit the Census classifies as held for seasonal, recreational, or occasional use.\n"
        "- **Weather data** comes live from the Open-Meteo historical weather API, 2016 to 2025.\n"
        "- Vacation homes are not the same as short-term rentals. Some are owner-used second homes, "
        "and some rentals are counted elsewhere.\n"
        "- Numbers are for whole counties, so large counties like Orange and Riverside dilute the "
        "resort areas inside them.\n"
        "- Each 5-year estimate overlaps the one before it, so year-to-year changes are smoothed."
    )

with st.expander("Markets in this app"):
    st.dataframe(
        pd.DataFrame(
            [{"Market": m.short_name, "County": m.county, "Group": m.group, "What draws visitors": m.anchor}
             for m in MARKETS.values()]
        ),
        hide_index=True, width="stretch",
    )
