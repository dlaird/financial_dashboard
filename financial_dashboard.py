# ###########################################################################
# at the command line> python -m streamlit run financial_dashboard.py
# 
# ###########################################################################
import pandas as pd
import plotly.express as px
import streamlit as st
import data_helpers as dh
from ynab_data_pipeline import get_ynab_data
from pandas.tseries.offsets import DateOffset


# -----------------------------------------------------------------------------
# get data
# -----------------------------------------------------------------------------
# use_api toggle
use_api = 0  # Set to False to load from CSV instead

if use_api:
    df = get_ynab_data()
else:
    df = pd.read_csv("ynab_extract.csv")

# -----------------------------------------------------------------------------
# grouping 
# -----------------------------------------------------------------------------
# Summarizing transaction data by summing amounts by:
#   category_supergroup (e.g.,Basic Expenses, Goals, Living Expenses)
#   category_group (e.g., Health Care, Travel, Insurance)
#   category_name (e.g., Dental Care, Summer Vacation, Auto Insurance)
# by both:
#   months
#   year
# -----------------------------------------------------------------------------
# by category super groups
df_sgrp  = dh.group_sum(df,["month_start", "category_supergroup"])
df_sgrpy = dh.group_sum(df,["year", "category_supergroup"])

# by category groups
df_grp = dh.group_sum(df,["month_start", "category_group"])
df_grpy = dh.group_sum(df,["year", "category_group"])

# by category name
df_cat = dh.group_sum(df,["month_start", "category_group", "category_name"])
df_caty = dh.group_sum(df,["year", "category_group", "category_name"])

# -----------------------------------------------------------------------------
# Segmenting and Charting
# -----------------------------------------------------------------------------
# Filtering monthly and yearly summarized data to create data slices at the
# three levels of aggregation to create a chart with
# -----------------------------------------------------------------------------
# Expenses Category Super Groups
# -----------------------------------------------------------------------------
# by month
# -----------------------------------------------------------------------------
df_sgrp_exp = dh.filter_group(df_sgrp,"category_supergroup",values=["Basic Expenses", "Goals", "Living Expenses"])
df_sgrp_exp = dh.sort_and_cast(df_sgrp_exp, "category_supergroup", "month_start", ascending_order=True)
df_sgrp_exp_line = dh.make_chart(df_sgrp_exp, "line", "month_start", "amount", "category_supergroup", "Category Super Groups", force_year_ticks=True)
df_sgrp_exp_bar = dh.make_chart(df_sgrp_exp, "bar", "month_start", "amount", "category_supergroup", "Category Super Groups, Cummulative", force_year_ticks=True)
# -----------------------------------------------------------------------------
# by year
# -----------------------------------------------------------------------------
df_sgrpy_exp = dh.filter_group(df_sgrpy,"category_supergroup",values=["Basic Expenses", "Goals", "Living Expenses"])
df_sgrpy_exp = dh.sort_and_cast(df_sgrpy_exp, "category_supergroup", "year", ascending_order=True)
df_sgrpy_exp_line = dh.make_chart(df_sgrpy_exp, "line", "year", "amount", "category_supergroup", "Category Super Groups", force_year_ticks=True)
df_sgrpy_exp_bar = dh.make_chart(df_sgrpy_exp, "bar", "year", "amount", "category_supergroup", "Category Super Groups, Cummulative", force_year_ticks=True)

# -----------------------------------------------------------------------------
# Supergroup = Basic Expenses
# -----------------------------------------------------------------------------
# All Basic Expenses category groups
# -----------------------------------------------------------------------------
df_grpy_exp = dh.filter_group(df_grpy,"category_group",startswith="Basic Expenses -")
df_grpy_exp = dh.sort_and_cast(df_grpy_exp, "category_group", "year", ascending_order=True)
df_grpy_exp_line = dh.make_chart(df_grpy_exp, "line", "year", "amount", "category_group", "Basic Expenses by Category Group", force_year_ticks=True)
df_grpy_exp_bar  = dh.make_chart(df_grpy_exp, "bar",  "year", "amount", "category_group", "Basic Expenses by Category Group, Cummulative", force_year_ticks=False)

# Categories in Group = Basic Expenses - Rental Home
# -----------------------------------------------------------------------------
df_caty_exp_rh = dh.filter_group(df_caty,"category_group",values=["Basic Expenses - Rental Home"])
df_caty_exp_rh = dh.sort_and_cast(df_caty_exp_rh, "category_name", "year", ascending_order=True)
df_caty_exp_rh_line = dh.make_chart(df_caty_exp_rh, "line", "year", "amount", "category_name", "Basic Expenses - Rental Home Group by Category", force_year_ticks=True)
df_caty_exp_rh_bar  = dh.make_chart(df_caty_exp_rh, "bar",  "year", "amount", "category_name", "Basic Expenses - Rental Home Group by Category, Cummulative", force_year_ticks=False)

