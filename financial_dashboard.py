# at the command line> python -m streamlit run financial_dashboard.py

import pandas as pd
import plotly.express as px
import streamlit as st
from data_helpers import sort_and_cast
from ynab_data_pipeline import get_ynab_data
from pandas.tseries.offsets import DateOffset

# Category: Goal - Travel: Travel,  after: 8/1/2024, before:9/1/2024, 

# use_api toggle
use_api = 1  # Set to False to load from CSV instead

if use_api:
    df = get_ynab_data()
else:
    df = pd.read_csv("ynab_extract.csv")

# ###########################################################################
# by category super groups
# ###########################################################################
# group by category_supergroup by month
df_sgrp = (
    df.groupby(["month_start", "category_supergroup"], as_index=False)["amount"]
    .sum()
)

# group by category_supergroup by year
df_sgrpy = (
    df.groupby(["year", "category_supergroup"], as_index=False)["amount"]
    .sum()
)

# ---------------------------------------------------------------------------
# Expenses Category Super Groups
# ---------------------------------------------------------------------------
# filter for category groups
df_sgrp_exp = df_sgrp[
    df_sgrp["category_supergroup"].isin(["Basic Expenses", "Goals", "Living Expenses"])
].copy()

df_sgrpy_exp = df_sgrpy[
    df_sgrpy["category_supergroup"].isin(["Basic Expenses", "Goals", "Living Expenses"])
].copy()

# charts
df_sgrp_exp_line = px.line(
    df_sgrp_exp,
    x="month_start",
    y="amount",
    color="category_supergroup",
    title="Category Super Groups",
)

df_sgrp_exp_bar = px.bar(
    df_sgrp_exp,
    x="month_start",
    y="amount",
    color="category_supergroup",
    title="Category Super Groups, Cummulative",
)

df_sgrpy_exp_line = px.line(
    df_sgrpy_exp,
    x="year",
    y="amount",
    color="category_supergroup",
    title="Category Super Groups",
)

df_sgrpy_exp_bar = px.bar(
    df_sgrpy_exp,
    x="year",
    y="amount",
    color="category_supergroup",
    title="Category Super Groups, Cummulative",
)

# ###########################################################################
# by category groups
# ###########################################################################
# group by category_group by month
df_grp = (
    df.groupby(["month_start", "category_group"], as_index=False)["amount"]
    .sum()
)

# group by category_group by year
df_grpy = (
    df.groupby(["year", "category_group"], as_index=False)["amount"]
    .sum()
)

# ---------------------------------------------------------------------------
# Living Expenses Category Groups
# ---------------------------------------------------------------------------
# filter for Living Expenses category groups
df_grp_lvg_exp = df_grp[
    df_grp["category_group"].str.startswith("Living Expenses -", na=False)
].copy()

df_grp_lvg_exp = sort_and_cast(df_grp_lvg_exp, "category_group", "month_start", ascending_order=True)

# charts
df_grp_lvg_exp_line = px.line(
    df_grp_lvg_exp,
    x="month_start",
    y="amount",
    color="category_group",
    title="Living Expenses Category Groups",
)

df_grp_lvg_exp_bar = px.bar(
    df_grp_lvg_exp,
    x="month_start",
    y="amount",
    color="category_group",
    title="Living Expenses Category Groups, Cummulative",
)

df_grp_lvg_exp_bar.add_hline(
    y=8000,  # Replace with your desired y-axis value
    line_dash="solid",  # Optional: dashed line style
    line_color="black",  # Optional: line color
    annotation_text="Right Capital Target",  # Optional: label
    annotation_position="top left",  # Optional: label position
    annotation_font=dict(
        # family="Arial Black",  # or any bold font family
        size=12,               # adjust size as needed
        color="brown")
)

# ---------------------------------------------------------------------------
# Goals category groups
# ---------------------------------------------------------------------------
# filter for Goals category groups
df_grpy_gls = df_grpy[
    df_grpy["category_group"].str.startswith("Goal -", na=False)
].copy()

df_grpy_gls = sort_and_cast(df_grpy_gls, "category_group", "year", ascending_order=True)

# charts
df_grpy_gls_line = px.line(
    df_grpy_gls,
    x="year",
    y="amount",
    color="category_group",
    title="Goal Expenses by Category Group",
)

