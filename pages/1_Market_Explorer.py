import altair as alt
import pandas as pd
import streamlit as st

from data import METRICS, get_panel_or_stop, markets_only, us_benchmark
from markets import BENCHMARK_COLOR, GROUP_COLORS, MARKETS, focus_market_picker

st.set_page_config(page_title="Market Explorer", page_icon="🏡", layout="wide")
focus = focus_market_picker()
m = MARKETS[focus]

st.title(f"Market Explorer: {m.short_name}")
st.caption(f"{m.county}, {m.group}. {m.anchor}")

panel = get_panel_or_stop()
market = markets_only(panel).query("fips == @focus").sort_values("year")
us = us_benchmark(panel)
years = [int(y) for y in sorted(market["year"].unique())]

if not years:
    st.info("No Census estimates are available for this market. Pick another focus market in the sidebar.")
    st.stop()

left, right = st.columns([3, 2])
with left:
    if len(years) > 1:
        start, end = st.select_slider("Years", options=years, value=(years[0], years[-1]))
    else:
        start = end = years[0]
with right:
    metric = st.selectbox("Measure", options=list(METRICS), format_func=lambda k: METRICS[k]["label"],
                          help="Choose what the chart shows.")
show_us = st.checkbox("Compare with the U.S. as a whole", value=True,
                      disabled=not METRICS[metric]["benchmark"],
                      help="Available for percentage measures only.")

view = market[(market["year"] >= start) & (market["year"] <= end)].dropna(subset=[metric])
if view.empty:
    st.info("No estimates for this measure in the selected years. Widen the year range or choose another measure.")
    st.stop()

first, last = view.iloc[0], view.iloc[-1]
us_last = us.set_index("year").loc[int(last["year"]), "seasonal_share"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vacation homes", f"{last['seasonal_units']:,.0f}",
          delta=f"{last['seasonal_units'] - first['seasonal_units']:+,.0f} since {int(first['year'])}")
c2.metric("Share of all housing", f"{last['seasonal_share']:.1f}%",
          delta=f"{last['seasonal_share'] - first['seasonal_share']:+.1f} pts since {int(first['year'])}")
c3.metric("U.S. share, same year", f"{us_last:.1f}%",
          help="All vacation homes in the country divided by all housing units.")
c4.metric("Rank among U.S. counties", f"Top {100 - last['share_percentile']:.0f}%",
          help="Where this county's vacation-home share falls among every U.S. county.")

info = METRICS[metric]
chart_df = view[["year", metric]].assign(series=m.short_name)
colors = {m.short_name: GROUP_COLORS[m.group]}
if show_us and info["benchmark"]:
    us_view = us[(us["year"] >= start) & (us["year"] <= end)][["year", metric]].assign(series="United States")
    chart_df = pd.concat([chart_df, us_view])
    colors["United States"] = BENCHMARK_COLOR

trend_tab, table_tab = st.tabs(["Trend", "Table"])
with trend_tab:
    chart = (
        alt.Chart(chart_df)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("year:O", title="5-year estimate ending in"),
            y=alt.Y(f"{metric}:Q", title=info["label"], axis=alt.Axis(format=info["axis"])),
            color=alt.Color("series:N", title=None,
                            scale=alt.Scale(domain=list(colors), range=list(colors.values())),
                            legend=alt.Legend(orient="top")),
            strokeDash=alt.StrokeDash("series:N", legend=None,
                                      scale=alt.Scale(domain=list(colors), range=[[1, 0], [6, 4]][: len(colors)])),
            tooltip=[alt.Tooltip("series:N", title="Market"), alt.Tooltip("year:O", title="Year"),
                     alt.Tooltip(f"{metric}:Q", title=info["label"], format=info["axis"])],
        )
        .properties(height=380, title=f"{info['label']}, {start} to {end}")
    )
    st.altair_chart(chart, width="stretch")
    st.caption(info["help"])
with table_tab:
    table = view[["year", "housing_units", "seasonal_units", "seasonal_share",
                  "median_home_value", "median_household_income", "value_to_income"]]
    st.dataframe(
        table, hide_index=True, width="stretch",
        column_config={
            "year": st.column_config.NumberColumn("Year", format="%d"),
            "housing_units": st.column_config.NumberColumn("Housing units", format="localized"),
            "seasonal_units": st.column_config.NumberColumn("Vacation homes", format="localized"),
            "seasonal_share": st.column_config.NumberColumn("Vacation homes, %", format="%.1f%%"),
            "median_home_value": st.column_config.NumberColumn("Median home value", format="dollar"),
            "median_household_income": st.column_config.NumberColumn("Median income", format="dollar"),
            "value_to_income": st.column_config.NumberColumn("Value to income", format="%.1fx"),
        },
    )

with st.expander("How to read this page"):
    st.write(
        "Each point is a Census 5-year estimate, so the value for 2023 describes 2019 to 2023. "
        "A rising share of vacation homes means more of the county's housing is being held for "
        "visitors or part-time owners rather than for people who live there year-round."
    )
