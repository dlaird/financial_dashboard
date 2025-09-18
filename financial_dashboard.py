### at the command line> python -m streamlit run financial_dashboard.py

import pandas as pd
import plotly.express as px
import streamlit as st
import data_helpers as dh
from ynab_data_pipeline import get_ynab_data
from pandas.tseries.offsets import DateOffset

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

# filtering, sorting, and charting
# specifications for each chart reside in a list of dictionaries

chart_specs = [
    # Super Groups
    {
        "name": "category_supergroups_monthly",
        "df": df_sgrp_monthly,
        "filter_col": "category_supergroup",
        "filter": {"values": ["Basic Expenses", "Goals", "Living Expenses"]},
        "color_col": "category_supergroup",
        "time_col": "month_start",
        "chart_type": ["line", "bar"],
        "title": [
            "Category Super Groups",
            "Category Super Groups, Cumulative"
        ],
        "force_year_ticks": [True, True]
    },
    {
        "name": "category_supergroups_yearly",
        "df": df_sgrp_yearly,
        "filter_col": "category_supergroup",
        "filter": {"values": ["Basic Expenses", "Goals", "Living Expenses"]},
        "color_col": "category_supergroup",
        "time_col": "year",
        "chart_type": ["line", "bar"],
        "title": [
            "Category Super Groups",
            "Category Super Groups, Cumulative"
        ],
        "force_year_ticks": [True, True]
    },
    # Basic Expenses
    {
        "name": "basic_expenses_group",
        "df": df_grp_yearly,
        "filter_col": "category_group",
        "filter": {"startswith": "Basic Expenses -"},
        "color_col": "category_group",
        "time_col": "year",
        "chart_type": ["line", "bar"],
        "title": [
            "Basic Expenses by Category Group",
            "Basic Expenses by Category Group, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "basic_expenses_rental_home",
        "df": df_cat_yearly,
        "filter_col": "category_group",
        "filter": {"values": ["Basic Expenses - Rental Home"]},
        "color_col": "category_name",
        "time_col": "year",
        "chart_type": ["line", "bar"],
        "title": [
            "Basic Expenses - Rental Home Group by Category",
            "Basic Expenses - Rental Home Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "basic_expenses_health_care",
        "df": df_cat_yearly,
        "filter_col": "category_group",
        "filter": {"values": ["Basic Expenses - Health Care"]},
        "color_col": "category_name",
        "time_col": "year",
        "chart_type": ["line", "bar"],
        "title": [
            "Basic Expenses - Health Care Group by Category",
            "Basic Expenses - Health Care Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    # Goals
    {
        "name": "goal_group",
        "df": df_grp_yearly,
        "filter_col": "category_group",
        "filter": {"startswith": "Goal -"},
        "color_col": "category_group",
        "time_col": "year",
        "chart_type": ["line", "bar"],
        "title": [
            "Goal Expenses by Category Group",
            "Goal Expenses by Category Group, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "goal_travel",
        "df": df_cat_yearly,
        "filter_col": "category_group",
        "filter": {"values": ["Goal - Travel"]},
        "color_col": "category_name",
        "time_col": "year",
        "chart_type": ["line", "area"],
        "title": [
            "Goal - Travel Group by Category",
            "Goal - Travel Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "goal_children_non_academic",
        "df": df_cat_yearly,
        "filter_col": "category_group",
        "filter": {"values": ["Goal - Children (Non-Academic)"]},
        "color_col": "category_name",
        "time_col": "year",
        "chart_type": ["line", "bar"],
        "title": [
            "Goal - Children (Non-Academic) Group by Category",
            "Goal - Children (Non-Academic) Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },

    # Living Expenses
    {
        "name": "living_expenses_group",
        "df": df_grp_monthly,
        "filter_col": "category_group",
        "filter": {"startswith": "Living Expenses -"},
        "color_col": "category_group",
        "time_col": "month_start",
        "chart_type": ["line", "bar"],
        "title": [
            "Living Expenses Category Groups",
            "Living Expenses Category Groups, Cumulative"
        ],
        "force_year_ticks": [True, False]
        # ,
        # "annotations": [
        #     None,
        #     {
        #         "y": 8000,
        #         "line_dash": "solid",
        #         "line_color": "black",
        #         "annotation_text": "Right Capital Target",
        #         "annotation_position": "top left",
        #         "annotation_font": {
        #             "size": 12,
        #             "color": "brown"
        #         }
        #     }
        # ]
    },
    {
        "name": "living_expenses_auto_transport",
        "df": df_cat_yearly,
        "filter_col": "category_group",
        "filter": {"values": ["Living Expenses - Auto/Transport"]},
        "color_col": "category_name",
        "time_col": "year",
        "chart_type": ["line", "bar"],
        "title": [
            "Living Expenses - Auto/Transport Group by Category",
            "Living Expenses - Auto/Transport Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "living_expenses_household",
        "df": df_cat_monthly,
        "filter_col": "category_group",
        "filter": {"values": ["Living Expenses - Household"]},
        "color_col": "category_name",
        "time_col": "month_start",
        "chart_type": ["line", "bar"],
        "title": [
            "Living Expenses - Household Group by Category",
            "Living Expenses - Household Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "living_expenses_insurance",
        "df": df_cat_yearly,
        "filter_col": "category_group",
        "filter": {"values": ["Living Expenses - Insurance"]},
        "color_col": "category_name",
        "time_col": "year",
        "chart_type": ["line", "bar"],
        "title": [
            "Living Expenses - Insurance Group by Category",
            "Living Expenses - Insurance Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "living_expenses_other_discretionary",
        "df": df_cat_monthly,
        "filter_col": "category_group",
        "filter": {"values": ["Living Expenses - Other Discretionary"]},
        "color_col": "category_name",
        "time_col": "month_start",
        "chart_type": ["line", "bar"],
        "title": [
            "Living Expenses - Other Discretionary Group by Category",
            "Living Expenses - Other Discretionary Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "living_expenses_other_non_discretionary",
        "df": df_cat_monthly,
        "filter_col": "category_group",
        "filter": {"values": ["Living Expenses - Other Non-Discretionary"]},
        "color_col": "category_name",
        "time_col": "month_start",
        "chart_type": ["line", "bar"],
        "title": [
            "Living Expenses - Other Non-Discretionary Group by Category",
            "Living Expenses - Other Non-Discretionary Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    }
]

### Generate charts from spec dictionaries ###
### initialize empty dictionary to be populated in the loop
charts = {}
### loop through specs to generate charts for each dictionary
for spec in chart_specs:
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
charts["living_expenses_group_line"].add_hline(
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
st.set_page_config(layout="wide")

with st.container():
    st.title("Spending Dashboard")
    st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

dh.render_chart_pair("Expense Category Super Groups (Yearly)", key_prefix="category_supergroups_yearly", charts=charts)
dh.render_chart_pair("Expense Category Super Groups (Monthly)", key_prefix="category_supergroups_monthly", charts=charts)

dh.render_chart_pair("Living Expenses Category Groups", key_prefix="living_expenses_group", charts=charts)
dh.render_chart_pair("Household Expenses Category Group", key_prefix="living_expenses_household", charts=charts)
dh.render_chart_pair("Other Discretionary Expenses Category Group", key_prefix="living_expenses_other_discretionary", charts=charts)
dh.render_chart_pair("Other Non-Discretionary Expenses Category Group", key_prefix="living_expenses_other_non_discretionary", charts=charts)
dh.render_chart_pair("Insurance Expenses Category Group", key_prefix="living_expenses_insurance", charts=charts)
dh.render_chart_pair("Auto/Transport Expenses Category Group", key_prefix="living_expenses_auto_transport", charts=charts)

dh.render_chart_pair("Goals Category Groups", key_prefix="goal_group", charts=charts)
dh.render_chart_pair("Travel Goal Category Group", chart1=charts["goal_travel_line"], chart2=charts["goal_travel_area"])
dh.render_chart_pair("Children - Non Academic Goal Category Group", key_prefix="goal_children_non_academic", charts=charts)

dh.render_chart_pair("Basic Expenses Category Groups", key_prefix="basic_expenses_group", charts=charts)
dh.render_chart_pair("Basic Expenses - Rental Home Category Group", key_prefix="basic_expenses_rental_home", charts=charts)
dh.render_chart_pair("Basic Expenses - Health Care Category Group", key_prefix="basic_expenses_health_care", charts=charts)