# Categories in Group = Basic Expenses - Health Care
# -----------------------------------------------------------------------------
df_caty_exp_hc = dh.filter_group(df_caty,"category_group",values=["Basic Expenses - Health Care"])
df_caty_exp_hc = dh.sort_and_cast(df_caty_exp_hc, "category_name", "year", ascending_order=True)
df_caty_exp_hc_line = dh.make_chart(df_caty_exp_hc, "line", "year", "amount", "category_name", "Basic Expenses - Health Care Group by Category", force_year_ticks=True)
df_caty_exp_hc_bar  = dh.make_chart(df_caty_exp_hc, "bar",  "year", "amount", "category_name", "Basic Expenses - Health Care Group by Category, Cummulative", force_year_ticks=False)

# -----------------------------------------------------------------------------
# Supergroup = Goals
# -----------------------------------------------------------------------------
# All Goal category groups
# -----------------------------------------------------------------------------
df_grpy_gls = dh.filter_group(df_grpy,"category_group",startswith="Goal -")
df_grpy_gls = dh.sort_and_cast(df_grpy_gls, "category_group", "year", ascending_order=True)
df_grpy_gls_line = dh.make_chart(df_grpy_gls, "line", "year", "amount", "category_group", "Goal Expenses by Category Group", force_year_ticks=True)
df_grpy_gls_bar  = dh.make_chart(df_grpy_gls, "bar",  "year", "amount", "category_group", "Goal Expenses by Category Group, Cummulative", force_year_ticks=False)

# Categories in Group = Goals - Travel
# -----------------------------------------------------------------------------
df_caty_gls_trvl = dh.filter_group(df_caty,"category_group",values=["Goal - Travel"])
df_caty_gls_trvl = dh.sort_and_cast(df_caty_gls_trvl, "category_name", "year", ascending_order=True)
df_caty_gls_trvl_line = dh.make_chart(df_caty_gls_trvl, "line", "year", "amount", "category_name", "Goal - Travel Group by Category", force_year_ticks=True)
df_caty_gls_trvl_bar  = dh.make_chart(df_caty_gls_trvl, "area",  "year", "amount", "category_name", "Goal - Travel Group by Category, Cummulative", force_year_ticks=False)

# Categories in Group = Goal - Children (Non-Academic)
# -----------------------------------------------------------------------------
df_caty_gls_cna = dh.filter_group(df_caty,"category_group",values=["Goal - Children (Non-Academic)"])
df_caty_gls_cna = dh.sort_and_cast(df_caty_gls_cna, "category_name", "year", ascending_order=True)
df_caty_gls_cna_line = dh.make_chart(df_caty_gls_cna, "line", "year", "amount", "category_name", "Goal - Children (Non-Academic) Group by Category", force_year_ticks=True)
df_caty_gls_cna_bar  = dh.make_chart(df_caty_gls_cna, "bar",  "year", "amount", "category_name", "Goal - Children (Non-Academic) Group by Category, Cummulative", force_year_ticks=False)


# -----------------------------------------------------------------------------
# Supergroup = Living Expenses
# -----------------------------------------------------------------------------
# All Living Expenses category groups
# -----------------------------------------------------------------------------
df_grp_lvg_exp = dh.filter_group(df_grp,"category_group",startswith="Living Expenses -")
df_grp_lvg_exp = dh.sort_and_cast(df_grp_lvg_exp, "category_group", "month_start", ascending_order=True)
df_grp_lvg_exp_line = dh.make_chart(df_grp_lvg_exp, "line", "month_start", "amount", "category_group", "Lving Expenses Category Groups", force_year_ticks=True)
df_grp_lvg_exp_bar  = dh.make_chart(df_grp_lvg_exp, "bar",  "month_start", "amount", "category_group", "Lving Expenses Category Groups, Cummulative", force_year_ticks=False)

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

