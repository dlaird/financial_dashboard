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
import pending_db
import ynab_writer as yw
# from config_charts_dev import chart_specs

### get data
### refresh_data toggle — pass --refresh-data at the command line to fetch from YNAB
_parser = argparse.ArgumentParser()
_parser.add_argument("--refresh-data", action="store_true", default=False)
_args, _ = _parser.parse_known_args()
refresh_data = _args.refresh_data

@st.cache_data
def load_data(refresh, demo=False):
    if refresh:
        df = get_ynab_data()
    else:
        df = pd.read_csv("ynab_extract.csv")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if demo:
        df = dh.apply_demo_scramble(df)
    return df

demo_mode = st.session_state.get("demo_mode", False)
df = load_data(refresh_data, demo_mode)

today, first_of_month, last_month, first_of_year, windows = dh.get_time_anchors()

# df_analytics: capped at end of last full month — used for charts and summaries
# so a partial current month never distorts bars or averages.
# df (full): used for transaction-level drill-downs where you want to see recent activity.
df_analytics = df[df["date"] < first_of_month].copy()

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
def build_static_charts(df, demo=False):
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
    if not demo:
        charts["living_expenses_group_bar"].add_hline(
            y=8000, line_dash="solid", line_color="black",
            annotation_text="Right Capital Target", annotation_position="top left",
            annotation_font=dict(family="Arial Black", size=12, color="brown")
        )
    return charts

charts = build_static_charts(df_analytics, demo_mode)

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
 df_cl_basic_summary, df_alerts_raw) = compute_summaries(df_analytics, windows, first_of_year, last_month)

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
port = 8501  # default Streamlit port
try:
    # Connect to an external address (doesn't send data) to find the real LAN IP
    _s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _s.connect(("8.8.8.8", 80))
    ip_address = _s.getsockname()[0]
    _s.close()
except Exception:
    ip_address = socket.gethostbyname(socket.gethostname())

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

st.sidebar.checkbox("Demo Mode", key="demo_mode", help="Scrambles amounts and payee names for safe screen-sharing.")
if demo_mode:
    st.sidebar.error("DEMO MODE — numbers are not real")

_pending_count = len(pending_db.get_pending())
_pending_label = f"Pending Transactions ({_pending_count})" if _pending_count else "Pending Transactions"

_SECTION_KEYS = [
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
    "Inflows",
    "How to Use",
    "Pending Transactions",
]
_PENDING_IDX = _SECTION_KEYS.index("Pending Transactions")

# Display labels: pending entry gets the live count; all others are unchanged
_section_labels = _SECTION_KEYS[:-1] + [_pending_label]

if "nav_idx" not in st.session_state:
    st.session_state["nav_idx"] = 0

_selected_label = st.sidebar.radio("**Jump to Section**", _section_labels, index=st.session_state["nav_idx"])
_selected_display_idx = _section_labels.index(_selected_label)
st.session_state["nav_idx"] = _selected_display_idx
selected_section = _SECTION_KEYS[_selected_display_idx]

@st.cache_data(ttl=300)
def _ynab_accounts():
    try:
        return yw.get_accounts()
    except Exception:
        return []

@st.cache_data(ttl=300)
def _ynab_categories():
    try:
        return yw.get_categories()
    except Exception:
        return []

