import altair as alt
import streamlit as st

from data import MONTHS, WEATHER_END, WEATHER_START, monthly_climate
from markets import BENCHMARK_COLOR, GROUP_COLORS, MARKETS, compare_set_picker, focus_market_picker

st.set_page_config(page_title="Seasonality", page_icon="🏡", layout="wide")
focus = focus_market_picker()
compare = compare_set_picker()

st.title("Seasonality")
st.write(
    "A vacation home only earns money while visitors come. This page counts how many months of "
    "warm weather each market gets, a demand condition the housing data can't show."
)

c1, c2 = st.columns([3, 2])
threshold = c1.slider("Warm month means an average daily high of at least (°F)", 65, 90, 75,
                      help="Raise it for beach and pool weather, lower it for mild sightseeing weather.")
measure = c2.radio("Chart shows", ["Average daily high", "Monthly rainfall"], horizontal=True)

if not compare:
    st.info("Pick at least one market in the sidebar to see its weather.")
    st.stop()

with st.spinner("Loading ten years of daily weather."):
    climate, failed = monthly_climate(compare)
if failed:
    st.warning(f"Weather couldn't be loaded for: {', '.join(failed)}. Refresh to try again.")
if climate.empty:
    st.info("No weather data is available for the selected markets right now.")
    st.stop()

warm = (
    climate.assign(is_warm=climate["avg_high_f"] >= threshold)
    .groupby(["fips", "market", "group"], as_index=False)["is_warm"].sum()
    .rename(columns={"is_warm": "warm_months"})
    .sort_values("warm_months", ascending=False)
)
warm["label"] = warm.apply(lambda r: f"{r['market']} (focus)" if r["fips"] == focus else r["market"], axis=1)

if focus in warm["fips"].values:
    f_row = warm.set_index("fips").loc[focus]
    others = warm[warm["fips"] != focus]["warm_months"]
    coolest = climate[climate["fips"] == focus]["avg_high_f"].min()
    a, b, c = st.columns(3)
    a.metric(f"Warm months in {MARKETS[focus].short_name}", f"{int(f_row['warm_months'])} of 12")
    if not others.empty:
        b.metric("Typical for the other markets shown", f"{others.median():.0f} of 12",
                 help="Median across the other selected markets.")
    c.metric("Coolest month's average high", f"{coolest:.0f}°F")
else:
    st.caption(f"Your focus market, {MARKETS[focus].short_name}, isn't selected. Add it in the sidebar to compare it.")

season_tab, count_tab, heat_tab = st.tabs(["Year at a glance", "Warm months", "Heat map"])

with season_tab:
    field, title, fmt = (("avg_high_f", "Average daily high (°F)", ".0f") if measure == "Average daily high"
                         else ("avg_rain_in", "Average monthly rainfall (in)", ".1f"))
    lines = alt.Chart(climate).mark_line(point=True).encode(
        x=alt.X("month_name:N", sort=MONTHS, title=None),
        y=alt.Y(f"{field}:Q", title=title, scale=alt.Scale(zero=False)),
        color=alt.Color("market:N", title="Market"),
        strokeWidth=alt.condition(alt.datum.fips == focus, alt.value(4), alt.value(1.5)),
        tooltip=[alt.Tooltip("market:N", title="Market"), alt.Tooltip("month_name:N", title="Month"),
                 alt.Tooltip(f"{field}:Q", title=title, format=fmt)],
    )
    layers = lines
    if measure == "Average daily high":
        layers = lines + alt.Chart().mark_rule(color=BENCHMARK_COLOR, strokeDash=[6, 4]).encode(
            y=alt.datum(threshold))
        st.caption(f"Dashed line: your warm-month threshold of {threshold}°F. The focus market is drawn thicker.")
    st.altair_chart(layers.properties(height=400, title=f"{title}, {WEATHER_START[:4]} to {WEATHER_END[:4]} average"),
                    width="stretch")

with count_tab:
    bars = alt.Chart(warm).mark_bar(stroke=BENCHMARK_COLOR).encode(
        y=alt.Y("label:N", sort=None, title=None),
        x=alt.X("warm_months:Q", title=f"Months averaging {threshold}°F or warmer",
                scale=alt.Scale(domain=[0, 12])),
        color=alt.Color("group:N", title="Group",
                        scale=alt.Scale(domain=list(GROUP_COLORS), range=list(GROUP_COLORS.values())),
                        legend=alt.Legend(orient="top")),
        strokeWidth=alt.condition(alt.datum.fips == focus, alt.value(2.5), alt.value(0)),
        tooltip=[alt.Tooltip("market:N", title="Market"), alt.Tooltip("warm_months:Q", title="Warm months")],
    )
    text = alt.Chart(warm).mark_text(align="left", dx=4, color=BENCHMARK_COLOR).encode(
        y=alt.Y("label:N", sort=None), x="warm_months:Q", text="warm_months:Q")
    st.altair_chart((bars + text).properties(height=max(220, 44 * len(warm))), width="stretch")

with heat_tab:
    heat = alt.Chart(climate).mark_rect().encode(
        x=alt.X("month_name:N", sort=MONTHS, title=None),
        y=alt.Y("market:N", sort=warm["market"].tolist(), title=None),
        color=alt.Color("avg_high_f:Q", title="Avg high (°F)", scale=alt.Scale(scheme="blueorange")),
        tooltip=[alt.Tooltip("market:N", title="Market"), alt.Tooltip("month_name:N", title="Month"),
                 alt.Tooltip("avg_high_f:Q", title="Average high (°F)", format=".0f")],
    )
    labels = alt.Chart(climate).mark_text(fontSize=11).encode(
        x=alt.X("month_name:N", sort=MONTHS), y=alt.Y("market:N", sort=warm["market"].tolist()),
        text=alt.Text("avg_high_f:Q", format=".0f"),
        color=alt.condition((alt.datum.avg_high_f > 88) | (alt.datum.avg_high_f < 50),
                            alt.value("white"), alt.value("black")),
    )
    st.altair_chart((heat + labels).properties(height=40 * climate["market"].nunique()),
                    width="stretch")
    st.caption("Each cell shows the ten-year average daily high for that month, so the numbers are readable without relying on color.")

with st.expander("About this data"):
    st.write(
        "Daily highs and rainfall come from the Open-Meteo historical weather API for one point in each "
        f"market, {WEATHER_START[:4]} to {WEATHER_END[:4]}. Monthly values are ten-year averages."
    )
