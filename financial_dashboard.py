### run at the command line> 
#### python -m streamlit run financial_dashboard.py
#### python -m streamlit run financial_dashboard.py -- --refresh-data

### dev
### - look at transactions with null category supergroup
###   remove anything where transaction begins "Transfer:"
###   chart monthly/yearly total by payee over time
###
### - organize dashboard

import argparse
import pandas as pd
import plotly.express as px
import streamlit as st
import socket
from datetime import datetime, timedelta
from pandas.tseries.offsets import DateOffset
# user packages
import data_helpers as dh
from data_helpers import ALERT_THRESHOLD
from ynab_data_pipeline import get_ynab_data
from config_charts import chart_specs
# from config_charts_dev import chart_specs

### get data
### refresh_data toggle — pass --refresh-data at the command line to fetch from YNAB
_parser = argparse.ArgumentParser()
_parser.add_argument("--refresh-data", action="store_true", default=False)
_args, _ = _parser.parse_known_args()
refresh_data = _args.refresh_data

if refresh_data:
    df = get_ynab_data()
else:
    df = pd.read_csv("ynab_extract.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

### grouping 
### summarizing transaction data by summing amounts by:
###   category_supergroup (e.g.,Basic Expenses, Goals, Living Expenses)
###   category_group (e.g., Health Care, Travel, Insurance)
###   category_name (e.g., Dental Care, Summer Vacation, Auto Insurance)
###   payee_name (e.g., HEB, Delta Airlines, Lemonade Insurance)
### by both:
###   months
###   year

### by category super groups
df_sgrp_monthly = dh.group_sum(df,["month", "category_supergroup"])
df_sgrp_yearly = dh.group_sum(df,["year", "category_supergroup"])

# by category groups
df_grp_monthly = dh.group_sum(df,["month", "category_group"])
df_grp_yearly = dh.group_sum(df,["year", "category_group"])

# by category name
df_cat_monthly = dh.group_sum(df,["month", "category_group", "category_name"])
df_cat_yearly = dh.group_sum(df,["year", "category_group", "category_name"])

# by payee name
df_pyn_monthly = dh.group_sum(df,["month", "category_name", "payee_name"])
df_pyn_yearly = dh.group_sum(df,["year", "category_name", "payee_name"])

### chart specifications are imported as chart_specs ###
### generate charts from spec dictionaries ###
### initialize empty dictionary to be populated in the loop ###
charts = {}
### loop through specs to generate charts for each dictionary
for spec in chart_specs:
    # resolve the df from df_name
    spec["df"] = globals()[spec["df_name"]]
    # Filter and sort
    filtered_df = dh.filter_group(spec["df"], spec["filter_col"], **spec["filter"])
    sorted_df = dh.sort_and_cast(filtered_df, spec["color_col"], spec["time_col"], ascending_order=True)

    # Generate charts
    for i, chart_type in enumerate(spec["chart_type"]):
        chart_key = f"{spec['name']}_{chart_type}"
        charts[chart_key] = dh.make_chart(
            sorted_df,
            chart_type,
            spec["time_col"],
            "amount",
            spec["color_col"],
            spec["title"][i],
            force_year_ticks=spec["force_year_ticks"][i]
        )

### annotations, should be made modular
charts["living_expenses_group_bar"].add_hline(
    y=8000,  # Replace with your desired y-axis value
    line_dash="solid",  # Optional: dashed line style
    line_color="black",  # Optional: line color
    annotation_text="Right Capital Target",  # Optional: label
    annotation_position="top left",  # Optional: label position
    annotation_font=dict(
        family="Arial Black",  # or any bold font family
        size=12,               # adjust size as needed
        color="brown")
)

# take a closer look at certain groups
# define the anchors
today, first_of_month, last_month, first_of_year, windows = dh.get_time_anchors()

# filter by super_group
df_cl_living = df[df["category_supergroup"] == "Living Expenses"]
df_cl_travel = df[df["category_group"] == "Goal - Travel"]
df_cl_goals = df[df["category_supergroup"] == "Goals"]
df_cl_basic = df[df["category_supergroup"] == "Basic Expenses"]

# summarize
df_cl_living_summary = dh.prepare_summary(df_cl_living, windows, first_of_year, last_month, group_col="category_name")
df_cl_travel_summary = dh.prepare_summary(df_cl_travel, windows, first_of_year, last_month)
df_cl_goals_summary = dh.prepare_summary(df_cl_goals, windows, first_of_year, last_month, group_col="category_group")
df_cl_basic_summary = dh.prepare_summary(df_cl_basic, windows, first_of_year, last_month, group_col="category_group")

# spending alerts: category_groups more than 20% above their 3-month average
df_main = df[df["category_supergroup"].isin(["Living Expenses", "Goals", "Basic Expenses"])]
df_alerts_raw = dh.prepare_summary(df_main, windows, first_of_year, last_month, group_col="category_group")
df_alerts = df_alerts_raw[df_alerts_raw["pct_ch_3m"].notna() & (df_alerts_raw["pct_ch_3m"] > ALERT_THRESHOLD)].sort_values("pct_ch_3m", ascending=False)

# style
df_cl_living_summary_styled = dh.style_summary(df_cl_living_summary)
df_cl_travel_summary_styled = dh.style_summary(df_cl_travel_summary)
df_cl_goals_summary_styled = dh.style_summary(df_cl_goals_summary)
df_cl_basic_summary_styled = dh.style_summary(df_cl_basic_summary)
df_alerts_styled = dh.style_summary(df_alerts)

### dashboard
st.set_page_config(layout="wide")
### data bits to add to heading
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)
port = 8501  # default Streamlit port