df_grpy_gls_bar = px.bar(
    df_grpy_gls,
    x="year",
    y="amount",
    color="category_group",
    title="Goal Expenses by Category Group",
)

df_grpy_gls_line.update_layout(
    xaxis=dict(
        tickmode="linear",
        tick0=df_grpy_gls["year"].min(),
        dtick=1  # One tick per year
    )
)

# ---------------------------------------------------------------------------
# Basic Expenses category groups
# ---------------------------------------------------------------------------
# filter for Goals category groups
df_grpy_exp = df_grpy[
    df_grpy["category_group"].str.startswith("Basic Expenses -", na=False)
].copy()

df_grpy_exp = sort_and_cast(df_grpy_exp, "category_group", "year", ascending_order=True)

# charts
df_grpy_exp_line = px.line(
    df_grpy_exp,
    x="year",
    y="amount",
    color="category_group",
    title="Basic Expenses by Category Group",
)

df_grpy_exp_bar = px.bar(
    df_grpy_exp,
    x="year",
    y="amount",
    color="category_group",
    title="Basic Expenses by Category Group",
)

df_grpy_exp_line.update_layout(
    xaxis=dict(
        tickmode="linear",
        tick0=df_grpy_gls["year"].min(),
        dtick=1  # One tick per year
    )
)
# ###########################################################################
# by category name
# ###########################################################################
# group by category_group and category_name
df_cat = (
    df.groupby(["month_start", "category_group", "category_name"], as_index=False)[
        "amount"
    ]
    .sum()
)

df_caty = (
    df.groupby(["year", "category_group", "category_name"], as_index=False)[
        "amount"
    ]
    .sum()
)

# ---------------------------------------------------------------------------
# Categories in Group = Living Expenses - Household
# ---------------------------------------------------------------------------
# filter for Household category group
df_cat_lvg_exp_hh = df_cat[
    df_cat["category_group"] == "Living Expenses - Household"
].copy()

df_cat_lvg_exp_hh = sort_and_cast(df_cat_lvg_exp_hh, "category_name", "month_start", ascending_order=True)

# charts
df_cat_lvg_exp_hh_line = px.line(
    df_cat_lvg_exp_hh,
    x="month_start",
    y="amount",
    color="category_name",
    title="Household Expenses Group by Category",
)

df_cat_lvg_exp_hh_bar = px.bar(
    df_cat_lvg_exp_hh,
    x="month_start",
    y="amount",
    color="category_name",
    title="Household Expenses Group by Category, Cummulative",
)

# ---------------------------------------------------------------------------
# Categories in Group = Living Expenses - Other Discretionary Expenses
# ---------------------------------------------------------------------------
# filter for Other Discretionary category group
df_cat_lvg_exp_od = df_cat[
    df_cat["category_group"] == "Living Expenses - Other Discretionary"
].copy()

df_cat_lvg_exp_od = sort_and_cast(df_cat_lvg_exp_od, "category_name", "month_start", ascending_order=True)

# charts
df_cat_lvg_exp_od_line = px.line(
    df_cat_lvg_exp_od,
    x="month_start",
    y="amount",
    color="category_name",
    title="Other Discretionary Expenses Group by Category",
)

df_cat_lvg_exp_od_bar = px.bar(
    df_cat_lvg_exp_od,
    x="month_start",
    y="amount",
    color="category_name",
    title="Other Discretionary Expenses Group by Category, Cummulative",
)

# ---------------------------------------------------------------------------
# Categories in Group = Living Expenses - Other Non-Discretionary Expenses
# ---------------------------------------------------------------------------
# filter for Other Discretionary category group
df_cat_lvg_exp_ond = df_cat[
    df_cat["category_group"] == "Living Expenses - Other Non-Discretionary"
].copy()

df_cat_lvg_exp_ond = sort_and_cast(df_cat_lvg_exp_ond, "category_name", "month_start", ascending_order=True)

# charts
df_cat_lvg_exp_ond_line = px.line(
    df_cat_lvg_exp_ond,
    x="month_start",
    y="amount",
    color="category_name",
    title="Other Non-Discretionary Expenses Group by Category",
)

