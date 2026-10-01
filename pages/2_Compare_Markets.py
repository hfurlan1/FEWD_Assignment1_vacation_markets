import altair as alt
import pandas as pd
import streamlit as st

from data import METRICS, get_panel_or_stop, markets_only, us_benchmark
from markets import BENCHMARK_COLOR, GROUP_COLORS, GROUPS, MARKETS, compare_set_picker, focus_market_picker

st.set_page_config(page_title="Compare Markets", page_icon="🏡", layout="wide")
focus = focus_market_picker()
compare = compare_set_picker()

st.title("Compare Markets")
st.write("See where Central Florida ranks against other U.S. tourist markets in a single year.")

panel = get_panel_or_stop()
mp = markets_only(panel)
years = sorted((int(y) for y in mp["year"].unique()), reverse=True)

c1, c2, c3 = st.columns([1, 2, 2])
year = c1.selectbox("Year", years)
metric = c2.selectbox("Measure", list(METRICS), format_func=lambda k: METRICS[k]["label"])
group = c3.radio("Market group", ["All groups"] + GROUPS, horizontal=True)
highest_first = st.toggle("Highest first", value=True)

view = mp[(mp["year"] == year) & (mp["fips"].isin(compare))]
if group != "All groups":
    view = view[view["group"] == group]
view = view.dropna(subset=[metric])

if view.empty:
    st.info(
        "No markets match these filters. Add markets in the sidebar, or switch the market group to "
        "'All groups'."
    )
    st.stop()

info = METRICS[metric]
view = view.sort_values(metric, ascending=not highest_first)
view["label"] = view.apply(lambda r: f"{r['market']} (focus)" if r["fips"] == focus else r["market"], axis=1)

if focus not in view["fips"].values:
    st.caption(f"Your focus market, {MARKETS[focus].short_name}, isn't in this view. Add it in the sidebar to see where it ranks.")
else:
    rank = view["fips"].tolist().index(focus) + 1
    st.metric(f"{MARKETS[focus].short_name} ranks", f"{rank} of {len(view)}",
              help=f"Rank on '{info['label']}' among the markets shown, ordered as sorted.")

rank_tab, group_tab, table_tab = st.tabs(["Market ranking", "Group totals", "Table"])

with rank_tab:
    base = alt.Chart(view).encode(
        y=alt.Y("label:N", sort=None, title=None),
        x=alt.X(f"{metric}:Q", title=info["label"], axis=alt.Axis(format=info["axis"])),
    )
    bars = base.mark_bar(stroke=BENCHMARK_COLOR).encode(
        color=alt.Color("group:N", title="Group",
                        scale=alt.Scale(domain=list(GROUP_COLORS), range=list(GROUP_COLORS.values())),
                        legend=alt.Legend(orient="top")),
        strokeWidth=alt.condition(alt.datum.fips == focus, alt.value(2.5), alt.value(0)),
        tooltip=[alt.Tooltip("market:N", title="Market"), alt.Tooltip("group:N", title="Group"),
                 alt.Tooltip(f"{metric}:Q", title=info["label"], format=info["axis"])],
    )
    labels = base.mark_text(align="left", dx=4, color=BENCHMARK_COLOR).encode(
        text=alt.Text(f"{metric}:Q", format=info["axis"])
    )
    layers = bars + labels
    if info["benchmark"]:
        us_value = us_benchmark(panel).set_index("year").loc[year, metric]
        rule = alt.Chart(pd.DataFrame({"v": [us_value]})).mark_rule(
            color=BENCHMARK_COLOR, strokeDash=[6, 4], strokeWidth=2).encode(x="v:Q")
        layers = layers + rule
        st.caption(f"Dashed line: United States as a whole ({info['fmt'].format(us_value)}).")
    st.altair_chart(layers.properties(height=max(220, 44 * len(view)), title=f"{info['label']}, {year}"),
                    width="stretch")
    st.caption(info["help"])

with group_tab:
    totals = (
        view.groupby("group")[["seasonal_units", "housing_units"]].sum().reset_index()
        .assign(seasonal_share=lambda d: d["seasonal_units"] / d["housing_units"] * 100)
    )
    us_row = us_benchmark(panel).query("year == @year")[["seasonal_units", "housing_units", "seasonal_share"]]
    totals = pd.concat([totals, us_row.assign(group="United States")], ignore_index=True)
    st.write(
        "Vacation homes as a share of all housing, adding up every selected county in each group. "
        "This treats each group as one combined market."
    )
    colors = {**GROUP_COLORS, "United States": BENCHMARK_COLOR}
    group_chart = (
        alt.Chart(totals).mark_bar()
        .encode(
            y=alt.Y("group:N", sort="-x", title=None),
            x=alt.X("seasonal_share:Q", title="Vacation homes, % of all housing", axis=alt.Axis(format=".1f")),
            color=alt.Color("group:N", legend=None,
                            scale=alt.Scale(domain=list(colors), range=list(colors.values()))),
            tooltip=[alt.Tooltip("group:N", title="Group"),
                     alt.Tooltip("seasonal_units:Q", title="Vacation homes", format=","),
                     alt.Tooltip("seasonal_share:Q", title="Share, %", format=".1f")],
        )
        .properties(height=60 * len(totals), title=f"Combined vacation-home share by group, {year}")
    )
    st.altair_chart(group_chart, width="stretch")

with table_tab:
    st.dataframe(
        view[["market", "group", "housing_units", "seasonal_units", "seasonal_share",
              "median_home_value", "value_to_income"]],
        hide_index=True, width="stretch",
        column_config={
            "market": "Market", "group": "Group",
            "housing_units": st.column_config.NumberColumn("Housing units", format="localized"),
            "seasonal_units": st.column_config.NumberColumn("Vacation homes", format="localized"),
            "seasonal_share": st.column_config.NumberColumn("Vacation homes, %", format="%.1f%%"),
            "median_home_value": st.column_config.NumberColumn("Median home value", format="dollar"),
            "value_to_income": st.column_config.NumberColumn("Value to income", format="%.1fx"),
        },
    )