if selected_section == "Pending Transactions":
    st.subheader("📬 Pending Transactions")
    st.caption("Transactions parsed from email — review, edit, then approve or reject.")

    if st.button("Check for New Transactions", icon="📧"):
        import email_poller
        import io, logging
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(handler)
        try:
            email_poller.run()
        finally:
            logging.getLogger().removeHandler(handler)
        output = buf.getvalue().strip()
        if output:
            st.code(output)
        st.session_state["nav_idx"] = _PENDING_IDX
        st.rerun()

    pending = pending_db.get_pending()
    if not pending:
        st.success("No pending transactions. Send a YNAB email to get started.")
    else:
        accounts = _ynab_accounts()
        categories = _ynab_categories()
        acct_names = [a["name"] for a in accounts]
        cat_names = [f"{c['group_name']} → {c['name']}" for c in categories]
        cat_lookup = {f"{c['group_name']} → {c['name']}": c["id"] for c in categories}
        acct_lookup = {a["name"]: a["id"] for a in accounts}

        if "dup_warnings" not in st.session_state:
            st.session_state["dup_warnings"] = {}

        for tx in pending:
            tx_id = tx["id"]
            label = f"#{tx_id} — {tx.get('payee') or 'Unknown payee'}  |  ${abs((tx.get('amount_milliunits') or 0) / 1000):.2f}  |  {tx.get('date', '')}"
            with st.expander(label, expanded=True):
                if tx.get("parse_warnings"):
                    st.warning(f"Parse warnings: {tx['parse_warnings']}")

                col1, col2 = st.columns(2)
                with col1:
                    payee = st.text_input("Payee", value=tx.get("payee") or "", key=f"payee_{tx_id}")
                    amount_dollars = st.number_input(
                        "Amount ($)",
                        value=abs((tx.get("amount_milliunits") or 0) / 1000),
                        min_value=0.0, step=0.01, format="%.2f",
                        key=f"amt_{tx_id}",
                    )
                    tx_date = st.text_input("Date (YYYY-MM-DD)", value=tx.get("date") or "", key=f"date_{tx_id}")

                with col2:
                    # Account selector
                    default_acct = tx.get("account_name") or ""
                    acct_options = acct_names if acct_names else [default_acct]
                    acct_idx = acct_options.index(default_acct) if default_acct in acct_options else 0
                    selected_acct = st.selectbox("Account", acct_options, index=acct_idx, key=f"acct_{tx_id}")

                    # Category selector
                    default_cat_display = ""
                    if tx.get("category_name"):
                        matches = [k for k in cat_names if tx["category_name"] in k]
                        default_cat_display = matches[0] if matches else ""
                    cat_options = ["(none)"] + cat_names
                    cat_idx = cat_options.index(default_cat_display) if default_cat_display in cat_options else 0
                    selected_cat_display = st.selectbox("Category", cat_options, index=cat_idx, key=f"cat_{tx_id}")

                    memo = st.text_input("Memo", value=tx.get("memo") or "", key=f"memo_{tx_id}")

                # Duplicate warning (persists across reruns via session state)
                dup_key = f"dups_{tx_id}"
                if st.session_state["dup_warnings"].get(dup_key):
                    dups = st.session_state["dup_warnings"][dup_key]
                    st.error(f"⚠️ {len(dups)} possible duplicate(s) found in YNAB:")
                    for d in dups:
                        st.markdown(f"- {d['date']}  |  {d['payee']}  |  ${abs(d['amount_milliunits']/1000):.2f}")

                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
                approve_label = "Approve Anyway" if st.session_state["dup_warnings"].get(dup_key) else "Approve"

                with btn_col1:
                    if st.button(approve_label, key=f"approve_{tx_id}", type="primary"):
                        amount_mu = -int(round(amount_dollars * 1000))
                        resolved_acct_id = acct_lookup.get(selected_acct)
                        resolved_cat_id = cat_lookup.get(selected_cat_display) if selected_cat_display != "(none)" else None

                        # Duplicate check (skip if already warned)
                        if not st.session_state["dup_warnings"].get(dup_key):
                            try:
                                dups = yw.check_duplicate(tx_date, amount_mu, payee)
                                if dups:
                                    st.session_state["dup_warnings"][dup_key] = dups
                                    st.session_state["nav_idx"] = _PENDING_IDX
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Duplicate check failed: {e}")

                        if not st.session_state["dup_warnings"].get(dup_key) or approve_label == "Approve Anyway":
                            if not resolved_acct_id:
                                st.error("Account not found — select a valid account before approving.")
                            else:
                                try:
                                    ynab_id = yw.post_transaction(
                                        date=tx_date,
                                        amount_milliunits=amount_mu,
                                        payee=payee,
                                        account_id=resolved_acct_id,
                                        category_id=resolved_cat_id,
                                        memo=memo or None,
                                    )
                                    pending_db.approve_transaction(tx_id, ynab_id)
                                    st.session_state["dup_warnings"].pop(dup_key, None)
                                    st.success(f"Posted to YNAB (id: {ynab_id})")
                                    st.session_state["nav_idx"] = _PENDING_IDX
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to post to YNAB: {e}")

                with btn_col2:
                    if st.button("Reject", key=f"reject_{tx_id}"):
                        pending_db.reject_transaction(tx_id)
                        st.session_state["dup_warnings"].pop(f"dups_{tx_id}", None)
                        st.session_state["nav_idx"] = _PENDING_IDX
                        st.rerun()