df_cat_lvg_exp_ond_bar = px.bar(
    df_cat_lvg_exp_ond,
    x="month_start",
    y="amount",
    color="category_name",
    title="Other Non-Discretionary Expenses Group by Category, Cummulative",
)

# ---------------------------------------------------------------------------
# Categories in Group = Living Expenses - Insurance
# ---------------------------------------------------------------------------
# filter for Other Discretionary category group
df_caty_lvg_exp_ins = df_caty[
    df_caty["category_group"] == "Living Expenses - Insurance"
].copy()

df_caty_lvg_exp_ins = sort_and_cast(df_caty_lvg_exp_ins, "category_name", "year", ascending_order=True)

# charts
df_caty_lvg_exp_ins_line = px.line(
    df_caty_lvg_exp_ins,
    x="year",
    y="amount",
    color="category_name",
    title="Insurance Expenses Group by Category",
)

df_caty_lvg_exp_ins_bar = px.bar(
    df_caty_lvg_exp_ins,
    x="year",
    y="amount",
    color="category_name",
    title="Insurance Expenses Group by Category, Cummulative",
)

# ---------------------------------------------------------------------------
# Categories in Group = Living Expenses - Auto/Transport
# ---------------------------------------------------------------------------
# filter for Auto/Transport category group
df_caty_lvg_exp_at = df_caty[
    df_caty["category_group"] == "Living Expenses - Auto/Transport"
].copy()

df_caty_lvg_exp_at = sort_and_cast(df_caty_lvg_exp_at, "category_name", "year", ascending_order=True)

# charts
df_caty_lvg_exp_at_line = px.line(
    df_caty_lvg_exp_at,
    x="year",
    y="amount",
    color="category_name",
    title="Auto/Transport Expenses Group by Category",
)

df_caty_lvg_exp_at_bar = px.bar(
    df_caty_lvg_exp_at,
    x="year",
    y="amount",
    color="category_name",
    title="Auto/Transport Expenses Group by Category, Cummulative",
)

# ---------------------------------------------------------------------------
# Categories in Group = Goals - Travel
# ---------------------------------------------------------------------------
# filter for Travel category group
df_caty_gls_trvl = df_caty[
    df_caty["category_group"] == "Goal - Travel"
].copy()

df_caty_gls_trvl = sort_and_cast(df_caty_gls_trvl, "category_name", "year", ascending_order=True)

# charts
df_caty_gls_trvl_line = px.line(
    df_caty_gls_trvl,
    x="year",
    y="amount",
    color="category_name",
    title="Travel Group by Category",
)

df_caty_gls_trvl_line.update_layout(
    xaxis=dict(
        tickmode="linear",
        tick0=df_grpy_gls["year"].min(),
        dtick=1  # One tick per year
    )
)

df_caty_gls_trvl_bar = px.area(
    df_caty_gls_trvl,
    x="year",
    y="amount",
    color="category_name",
    title="Travel Group by Category, Cummulative",
)

df_caty_gls_trvl_bar.add_hline(
    y=20000,  # Replace with your desired y-axis value
    line_dash="solid",  # Optional: dashed line style
    line_color="black",  # Optional: line color
    annotation_text="Right Capital Target",  # Optional: label
    annotation_position="top left",  # Optional: label position
    annotation_font=dict(
        # family="Arial Black",  # or any bold font family
        size=12,               # adjust size as needed
        color="brown")
)

# ---------------------------------------------------------------------------
# Categories in Group = Goal - Children (Non-Academic)
# ---------------------------------------------------------------------------
# filter for Travel category group
df_caty_gls_cna = df_caty[
    df_caty["category_group"] == "Goal - Children (Non-Academic)"
].copy()

df_caty_gls_cna = sort_and_cast(df_caty_gls_cna, "category_name", "year", ascending_order=True)

# charts
df_caty_gls_cna_line = px.line(
    df_caty_gls_cna,
    x="year",
    y="amount",
    color="category_name",
    title="Children (Non-Academic) Group by Category",
)

df_caty_gls_cna_line.update_layout(
    xaxis=dict(
        tickmode="linear",
        tick0=df_grpy_gls["year"].min(),
        dtick=1  # One tick per year
    )
)

