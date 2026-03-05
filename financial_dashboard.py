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

@st.cache_data
def load_data(refresh):
    if refresh:
        return get_ynab_data()
    df = pd.read_csv("ynab_extract.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

df = load_data(refresh_data)

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

@st.cache_data
def build_static_charts(df):
    agg = {
        "df_sgrp_monthly": dh.group_sum(df, ["month", "category_supergroup"]),
        "df_sgrp_yearly":  dh.group_sum(df, ["year",  "category_supergroup"]),
        "df_grp_monthly":  dh.group_sum(df, ["month", "category_group"]),
        "df_grp_yearly":   dh.group_sum(df, ["year",  "category_group"]),
        "df_cat_monthly":  dh.group_sum(df, ["month", "category_group", "category_name"]),
        "df_cat_yearly":   dh.group_sum(df, ["year",  "category_group", "category_name"]),
        "df_pyn_monthly":  dh.group_sum(df, ["month", "category_name", "payee_name"]),
        "df_pyn_yearly":   dh.group_sum(df, ["year",  "category_name", "payee_name"]),
    }
    charts = {}
    for spec in chart_specs:
        filtered_df = dh.filter_group(agg[spec["df_name"]], spec["filter_col"], **spec["filter"])
        sorted_df = dh.sort_and_cast(filtered_df, spec["color_col"], spec["time_col"], ascending_order=True)
        for i, chart_type in enumerate(spec["chart_type"]):
            charts[f"{spec['name']}_{chart_type}"] = dh.make_chart(
                sorted_df, chart_type, spec["time_col"], "amount",
                spec["color_col"], spec["title"][i], force_year_ticks=spec["force_year_ticks"][i]
            )
    charts["living_expenses_group_bar"].add_hline(
        y=8000, line_dash="solid", line_color="black",
        annotation_text="Right Capital Target", annotation_position="top left",
        annotation_font=dict(family="Arial Black", size=12, color="brown")
    )
    return charts

charts = build_static_charts(df)

today, first_of_month, last_month, first_of_year, windows = dh.get_time_anchors()

@st.cache_data
def compute_summaries(df, windows, first_of_year, last_month):
    df_main = df[df["category_supergroup"].isin(["Living Expenses", "Goals", "Basic Expenses"])]
    return (
        dh.prepare_summary(df[df["category_supergroup"] == "Living Expenses"], windows, first_of_year, last_month, group_col="category_name"),
        dh.prepare_summary(df[df["category_group"] == "Goal - Travel"],        windows, first_of_year, last_month),
        dh.prepare_summary(df[df["category_supergroup"] == "Goals"],           windows, first_of_year, last_month, group_col="category_group"),
        dh.prepare_summary(df[df["category_supergroup"] == "Basic Expenses"],  windows, first_of_year, last_month, group_col="category_group"),
        dh.prepare_summary(df_main,                                            windows, first_of_year, last_month, group_col="category_group"),
    )

(df_cl_living_summary, df_cl_travel_summary, df_cl_goals_summary,
 df_cl_basic_summary, df_alerts_raw) = compute_summaries(df, windows, first_of_year, last_month)

df_alerts = df_alerts_raw[df_alerts_raw["pct_ch_3m"].notna() & (df_alerts_raw["pct_ch_3m"] > ALERT_THRESHOLD)].sort_values("pct_ch_3m", ascending=False)

# style
df_cl_living_summary_styled = dh.style_summary(df_cl_living_summary)
df_cl_travel_summary_styled = dh.style_summary(df_cl_travel_summary)
df_cl_goals_summary_styled = dh.style_summary(df_cl_goals_summary)
df_cl_basic_summary_styled = dh.style_summary(df_cl_basic_summary)
df_alerts_styled = dh.style_summary(df_alerts)

### dashboard
st.set_page_config(layout="wide")
st.markdown("""<style>
[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
</style>""", unsafe_allow_html=True)
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
    "Trend Analysis",
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
    st.caption(f"Category groups spending more than {ALERT_THRESHOLD:.0%} above their 3-month average last month.")
    if df_alerts.empty:
        st.success("No categories significantly above their 3-month average.")
    else:
        st.warning(f"{len(df_alerts)} category group(s) are running above their 3-month average.")
        st.dataframe(df_alerts_styled)

        st.markdown("---")
        st.markdown("#### Drill Down")
        month_label = last_month.strftime("%B %Y")
        alert_groups = df_alerts["category_name"].tolist()  # category_name column holds category_group values here
        selected_group = st.selectbox("Select a category group to inspect", alert_groups, key="alert_drilldown")

        df_last = df[
            (df["category_group"] == selected_group) &
            (df["date"] >= last_month) &
            (df["date"] < first_of_month) &
            (df["amount"] > 0)
        ].copy()

        # same month one year prior for comparison
        last_month_ly = last_month - pd.DateOffset(years=1)
        first_of_month_ly = first_of_month - pd.DateOffset(years=1)
        df_ly = df[
            (df["category_group"] == selected_group) &
            (df["date"] >= last_month_ly) &
            (df["date"] < first_of_month_ly) &
            (df["amount"] > 0)
        ].copy()

        total_last = df_last["amount"].sum()
        total_ly = df_ly["amount"].sum()
        ly_label = last_month_ly.strftime("%B %Y")

        col_a, col_b, col_c = st.columns(3)
        col_a.metric(f"{month_label} Total", f"${total_last:,.0f}")
        col_b.metric(f"{ly_label} Total", f"${total_ly:,.0f}")
        if total_ly > 0:
            col_c.metric("vs Same Month Last Year", f"{(total_last - total_ly) / total_ly:+.1%}")

        st.markdown(f"**Category breakdown — {month_label}**")
        cat_breakdown = (
            df_last.groupby("category_name")["amount"]
            .sum().reset_index()
            .sort_values("amount", ascending=False)
        )
        st.dataframe(
            cat_breakdown.style.format({"amount": "{:,.0f}"}),
            hide_index=True, width='stretch'
        )

        st.markdown(f"**Transactions — {month_label}**")
        tx_cols = ["date", "category_name", "payee_name", "amount"]
        if "memo" in df_last.columns:
            tx_cols.append("memo")
        df_show = df_last[tx_cols].sort_values("amount", ascending=False).copy()
        df_show["date"] = df_show["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            df_show.style.format({"amount": "{:,.0f}"}),
            hide_index=True, width='stretch'
        )

elif selected_section == "Spending Breakdown":
    st.subheader("Spending Breakdown")
    col_yr, col_sg = st.columns(2)
    with col_yr:
        years = sorted(df["year"].dropna().unique().tolist(), reverse=True)
        selected_year = st.selectbox("Select Year", ["All"] + years, key="sb_year")
    with col_sg:
        selected_sg = st.selectbox(
            "Select Supergroup",
            ["All", "Living Expenses", "Goals", "Basic Expenses"],
            key="sb_sg"
        )

    tab_sun, tab_tree, tab_ice, tab_tx = st.tabs(["Sunburst", "Treemap", "Icicle", "Transactions"])
    with tab_sun:
        st.plotly_chart(dh.make_hierarchy_chart(df, "sunburst", selected_year, selected_sg), width='stretch', key=f"sun_{selected_year}_{selected_sg}")
    with tab_tree:
        st.plotly_chart(dh.make_hierarchy_chart(df, "treemap", selected_year, selected_sg), width='stretch', key=f"tree_{selected_year}_{selected_sg}")
    with tab_ice:
        st.plotly_chart(dh.make_hierarchy_chart(df, "icicle", selected_year, selected_sg), width='stretch', key=f"ice_{selected_year}_{selected_sg}")

    with tab_tx:
        st.markdown("#### Transaction Drill-Down")
        st.caption("Each dropdown narrows the next. Year and supergroup filters above apply here too.")

        # Base: respect both top-level filters, expenses only
        df_base = df[df["category_supergroup"].isin(["Living Expenses", "Goals", "Basic Expenses"])].copy()
        if selected_year and selected_year != "All":
            df_base = df_base[df_base["year"] == selected_year]
        if selected_sg and selected_sg != "All":
            df_base = df_base[df_base["category_supergroup"] == selected_sg]
        df_base = df_base[df_base["amount"] > 0]

        # When a supergroup is already chosen above, skip that dropdown (3 cols); otherwise show all 4
        if selected_sg and selected_sg != "All":
            col1, col2, col3 = st.columns(3)
            with col1:
                sel_grp = st.selectbox("Group", ["All"] + sorted(df_base["category_group"].dropna().unique()), key="drill_grp")
            df_grp = df_base if sel_grp == "All" else df_base[df_base["category_group"] == sel_grp]
            with col2:
                sel_cat = st.selectbox("Category", ["All"] + sorted(df_grp["category_name"].dropna().unique()), key="drill_cat")
            df_cat = df_grp if sel_cat == "All" else df_grp[df_grp["category_name"] == sel_cat]
            with col3:
                sel_payee = st.selectbox("Payee", ["All"] + sorted(df_cat["payee_name"].dropna().unique()), key="drill_payee")
            df_tx = df_cat if sel_payee == "All" else df_cat[df_cat["payee_name"] == sel_payee]
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                sel_sg2 = st.selectbox("Supergroup", ["All"] + sorted(df_base["category_supergroup"].dropna().unique()), key="drill_sg")
            df_sg2 = df_base if sel_sg2 == "All" else df_base[df_base["category_supergroup"] == sel_sg2]
            with col2:
                sel_grp = st.selectbox("Group", ["All"] + sorted(df_sg2["category_group"].dropna().unique()), key="drill_grp")
            df_grp = df_sg2 if sel_grp == "All" else df_sg2[df_sg2["category_group"] == sel_grp]
            with col3:
                sel_cat = st.selectbox("Category", ["All"] + sorted(df_grp["category_name"].dropna().unique()), key="drill_cat")
            df_cat = df_grp if sel_cat == "All" else df_grp[df_grp["category_name"] == sel_cat]
            with col4:
                sel_payee = st.selectbox("Payee", ["All"] + sorted(df_cat["payee_name"].dropna().unique()), key="drill_payee")
            df_tx = df_cat if sel_payee == "All" else df_cat[df_cat["payee_name"] == sel_payee]

        # Summary metrics
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Transactions", f"{len(df_tx):,}")
        col_m2.metric("Total Spend", f"${df_tx['amount'].sum():,.0f}")
        col_m3.metric("Avg per Transaction", f"${df_tx['amount'].mean():,.0f}" if len(df_tx) > 0 else "—")

        # Transaction table — most recent first, capped at 500 rows
        tx_cols = ["date", "category_supergroup", "category_group", "category_name", "payee_name", "amount"]
        if "memo" in df_tx.columns:
            tx_cols.append("memo")
        df_tx_show = df_tx[tx_cols].sort_values("date", ascending=False).head(500).copy()
        df_tx_show["date"] = df_tx_show["date"].dt.strftime("%Y-%m-%d")
        if len(df_tx) > 500:
            st.caption(f"Showing 500 of {len(df_tx):,} transactions. Apply filters to narrow results.")
        st.dataframe(
            df_tx_show.style.format({"amount": "{:,.0f}"}),
            hide_index=True, width='stretch'
        )

elif selected_section == "Trend Analysis":
    st.subheader("Trend Analysis")
    tab_bubble, tab_heat = st.tabs(["Deviation Bubble Chart", "Monthly Heatmap"])

    with tab_bubble:
        st.caption("Each bubble is a category group. Right = higher avg spend. Up = recent spike vs 3-month avg. Size = YTD total.")
        st.plotly_chart(dh.make_bubble_chart(df, windows, first_of_year, last_month), width='stretch')

    with tab_heat:
        st.caption("Color shows each month vs that category's own average. Red = above avg, green = below. Hover for actual $.")
        supergroups = ["All", "Living Expenses", "Goals", "Basic Expenses"]
        years = sorted(df["year"].dropna().unique().tolist(), reverse=True)
        col_sg, col_yr = st.columns(2)
        with col_sg:
            selected_sg = st.selectbox("Filter by Supergroup", supergroups, key="heatmap_sg")
        with col_yr:
            selected_yr = st.selectbox("Filter by Year", ["All"] + years, key="heatmap_yr")
        st.plotly_chart(dh.make_heatmap(df, supergroup=selected_sg, year=selected_yr), width='stretch')

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