# Categories in Group = Living Expenses - Auto/Transport
# -----------------------------------------------------------------------------
df_caty_lvg_exp_at = dh.filter_group(df_caty,"category_group",values=["Living Expenses - Auto/Transport"])
df_caty_lvg_exp_at = dh.sort_and_cast(df_caty_lvg_exp_at, "category_name", "year", ascending_order=True)
df_caty_lvg_exp_at_line = dh.make_chart(df_caty_lvg_exp_at, "line", "year", "amount", "category_name", "Living Expenses - Auto/Transport Group by Category", force_year_ticks=True)
df_caty_lvg_exp_at_bar  = dh.make_chart(df_caty_lvg_exp_at, "bar",  "year", "amount", "category_name", "Living Expenses - Auto/Transport Group by Category, Cummulative", force_year_ticks=False)

# Categories in Group = Living Expenses - Household
# -----------------------------------------------------------------------------
df_cat_lvg_exp_hh = dh.filter_group(df_cat,"category_group",values=["Living Expenses - Household"])
df_cat_lvg_exp_hh = dh.sort_and_cast(df_cat_lvg_exp_hh, "category_name", "month_start", ascending_order=True)
df_cat_lvg_exp_hh_line = dh.make_chart(df_cat_lvg_exp_hh, "line", "month_start", "amount", "category_name", "Living Expenses - Household Group by Category", force_year_ticks=True)
df_cat_lvg_exp_hh_bar  = dh.make_chart(df_cat_lvg_exp_hh, "bar",  "month_start", "amount", "category_name", "Living Expenses - Household Group by Category, Cummulative", force_year_ticks=False)

# Categories in Group = Living Expenses - Insurance
# -----------------------------------------------------------------------------
df_caty_lvg_exp_ins = dh.filter_group(df_caty,"category_group",values=["Living Expenses - Insurance"])
df_caty_lvg_exp_ins = dh.sort_and_cast(df_caty_lvg_exp_ins, "category_name", "year", ascending_order=True)
df_caty_lvg_exp_ins_line = dh.make_chart(df_caty_lvg_exp_ins, "line", "year", "amount", "category_name", "Living Expenses - Insurance Group by Category", force_year_ticks=True)
df_caty_lvg_exp_ins_bar  = dh.make_chart(df_caty_lvg_exp_ins, "bar",  "year", "amount", "category_name", "Living Expenses - Insurance Group by Category, Cummulative", force_year_ticks=False)

# Categories in Group = Living Expenses - Other Discretionary Expenses
# -----------------------------------------------------------------------------
df_cat_lvg_exp_od = dh.filter_group(df_cat,"category_group",values=["Living Expenses - Other Discretionary"])
df_cat_lvg_exp_od = dh.sort_and_cast(df_cat_lvg_exp_od, "category_name", "month_start", ascending_order=True)
df_cat_lvg_exp_od_line = dh.make_chart(df_cat_lvg_exp_od, "line", "month_start", "amount", "category_name", "Living Expenses - Other Discretionary Group by Category", force_year_ticks=True)
df_cat_lvg_exp_od_bar  = dh.make_chart(df_cat_lvg_exp_od, "bar",  "month_start", "amount", "category_name", "Living Expenses - Other Discretionary Group by Category, Cummulative", force_year_ticks=False)

# Categories in Group = Living Expenses - Other Non-Discretionary Expenses
# -----------------------------------------------------------------------------
df_cat_lvg_exp_ond = dh.filter_group(df_cat,"category_group",values=["Living Expenses - Other Non-Discretionary"])
df_cat_lvg_exp_ond = dh.sort_and_cast(df_cat_lvg_exp_ond, "category_name", "month_start", ascending_order=True)
df_cat_lvg_exp_ond_line = dh.make_chart(df_cat_lvg_exp_ond, "line", "month_start", "amount", "category_name", "Living Expenses - Other Non-Discretionary Group by Category", force_year_ticks=True)
df_cat_lvg_exp_ond_bar  = dh.make_chart(df_cat_lvg_exp_ond, "bar",  "month_start", "amount", "category_name", "Living Expenses - Other Non-Discretionary Group by Category, Cummulative", force_year_ticks=False)

# chart_specs = [
#     {
#         "name": "living_expenses_bar",
#         "df": df_grp,
#         "filter": {"startswith": "Living Expenses -"},
#         "group_col": "category_group",
#         "time_col": "month_start",
#         "chart_type": "bar",
#         "title": "Living Expenses Category Groups, Cumulative"
#     },
#     ...
# ]

# charts = {}

# for spec in chart_specs:
#     filtered_df = filter_group(spec["df"], spec["group_col"], startswith=spec["filter"].get("startswith"))
#     sorted_df = dh.sort_and_cast(filtered_df, spec["group_col"], spec["time_col"], ascending_order=True)
#     fig = px.bar(...)  # or px.line(...) depending on spec
#     charts[spec["name"]] = fig

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