df_caty_gls_cna_bar = px.bar(
    df_caty_gls_cna,
    x="year",
    y="amount",
    color="category_name",
    title="Children (Non-Academic) Group by Category, Cummulative",
)

# ---------------------------------------------------------------------------
# Categories in Group = Basic Expenses - Rental Home
# ---------------------------------------------------------------------------
# filter for Travel category group
df_caty_exp_rh = df_caty[
    df_caty["category_group"] == "Basic Expenses - Rental Home"
].copy()

df_caty_exp_rh = sort_and_cast(df_caty_exp_rh, "category_name", "year", ascending_order=True)

# charts
df_caty_exp_rh_line = px.line(
    df_caty_exp_rh,
    x="year",
    y="amount",
    color="category_name",
    title="Basic Expenses - Rental Home Group by Category",
)

df_caty_exp_rh_line.update_layout(
    xaxis=dict(
        tickmode="linear",
        tick0=df_grpy_gls["year"].min(),
        dtick=1  # One tick per year
    )
)

df_caty_exp_rh_bar = px.bar(
    df_caty_exp_rh,
    x="year",
    y="amount",
    color="category_name",
    title="Basic Expenses - Rental Home Group by Category, Cummulative",
)

# ---------------------------------------------------------------------------
# Categories in Group = Basic Expenses - Health Care
# ---------------------------------------------------------------------------
# filter for Travel category group
df_caty_exp_hc = df_caty[
    df_caty["category_group"] == "Basic Expenses - Health Care"
].copy()

df_caty_exp_hc = sort_and_cast(df_caty_exp_hc, "category_name", "year", ascending_order=True)

# charts
df_caty_exp_hc_line = px.line(
    df_caty_exp_hc,
    x="year",
    y="amount",
    color="category_name",
    title="Basic Expenses - Health Care Group by Category",
)

df_caty_exp_hc_line.update_layout(
    xaxis=dict(
        tickmode="linear",
        tick0=df_grpy_gls["year"].min(),
        dtick=1  # One tick per year
    )
)

df_caty_exp_hc_bar = px.bar(
    df_caty_exp_hc,
    x="year",
    y="amount",
    color="category_name",
    title="Basic Expenses - Health Care Group by Category, Cummulative",
)

# # Set latest_month to last complete month
# df['latest_month'] = df['month_start'].max() - DateOffset(months=1)

# ###########################################################################
# dashboard
# ###########################################################################

with st.container():
    st.title("Spending Dashboard")
#    st.write("This is some content inside the container.")
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.set_page_config(layout="wide")

st.header("Expense Category Super Groups")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_sgrpy_exp_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_sgrpy_exp_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.header("Expense Category Super Groups")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_sgrp_exp_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_sgrp_exp_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.header("Living Expenses Category Groups")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_grp_lvg_exp_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_grp_lvg_exp_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.subheader("Household Expenses Category Group")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_cat_lvg_exp_hh_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_cat_lvg_exp_hh_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.subheader("Other Discretionary Expenses Category Group")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_cat_lvg_exp_od_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_cat_lvg_exp_od_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.subheader("Other Non-Discretionary Expenses Category Group")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_cat_lvg_exp_ond_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_cat_lvg_exp_ond_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.subheader("Insurance Expenses Category Group")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_caty_lvg_exp_ins_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_caty_lvg_exp_ins_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.subheader("Auto/Transport Expenses Category Group")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_caty_lvg_exp_at_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_caty_lvg_exp_at_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.header("Goals Category Groups")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_grpy_gls_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_grpy_gls_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.subheader("Travel Goal Category Group")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_caty_gls_trvl_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_caty_gls_trvl_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.subheader("Children - Non Academic Goal Category Group")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_caty_gls_cna_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_caty_gls_cna_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.header("Basic Expenses Category Groups")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_grpy_exp_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_grpy_exp_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.subheader("Basic Expenses - Rental Home Category Group")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_caty_exp_rh_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_caty_exp_rh_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

st.subheader("Basic Expenses - Health Care Category Group")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(df_caty_exp_hc_line, use_container_width=True)
    with col2:
        st.plotly_chart(df_caty_exp_hc_bar, use_container_width=True)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

