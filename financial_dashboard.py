### at the command line> python -m streamlit run financial_dashboard.py

### dev
### - look at transactions with null category supergroup
###   remove anything where transaction begins "Transfer:"
###   chart monthly/yearly total by payee over time
###
### - organize dashboard



import pandas as pd
import plotly.express as px
import streamlit as st
import data_helpers as dh
from ynab_data_pipeline import get_ynab_data
from pandas.tseries.offsets import DateOffset
from config_charts import chart_specs

### get data
### use_api toggle
use_api = 0  # Set to False to load from CSV instead

if use_api:
    df = get_ynab_data()
else:
    df = pd.read_csv("ynab_extract.csv")

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
df_sgrp_monthly = dh.group_sum(df,["month_start", "category_supergroup"])
df_sgrp_yearly = dh.group_sum(df,["year", "category_supergroup"])

# by category groups
df_grp_monthly = dh.group_sum(df,["month_start", "category_group"])
df_grp_yearly = dh.group_sum(df,["year", "category_group"])

# by category name
df_cat_monthly = dh.group_sum(df,["month_start", "category_group", "category_name"])
df_cat_yearly = dh.group_sum(df,["year", "category_group", "category_name"])

# by payee name
df_pyn_monthly = dh.group_sum(df,["month_start", "category_name", "payee_name"])
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

### dashboard
### data bits to add to heading
from datetime import datetime
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

import socket
hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)
port = 8501  # default Streamlit port


st.set_page_config(layout="wide")

with st.container():
    st.title("Spending Dashboard")
    st.markdown(f"**Dashboard generated:** {timestamp}")
    st.markdown(f"""
    **Host:** `{hostname}`  
    **IP Address:** `{ip_address}`  
    **Dashboard URL:** [`http://{ip_address}:{port}`](http://{ip_address}:{port})
    """)
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

with st.expander("📊 Expense Category Super Groups"):
    dh.render_chart_pair("Expense Category Super Groups (Yearly)", key_prefix="category_supergroups_yearly", charts=charts)
    dh.render_chart_pair("Expense Category Super Groups (Monthly)", key_prefix="category_supergroups_monthly", charts=charts)

with st.expander("🏠 Living Expenses"):
    dh.render_chart_pair("Living Expenses Category Groups", key_prefix="living_expenses_group", charts=charts)
    dh.render_chart_pair("Household Expenses Category Group", key_prefix="living_expenses_household", charts=charts)
    dh.render_chart_pair("Other Discretionary Expenses Category Group", key_prefix="living_expenses_other_discretionary", charts=charts)
    dh.render_chart_pair("Other Non-Discretionary Expenses Category Group", key_prefix="living_expenses_other_non_discretionary", charts=charts)
    dh.render_chart_pair("Insurance Expenses Category Group", key_prefix="living_expenses_insurance", charts=charts)
    dh.render_chart_pair("Auto/Transport Expenses Category Group", key_prefix="living_expenses_auto_transport", charts=charts)

with st.expander("🎯 Goals"):
    dh.render_chart_pair("Goals Category Groups", key_prefix="goal_group", charts=charts)
    dh.render_chart_pair("Chris on Payroll Goal Category Group", key_prefix="goal_chris_on_payroll", charts=charts)
    dh.render_chart_pair("Travel Goal Category Group", key_prefix="goal_travel", charts=charts)
    # dh.render_chart_pair("Travel Goal Category Group", chart1=charts["goal_travel_line"], chart2=charts["goal_travel_bar"])
    dh.render_chart_pair("Children - Non Academic Goal Category Group", key_prefix="goal_children_non_academic", charts=charts)
    dh.render_chart_pair("Home Improvement Goal Category Group", key_prefix="goal_home_improvement", charts=charts)

with st.expander("🧱 Basic Expenses"):
    dh.render_chart_pair("Basic Expenses Category Groups", key_prefix="basic_expenses_group", charts=charts)
    dh.render_chart_pair("Basic Expenses - Housing Category Group", key_prefix="basic_expenses_housing", charts=charts)
    dh.render_chart_pair("Basic Expenses - Rental Home Category Group", key_prefix="basic_expenses_rental_home", charts=charts)
    dh.render_chart_pair("Basic Expenses - Health Care Category Group", key_prefix="basic_expenses_health_care", charts=charts)

with st.expander("💰 Inflow"):
    dh.render_chart_pair("Inflow by Source", key_prefix="inflow", charts=charts)


### Sidebar
# sections = [
#     "Expense Super Groups",
#     "Living Expenses",
#     "Goals",
#     "Basic Expenses"
# ]

# selected_section = st.sidebar.radio("Jump to Section", sections)

# if selected_section == "Expense Super Groups":
#     with st.expander("📊 Expense Category Super Groups"):
#         dh.render_chart_pair("Expense Category Super Groups (Yearly)", key_prefix="category_supergroups_yearly", charts=charts)
#         dh.render_chart_pair("Expense Category Super Groups (Monthly)", key_prefix="category_supergroups_monthly", charts=charts)

# elif selected_section == "Living Expenses":
#     with st.expander("🏠 Living Expenses"):
#         dh.render_chart_pair("Living Expenses Category Groups", key_prefix="living_expenses_group", charts=charts)
#         dh.render_chart_pair("Household Expenses Category Group", key_prefix="living_expenses_household", charts=charts)
#         dh.render_chart_pair("Other Discretionary Expenses Category Group", key_prefix="living_expenses_other_discretionary", charts=charts)
#         dh.render_chart_pair("Other Non-Discretionary Expenses Category Group", key_prefix="living_expenses_other_non_discretionary", charts=charts)
#         dh.render_chart_pair("Insurance Expenses Category Group", key_prefix="living_expenses_insurance", charts=charts)
#         dh.render_chart_pair("Auto/Transport Expenses Category Group", key_prefix="living_expenses_auto_transport", charts=charts)

# elif selected_section == "Goals":
#     with st.expander("🎯 Goals"):
#         dh.render_chart_pair("Goals Category Groups", key_prefix="goal_group", charts=charts)
#         dh.render_chart_pair("Travel Goal Category Group", chart1=charts["goal_travel_line"], chart2=charts["goal_travel_area"])
#         dh.render_chart_pair("Children - Non Academic Goal Category Group", key_prefix="goal_children_non_academic", charts=charts)

# elif selected_section == "Basic Expenses":
#     with st.expander("🧱 Basic Expenses"):
#         dh.render_chart_pair("Basic Expenses Category Groups", key_prefix="basic_expenses_group", charts=charts)
#         dh.render_chart_pair("Basic Expenses - Rental Home Category Group", key_prefix="basic_expenses_rental_home", charts=charts)
#         dh.render_chart_pair("Basic Expenses - Health Care Category Group", key_prefix="basic_expenses_health_care", charts=charts)

