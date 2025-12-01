"""Streamlit application to explore the Casa Genova listings view."""

from __future__ import annotations

import os
from typing import Optional

import duckdb
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATABASE = os.getenv("MOTHERDUCK_DATABASE", "test_cso_g")
ENV_TOKEN = os.getenv("MOTHERDUCK_TOKEN", "")
LISTING_VIEW = "test_cso_g.casa.vw_a_cgenova"
LISTING_COLUMNS = [
    "name",
    "url",
    "description",
    "number_of_rooms",
    "price_value_eur",
    "size_mq",
]


st.set_page_config(page_title="Casa Genova Listing Explorer", layout="wide")


def _normalize_database_name(database: str) -> str:
    database = database.strip()
    if not database:
        raise ValueError("A MotherDuck database name is required.")
    return database if database.startswith("md:") else f"md:{database}"


def _quote_identifier(identifier: str) -> str:
    parts = [p.strip().strip('"') for p in identifier.split(".") if p.strip()]
    if not parts:
        raise ValueError("A table or view name is required.")
    return ".".join(f'"{part}"' for part in parts)


@st.cache_resource(show_spinner=False)
def connect_to_motherduck(database: str, token: Optional[str]) -> duckdb.DuckDBPyConnection:
    db_name = _normalize_database_name(database)
    config: dict[str, str] = {}
    if token:
        config["motherduck_token"] = token

    conn = duckdb.connect(database=db_name, config=config or None)
    conn.execute("INSTALL motherduck")
    conn.execute("LOAD motherduck")
    return conn


@st.cache_data(show_spinner=False)
def fetch_listings(database: str, token: Optional[str]) -> pd.DataFrame:
    conn = connect_to_motherduck(database, token)
    qualified_view = _quote_identifier(LISTING_VIEW)
    query = f"SELECT {', '.join(LISTING_COLUMNS)} FROM {qualified_view}"
    return conn.sql(query).df()


st.title("Casa Genova Listing Explorer")
st.write(
    "This dashboard connects to the `test_cso_g.casa.vw_a_cgenova` view stored in MotherDuck "
    "and surfaces real-estate listings with interactive summaries and filters."
)

# with st.sidebar:
#     st.subheader("Connection")
#     database_input = st.text_input(
#         "MotherDuck database",
#         value=DEFAULT_DATABASE,
#         placeholder="analytics",
#         help='Provide a plain database name (e.g. "analytics") or the full `md:` URI.',
#     )
#     token_input = st.text_input(
#         "MotherDuck token",
#         value=ENV_TOKEN,
#         type="password",
#         placeholder="duckdb_secret_123",
#         help="Generate a MotherDuck token once and paste it here for authenticated access.",
#     )
#     st.caption(
#         "Tokens loaded via the `MOTHERDUCK_TOKEN` environment variable will pre-fill automatically, "
#         "but they are only used in-memory by Streamlit."
#     )

database_input = DEFAULT_DATABASE
# if not database_input.strip():
#     st.error("Please provide a MotherDuck database name in the sidebar to continue.")
#     st.stop()

with st.spinner("Fetching latest listings from MotherDuck..."):
    try:
        listings_df = fetch_listings(database_input, ENV_TOKEN)
    except (duckdb.Error, ValueError) as err:
        st.error(f"Unable to fetch data: {err}")
        st.stop()

if listings_df.empty:
    st.warning("No listings were returned from the Casa Genova view.")
    st.stop()

listings_df = listings_df.assign(
    price_value_eur=pd.to_numeric(listings_df["price_value_eur"], errors="coerce"),
    size_mq=pd.to_numeric(listings_df["size_mq"], errors="coerce"),
    number_of_rooms=pd.to_numeric(listings_df["number_of_rooms"], errors="coerce"),
)
listings_df["price_per_mq"] = listings_df.apply(
    lambda row: row["price_value_eur"] / row["size_mq"] if row["size_mq"] else 0,
    axis=1,
)

total_listings = int(listings_df.shape[0])
avg_price = float(listings_df["price_value_eur"].mean())
avg_price_per_mq = float(listings_df["price_per_mq"].mean())

st.subheader("Market snapshot")
metric_cols = st.columns(3)
metric_cols[0].metric("Listings", f"{total_listings}")
metric_cols[1].metric("Avg price (EUR)", f"€{avg_price:,.0f}")
metric_cols[2].metric("Avg price per m²", f"€{avg_price_per_mq:,.0f}")

st.subheader("Filter listings")
room_options = sorted({int(v) for v in listings_df["number_of_rooms"].dropna().unique()})
selected_rooms = st.multiselect(
    "Number of rooms",
    options=room_options,
    default=room_options,
    help="Filter the dataset to specific room counts.",
)

price_min = int(listings_df["price_value_eur"].min() or 0)
price_max = int(listings_df["price_value_eur"].max() or price_min + 1)
if price_min == price_max:
    price_max = price_min + 1
price_range = st.slider(
    "Price range (EUR)",
    min_value=price_min,
    max_value=price_max,
    value=(price_min, price_max),
    step=max(1000, int((price_max - price_min) / 100) or 1),
)

size_min = float(listings_df["size_mq"].min() or 0.0)
size_max = float(listings_df["size_mq"].max() or size_min + 1.0)
if size_min == size_max:
    size_max = size_min + 1.0
size_range = st.slider(
    "Size range (m²)",
    min_value=float(size_min),
    max_value=float(size_max),
    value=(float(size_min), float(size_max)),
    step=max(1.0, (size_max - size_min) / 50),
)

filtered_df = listings_df.copy()
if selected_rooms:
    filtered_df = filtered_df[filtered_df["number_of_rooms"].isin(selected_rooms)]
filtered_df = filtered_df[
    (filtered_df["price_value_eur"].between(price_range[0], price_range[1]))
    & (filtered_df["size_mq"].between(size_range[0], size_range[1]))
]

st.caption(f"Showing {len(filtered_df)} of {total_listings} listings.")

if filtered_df.empty:
    st.info("No listings match the selected filters. Adjust the sliders or room selection.")
else:
    display_df = filtered_df[
        ["name", "url", "description", "number_of_rooms", "price_value_eur", "size_mq", "price_per_mq"]
    ].rename(
        columns={
            "name": "Name",
            "url": "URL",
            "description": "Description",
            "number_of_rooms": "Rooms",
            "price_value_eur": "Price (EUR)",
            "size_mq": "Size (m²)",
            "price_per_mq": "Price per m² (EUR)",
        }
    )
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "URL": st.column_config.LinkColumn("Listing URL", help="Open the original listing in a new tab"),
            "Price (EUR)": st.column_config.NumberColumn(format="€%d"),
            "Price per m² (EUR)": st.column_config.NumberColumn(format="€%.0f"),
            "Size (m²)": st.column_config.NumberColumn(format="%.0f"),
            "Rooms": st.column_config.NumberColumn(format="%d"),
        },
    )
    csv_payload = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered listings (CSV)",
        data=csv_payload,
        file_name="casa_genova_listings.csv",
        mime="text/csv",
        use_container_width=True,
    )