elif selected_section == "Spending Alerts":
    st.subheader("⚠️ Spending Alerts")
    st.caption(f"Category groups spending more than {ALERT_THRESHOLD:.0%} above their 3-month average last month.")
    if df_alerts.empty:
        st.success("No categories significantly above their 3-month average.")
    else:
        st.warning(f"{len(df_alerts)} category group(s) are running above their 3-month average.")
        st.dataframe(df_alerts_styled)

        st.markdown("---")
        st.markdown("#### Drill Down")
        st.caption(f"Alerts based on {last_month.strftime('%B %Y')}. Transaction tables below include data through today.")
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
    st.caption(f"Charts show data through {last_month.strftime('%B %Y')} (last full month). Transaction tab includes data through today.")
    with col_sg:
        selected_sg = st.selectbox(
            "Select Supergroup",
            ["All", "Living Expenses", "Goals", "Basic Expenses"],
            key="sb_sg"
        )

    tab_sun, tab_tree, tab_ice, tab_tx = st.tabs(["Sunburst", "Treemap", "Icicle", "Transactions"])
    with tab_sun:
        st.plotly_chart(dh.make_hierarchy_chart(df_analytics, "sunburst", selected_year, selected_sg), width='stretch', key=f"sun_{selected_year}_{selected_sg}")
    with tab_tree:
        st.plotly_chart(dh.make_hierarchy_chart(df_analytics, "treemap", selected_year, selected_sg), width='stretch', key=f"tree_{selected_year}_{selected_sg}")
    with tab_ice:
        st.plotly_chart(dh.make_hierarchy_chart(df_analytics, "icicle", selected_year, selected_sg), width='stretch', key=f"ice_{selected_year}_{selected_sg}")

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
        st.plotly_chart(dh.make_bubble_chart(df_analytics, windows, first_of_year, last_month), width='stretch')

    with tab_heat:
        st.caption("Color shows each month vs that category's own average. Red = above avg, green = below. Hover for actual $.")
        supergroups = ["All", "Living Expenses", "Goals", "Basic Expenses"]
        years = sorted(df_analytics["year"].dropna().unique().tolist(), reverse=True)
        col_sg, col_yr = st.columns(2)
        with col_sg:
            selected_sg = st.selectbox("Filter by Supergroup", supergroups, key="heatmap_sg")
        with col_yr:
            selected_yr = st.selectbox("Filter by Year", ["All"] + years, key="heatmap_yr")
        st.plotly_chart(dh.make_heatmap(df_analytics, supergroup=selected_sg, year=selected_yr), width='stretch')

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

