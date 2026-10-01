"""Market definitions and the session-state pickers shared by every page."""
from dataclasses import dataclass

import streamlit as st

CENTRAL_FL = "Central Florida"
COMPARISON = "Other tourist markets"
METRO = "Metro benchmark"
GROUPS = [CENTRAL_FL, COMPARISON, METRO]

# Colors pass 3:1 contrast against the page background for chart marks.
GROUP_COLORS = {CENTRAL_FL: "#0B6E69", COMPARISON: "#5E7380", METRO: "#A3622A"}
BENCHMARK_COLOR = "#1C2B33"


@dataclass(frozen=True)
class Market:
    fips: str          # 5-digit state + county FIPS code (Census county ID)
    short_name: str
    county: str
    group: str
    lat: float         # point used for the weather lookup
    lon: float
    anchor: str        # what draws visitors


_MARKET_LIST = [
    Market("12095", "Orlando / International Drive", "Orange County, FL", CENTRAL_FL,
           28.45, -81.47, "Theme parks and the convention center; home to International Drive."),
    Market("12097", "Kissimmee / Four Corners", "Osceola County, FL", CENTRAL_FL,
           28.30, -81.55, "The main cluster of gated vacation-home resorts near Disney."),
    Market("12105", "Davenport", "Polk County, FL", CENTRAL_FL,
           28.16, -81.60, "The Polk side of Four Corners, along I-4 and US-27."),
    Market("47155", "Gatlinburg / Pigeon Forge", "Sevier County, TN", COMPARISON,
           35.79, -83.55, "Great Smoky Mountains and Dollywood; a large cabin-rental market."),
    Market("45051", "Myrtle Beach", "Horry County, SC", COMPARISON,
           33.69, -78.89, "Atlantic beach market with condo and beach-house rentals."),
    Market("01003", "Gulf Shores / Orange Beach", "Baldwin County, AL", COMPARISON,
           30.25, -87.70, "Gulf Coast beach market with a strong summer season."),
    Market("48091", "New Braunfels / Canyon Lake", "Comal County, TX", COMPARISON,
           29.70, -98.12, "Texas Hill Country river and lake tourism between Austin and San Antonio."),
    Market("06065", "Palm Springs / Coachella Valley", "Riverside County, CA", COMPARISON,
           33.83, -116.55, "Desert winter-resort market where cities regulate short-term rentals tightly."),
    Market("48453", "Austin", "Travis County, TX", METRO,
           30.27, -97.74, "Fast-growing Sun Belt metro without a vacation-home economy, used as a control."),
]
MARKETS = {m.fips: m for m in _MARKET_LIST}

DEFAULT_FOCUS = "12097"
DEFAULT_COMPARE = list(MARKETS)


def label(fips: str) -> str:
    return MARKETS[fips].short_name


def init_state() -> None:
    st.session_state.setdefault("focus_market", DEFAULT_FOCUS)
    st.session_state.setdefault("compare_set", DEFAULT_COMPARE.copy())


def _sync_focus() -> None:
    st.session_state.focus_market = st.session_state._focus_widget


def _sync_compare() -> None:
    st.session_state.compare_set = list(st.session_state._compare_widget)


def focus_market_picker() -> str:
    """Sidebar picker for the one market the user is studying.

    The value lives in st.session_state.focus_market, so it carries across pages:
    the Explorer shows it, and Compare and Seasonality highlight it.
    """
    init_state()
    # Widget keys are cleared when a page without the widget runs, so the
    # durable value is copied into the widget before it is drawn.
    st.session_state._focus_widget = st.session_state.focus_market
    st.sidebar.selectbox(
        "Focus market",
        options=list(MARKETS),
        format_func=lambda f: f"{MARKETS[f].short_name} ({MARKETS[f].county})",
        key="_focus_widget",
        on_change=_sync_focus,
    )
    st.sidebar.caption("Your focus market stays selected on every page and is highlighted in comparisons.")
    return st.session_state.focus_market


def compare_set_picker() -> list[str]:
    """Sidebar picker for the comparison set, shared by Compare and Seasonality."""
    init_state()
    st.session_state._compare_widget = st.session_state.compare_set
    st.sidebar.multiselect(
        "Markets to compare",
        options=list(MARKETS),
        format_func=label,
        key="_compare_widget",
        on_change=_sync_compare,
    )
    return st.session_state.compare_set