with st.container():
    st.title("Spending Dashboard")
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

# Sidebar
# st.sidebar.markdown(f"**Dashboard generated:** {timestamp}")
st.sidebar.markdown(f"""
**Dashboard generated:**\n
**{timestamp}**\n
**Dashboard URL:** [`http://{ip_address}:{port}`](http://{ip_address}:{port})
""")

sections = [
    "Spending Alerts",
    "Spending Breakdown",
    "Payee Cleanup",
    "Expense Super Groups",
    "Living Expenses",
    "Goals",
    "Basic Expenses",
    "Living Expense Details",
    "Travel Details",
    "Inflows"
]

selected_section = st.sidebar.radio("**Jump to Section**", sections)

if selected_section == "Spending Alerts":
    st.subheader("⚠️ Spending Alerts")
    st.caption("Category groups spending more than 20% above their 3-month average last month.")
    if df_alerts.empty:
        st.success("No categories significantly above their 3-month average.")
    else:
        st.warning(f"{len(df_alerts)} category group(s) are running above their 3-month average.")
        st.dataframe(df_alerts_styled)

elif selected_section == "Spending Breakdown":
    st.subheader("Spending Breakdown")
    years = sorted(df["year"].dropna().unique().tolist(), reverse=True)
    selected_year = st.selectbox("Select Year", ["All"] + years)
    fig_sb = dh.make_sunburst(df, year=selected_year)
    st.plotly_chart(fig_sb, width='stretch')

elif selected_section == "Payee Cleanup":
    st.subheader("Payee Cleanup")
    top_payees, variants = dh.payee_name_report(df)

    st.markdown("#### Top Payees by Transaction Count")
    st.caption("Highest-volume payees — most valuable to standardize first.")
    st.dataframe(
        top_payees.style
        .format({"transactions": "{:,}", "total_spent": "{:,.0f}"})
        .set_properties(**{"font-size": "14px"}),
        width='stretch'
    )

    st.markdown("#### Payees with Name Variants")
    st.caption("Groups sharing the same first 10 characters — likely the same vendor entered differently.")
    if variants.empty:
        st.success("No obvious name variants detected.")
    else:
        st.dataframe(
            variants.style
            .format({"variant_count": "{:,}", "transactions": "{:,}"})
            .set_properties(**{"font-size": "14px"}),
            width='stretch'
        )

elif selected_section == "Expense Super Groups":
    # with st.expander("📊 Expense Category Super Groups"):
    dh.render_chart_pair("Expense Category Super Groups (Yearly)", key_prefix="category_supergroups_yearly", charts=charts)
    dh.render_chart_pair("Expense Category Super Groups (Monthly)", key_prefix="category_supergroups_monthly", charts=charts)

elif selected_section == "Living Expenses":
    # with st.expander("🏠 Living Expenses"):
    dh.render_chart_pair("Living Expenses Category Groups", key_prefix="living_expenses_group", charts=charts)
    dh.render_chart_pair("Household Expenses Category Group", key_prefix="living_expenses_household", charts=charts)
    dh.render_chart_pair("Other Discretionary Expenses Category Group", key_prefix="living_expenses_other_discretionary", charts=charts)
    dh.render_chart_pair("Other Non-Discretionary Expenses Category Group", key_prefix="living_expenses_other_non_discretionary", charts=charts)
    dh.render_chart_pair("Insurance Expenses Category Group", key_prefix="living_expenses_insurance", charts=charts)
    dh.render_chart_pair("Auto/Transport Expenses Category Group", key_prefix="living_expenses_auto_transport", charts=charts)

elif selected_section == "Goals":
    # with st.expander("🎯 Goals"):
    dh.render_chart_pair("Goals Category Groups", key_prefix="goal_group", charts=charts)
    dh.render_chart_pair("Chris on Payroll Goal Category Group", key_prefix="goal_chris_on_payroll", charts=charts)
    dh.render_chart_pair("Travel Goal Category Group", key_prefix="goal_travel", charts=charts)
    dh.render_chart_pair("Children - Non Academic Goal Category Group", key_prefix="goal_children_non_academic", charts=charts)
    dh.render_chart_pair("Home Improvement Goal Category Group", key_prefix="goal_home_improvement", charts=charts)
    st.subheader("Goals Summary")
    st.dataframe(df_cl_goals_summary_styled)

elif selected_section == "Basic Expenses":
    # with st.expander("🧱 Basic Expenses"):
    dh.render_chart_pair("Basic Expenses Category Groups", key_prefix="basic_expenses_group", charts=charts)
    dh.render_chart_pair("Basic Expenses - Housing Category Group", key_prefix="basic_expenses_housing", charts=charts)
    dh.render_chart_pair("Basic Expenses - Rental Home Category Group", key_prefix="basic_expenses_rental_home", charts=charts)
    dh.render_chart_pair("Basic Expenses - Health Care Category Group", key_prefix="basic_expenses_health_care", charts=charts)
    st.subheader("Basic Expenses Summary")
    st.dataframe(df_cl_basic_summary_styled)

elif selected_section == "Inflows":
    dh.render_chart_pair("Inflow Category Groups", key_prefix="inflow", charts=charts)

elif selected_section == "Living Expense Details":
    st.subheader("🏠 Living Expenses Details")
    st.dataframe(df_cl_living_summary_styled)

elif selected_section == "Travel Details":
    st.subheader("✈️ Travel Spending Details")
    st.dataframe(df_cl_travel_summary_styled)