elif selected_section == "How to Use":
    st.subheader("How to Use This Dashboard")

    st.markdown("### Overview")
    st.markdown("""
This dashboard pulls your transaction data from **YNAB** and adds the analytical views that YNAB's built-in reports don't provide:
trend detection, deviation alerts, drillable spending breakdowns, and a quick-entry pipeline for logging transactions by email.

YNAB categories are named to match the groups used by your financial advisor's **Right Capital** plan.
The $8,000/month target line on the Living Expenses chart comes directly from that plan.
""")

    st.markdown("---")
    st.markdown("### Sections")
    st.markdown("""
| Section | What it shows |
|---|---|
| **Spending Alerts** | Category groups spending >20% above their 3-month average last month. Includes transaction drill-down. |
| **Spending Breakdown** | Drillable sunburst / treemap / icicle charts by supergroup → group → category → payee, plus a transaction table. |
| **Trend Analysis** | Deviation bubble chart (recent vs. historical) and a monthly heatmap by category group. |
| **Payee Cleanup** | Top payees by volume and groups of likely name variants to standardize in YNAB. |
| **Expense Super Groups** | Bar/line charts for Living Expenses, Goals, and Basic Expenses rolled up. |
| **Living Expenses** | Charts for each Living Expenses category group with the Right Capital $8K target line. |
| **Goals** | Charts and summary table for goal-related spending. |
| **Basic Expenses** | Charts and summary table for fixed/recurring expenses. |
| **Living Expense Details** | Month-by-month summary table with 3-month average and % deviation columns. |
| **Travel Details** | Same summary table scoped to the Travel goal group. |
| **Inflows** | Income and transfer inflows over time. |
| **Pending Transactions** | Review and approve transactions submitted by email before they post to YNAB. |
""")

    st.markdown("---")
    st.markdown("### Refreshing Data")
    st.markdown("""
By default the dashboard reads from the local `ynab_extract.csv` cache.
To pull fresh data from YNAB, restart with the `--refresh-data` flag:

```bash
.venv/bin/python -m streamlit run financial_dashboard.py -- --refresh-data
```
""")

    st.markdown("---")
    st.markdown("### Logging Transactions by Email — Phase 1 (Manual Entry)")
    st.markdown("""
You can add a YNAB transaction by sending a plain-text email to **k2udal@gmail.com**.

**Subject line:** anything containing `ynab` (case-insensitive)

**Body — one item per line, in this order:**

| Line | Field | Example |
|---|---|---|
| 1 | Amount | `47.23` or `$47.23` |
| 2 | Payee | `Whole Foods` |
| 3 | Account shortcut | `chase` |
| 4 | Category shortcut | `groceries` |
| 5+ | Memo (optional) | `weekly shopping` |

The transaction date is taken from the email's sent timestamp — no need to specify it.

**Example email body:**
```
47.23
Whole Foods
chase
groceries
weekly shopping
```

The email poller checks Gmail for unread messages matching the subject trigger and writes parsed transactions
to the Pending Transactions queue. Open the **Pending Transactions** section to review, edit, and approve
before posting to YNAB.
""")

    st.markdown("---")
    st.markdown("### Checking for New Transactions")
    st.markdown("""
Click **Check for New Transactions** at the top of the **Pending Transactions** section.
This runs the email poller on demand — no scheduled background process needed.

The poller checks Gmail for unread emails from trusted senders, parses them (Phase 1 or
Phase 2 depending on the subject), and adds results to the pending queue. The page
refreshes automatically when it's done.

Progress and any errors are also written to `email_poller.log` in the project folder.
""")

    st.markdown("---")
    st.markdown("### Account & Category Shortcuts")
    st.markdown("""
Shortcuts are defined in two JSON files in the project folder:

- `account_shortcuts.json` — maps aliases like `evisa`, `usaac` to exact YNAB account names
- `category_shortcuts.json` — maps aliases like `grocs`, `dining` to YNAB category names

Shortcuts are case-insensitive. To see all available shortcuts, run:
```bash
.venv/bin/python ynab_writer.py --list-accounts
.venv/bin/python ynab_writer.py --list-categories
```
""")

    st.markdown("---")
    st.markdown("### AI Bill & Receipt Processing (Phase 2)")
    st.markdown("""
Forwarded emails from known senders (Amazon, Whole Foods, utility companies) are
automatically parsed by Claude AI and added to the Pending Transactions queue.

**How it works:**
- Forward the bill or receipt email to **k2udal@gmail.com** — do **not** include `ynab` in the subject
- The poller detects the original sender, passes the email to Claude, and creates one pending
  transaction per order or charge
- Memo is prefixed with **D:** (David) or **M:** (Michele) based on who forwarded it
- Review and approve in the **Pending Transactions** section as usual

**Currently configured senders:**
| Sender | Payee | Account |
|---|---|---|
| amazon.com | Amazon | USAA Everyday Visa |
| wholefoodsmarket.com | Whole Foods | USAA Everyday Visa |
| City of Austin Utilities | City of Austin Utilities | USAA Checking |
| West Travis County PUD (via invoicecloud.net) | West Travis County PUD | USAA Checking |

**Adding a new sender:**

1. Forward one of their emails to k2udal@gmail.com (no `ynab` in subject)
2. Run the poller — it will log the exact From line:
   ```
   No sender rule for forwarded-from 'Acme Corp <billing@acme.com>' — skipping.
   ```
3. Add an entry to `phase2_sources.json` under `sender_rules`:

| Situation | Field to use | Example |
|---|---|---|
| Sender has a recognizable domain | `"domain"` | `"domain": "acme.com"` |
| Sender uses a billing service (e.g. InvoiceCloud) | `"name_contains"` | `"name_contains": "acme corp"` |
| Single specific address | `"address"` | `"address": "bills@acme.com"` |

Example entry:
```json
{
  "name_contains": "acme corp",
  "payee": "Acme Corp",
  "account": "usaac"
}
```
4. Mark the email unread in Gmail and run the poller again.
""")

    st.markdown("---")
    st.markdown("### Demo Mode")
    st.markdown("""
Toggle **Demo Mode** in the sidebar to scramble all dollar amounts and replace payee names
with generic labels (Vendor 001, Vendor 002, etc.). Use this when screen-sharing the
dashboard with someone you don't want to see your real financial data.

- Spending trends and chart shapes are preserved — the dashboard still makes sense to viewers
- The Right Capital $8,000 target line is hidden in demo mode
- Numbers are stable while you interact (toggling off restores real data instantly)
""")

elif selected_section == "Living Expense Details":
    st.subheader("🏠 Living Expenses Details")
    st.dataframe(df_cl_living_summary_styled)

elif selected_section == "Travel Details":
    st.subheader("✈️ Travel Spending Details")
    st.dataframe(df_cl_travel_summary_styled)

