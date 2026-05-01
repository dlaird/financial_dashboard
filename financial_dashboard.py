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
import os
import pandas as pd
import plotly.express as px
import streamlit as st
import socket
from datetime import date, datetime, timedelta
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
section[data-testid="stSidebar"] .stButton > button {
    width: 200px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-left: 14px;
}
.block-container { padding-top: 1rem !important; }
</style>""", unsafe_allow_html=True)
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
    st.markdown("<h1 style='margin:0 0 0.1rem 0; font-size:2.2rem; font-weight:700'>Spending Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<hr style='border:2px solid #bbb; margin-top:0.4rem'>", unsafe_allow_html=True)

# ---- Sidebar: Refresh ----
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    with st.spinner("Fetching latest data from YNAB..."):
        get_ynab_data()
        load_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# ---- Navigation ----
_spending_keys = [
    "Spending Breakdown", "Spending Alerts", "Actual vs. Plan",
    "Trend Analysis", "Expense Super Groups", "Living Expenses",
    "Goals", "Basic Expenses", "Inflows", "Other Expenses",
]
_utility_keys = ["Pending Transactions", "Payee Cleanup", "How to Use"]
_pending_count = len(pending_db.get_pending())

# Programmatic navigation (from approve/reject/poll actions — set nav_target before rerun)
_nav_target = st.session_state.pop("nav_target", None)
if _nav_target:
    st.session_state["_nav_selected"] = _nav_target

if "_nav_selected" not in st.session_state:
    st.session_state["_nav_selected"] = "Spending Breakdown"

_selected = st.session_state["_nav_selected"]

def _nav_label(key):
    if key == "Pending Transactions" and _pending_count:
        return f"Pending Transactions ({_pending_count})"
    return key

st.sidebar.markdown("**Spending Analysis**")
for _nk in _spending_keys:
    if st.sidebar.button(_nav_label(_nk), key=f"nav_{_nk}",
                         type="primary" if _selected == _nk else "secondary"):
        st.session_state["_nav_selected"] = _nk
        st.rerun()

st.sidebar.markdown("**Utility**")
for _nk in _utility_keys:
    if st.sidebar.button(_nav_label(_nk), key=f"nav_{_nk}",
                         type="primary" if _selected == _nk else "secondary"):
        st.session_state["_nav_selected"] = _nk
        st.rerun()

selected_section = _selected

# ---- Demo Mode ----
st.sidebar.markdown("---")
st.sidebar.checkbox("Demo Mode", key="demo_mode", help="Scrambles amounts and payee names for safe screen-sharing.")
if demo_mode:
    st.sidebar.error("DEMO MODE — numbers are not real")

# ---- Dashboard info ----
st.sidebar.markdown("---")
_csv_path = "ynab_extract.csv"
_data_ts = (datetime.fromtimestamp(os.path.getmtime(_csv_path)).strftime("%Y-%m-%d %H:%M")
            if os.path.exists(_csv_path) else "unknown")
st.sidebar.markdown(f"""
**Dashboard URL:**
[`http://{ip_address}:{port}`](http://{ip_address}:{port})

**Data last refreshed:**
{_data_ts}
""")

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

    _polling = st.session_state.get("polling", False)
    if st.button("Check for New Transactions", icon="📧", disabled=_polling):
        st.session_state["polling"] = True
        st.rerun()

    if _polling:
        import email_poller
        import io, logging
        with st.spinner("Checking for new transactions..."):
            buf = io.StringIO()
            handler = logging.StreamHandler(buf)
            handler.setLevel(logging.INFO)
            logging.getLogger().addHandler(handler)
            try:
                email_poller.run()
            finally:
                logging.getLogger().removeHandler(handler)
        st.session_state["polling"] = False
        st.session_state["nav_target"] = "Pending Transactions"
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

        tx_by_id = {tx["id"]: tx for tx in pending}

        def _bulk_post(target_ids):
            successes, errors = [], []
            for tid in target_ids:
                tx = tx_by_id[tid]
                # Use edited session_state values; fall back to DB values if widget not yet rendered
                payee_val  = st.session_state.get(f"payee_{tid}", tx.get("payee") or "")
                amt_val    = st.session_state.get(f"amt_{tid}",   abs((tx.get("amount_milliunits") or 0) / 1000))
                date_val   = st.session_state.get(f"date_{tid}",  tx.get("date") or "")
                acct_val   = st.session_state.get(f"acct_{tid}",  tx.get("account_name") or "")
                cat_val    = st.session_state.get(f"cat_{tid}",   "")
                memo_val   = st.session_state.get(f"memo_{tid}",  tx.get("memo") or "")
                amount_mu  = -int(round(amt_val * 1000))
                resolved_acct_id = acct_lookup.get(acct_val)
                resolved_cat_id  = cat_lookup.get(cat_val) if cat_val and cat_val != "(none)" else None
                if not resolved_acct_id:
                    errors.append(f"#{tid} ({payee_val}): account not found — skipped")
                    continue
                try:
                    ynab_id = yw.post_transaction(
                        date=date_val, amount_milliunits=amount_mu, payee=payee_val,
                        account_id=resolved_acct_id, category_id=resolved_cat_id,
                        memo=memo_val or None,
                    )
                    pending_db.approve_transaction(tid, ynab_id)
                    successes.append(tid)
                except Exception as e:
                    errors.append(f"#{tid} ({payee_val}): {e}")
            return successes, errors

        # ---- Bulk action bar ----
        _all_ids = [tx["id"] for tx in pending]
        _sel_ids = [tid for tid in _all_ids if st.session_state.get(f"sel_{tid}", False)]

        _bc1, _bc2, _bc3 = st.columns([1, 1, 3])
        with _bc1:
            _approve_all = st.button("Approve All", key="bulk_approve_all", type="primary")
        with _bc2:
            _sel_label = f"Approve Selected ({len(_sel_ids)})" if _sel_ids else "Approve Selected"
            _approve_sel = st.button(_sel_label, key="bulk_approve_sel", type="primary", disabled=not _sel_ids)

        if _approve_all or _approve_sel:
            _targets = _all_ids if _approve_all else _sel_ids
            _ok, _errs = _bulk_post(_targets)
            if _ok:
                st.success(f"Approved {len(_ok)} transaction(s).")
            for _e in _errs:
                st.error(_e)
            if _ok:
                st.session_state["nav_target"] = "Pending Transactions"
                st.rerun()

        st.markdown("---")

        # ---- Individual transactions ----
        for tx in pending:
            tx_id = tx["id"]
            label = f"#{tx_id} — {tx.get('payee') or 'Unknown payee'}  |  ${abs((tx.get('amount_milliunits') or 0) / 1000):.2f}  |  {tx.get('date', '')}"

            chk_col, exp_col = st.columns([1, 25])
            with chk_col:
                st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)
                st.checkbox("", key=f"sel_{tx_id}", label_visibility="collapsed")
            with exp_col:
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
                    default_acct = tx.get("account_name") or ""
                    acct_options = acct_names if acct_names else [default_acct]
                    acct_idx = acct_options.index(default_acct) if default_acct in acct_options else 0
                    selected_acct = st.selectbox("Account", acct_options, index=acct_idx, key=f"acct_{tx_id}")

                    default_cat_display = ""
                    if tx.get("category_name"):
                        matches = [k for k in cat_names if tx["category_name"] in k]
                        default_cat_display = matches[0] if matches else ""
                    cat_options = ["(none)"] + cat_names
                    cat_idx = cat_options.index(default_cat_display) if default_cat_display in cat_options else 0
                    selected_cat_display = st.selectbox("Category", cat_options, index=cat_idx, key=f"cat_{tx_id}")

                    memo = st.text_input("Memo", value=tx.get("memo") or "", key=f"memo_{tx_id}")

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

                        if not st.session_state["dup_warnings"].get(dup_key):
                            try:
                                dups = yw.check_duplicate(tx_date, amount_mu, payee)
                                if dups:
                                    st.session_state["dup_warnings"][dup_key] = dups
                                    st.session_state["nav_target"] = "Pending Transactions"
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Duplicate check failed: {e}")

                        if not st.session_state["dup_warnings"].get(dup_key) or approve_label == "Approve Anyway":
                            if not resolved_acct_id:
                                st.error("Account not found — select a valid account before approving.")
                            else:
                                try:
                                    ynab_id = yw.post_transaction(
                                        date=tx_date, amount_milliunits=amount_mu, payee=payee,
                                        account_id=resolved_acct_id, category_id=resolved_cat_id,
                                        memo=memo or None,
                                    )
                                    pending_db.approve_transaction(tx_id, ynab_id)
                                    st.session_state["dup_warnings"].pop(dup_key, None)
                                    st.success(f"Posted to YNAB (id: {ynab_id})")
                                    st.session_state["nav_target"] = "Pending Transactions"
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to post to YNAB: {e}")

                with btn_col2:
                    if st.button("Reject", key=f"reject_{tx_id}"):
                        pending_db.reject_transaction(tx_id)
                        st.session_state["dup_warnings"].pop(f"dups_{tx_id}", None)
                        st.session_state["nav_target"] = "Pending Transactions"
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

    # ---- Defaults and state init (runs before charts so charts see current values) ----
    _lm_start = last_month.date()
    _lm_end = (last_month + pd.offsets.MonthEnd(0)).date()

    if "sb_date_from" not in st.session_state:
        st.session_state["sb_date_from"] = _lm_start
        st.session_state["sb_date_to"]   = _lm_end
        st.session_state["sb_year"]      = str(last_month.year)
        st.session_state["sb_sg"]        = "All"
        st.session_state["_sb_year_prev"] = str(last_month.year)

    # Year selector change → update date range
    _sb_year = st.session_state.get("sb_year", str(last_month.year))
    if st.session_state.get("_sb_year_prev") != _sb_year:
        if _sb_year == "All":
            st.session_state["sb_date_from"] = df["date"].min().date()
            st.session_state["sb_date_to"]   = _lm_end
        else:
            _py = int(_sb_year)
            st.session_state["sb_date_from"] = date(_py, 1, 1)
            st.session_state["sb_date_to"]   = min(date(_py, 12, 31), _lm_end)
        st.session_state["_sb_year_prev"] = _sb_year

    _sb_sg       = st.session_state.get("sb_sg", "All")
    sb_date_from = st.session_state["sb_date_from"]
    sb_date_to   = st.session_state["sb_date_to"]

    # ---- Charts (shown first) ----
    _chart_key = f"{sb_date_from}_{sb_date_to}_{_sb_sg}"
    tab_sun, tab_tree, tab_ice = st.tabs(["Sunburst", "Treemap", "Icicle"])
    with tab_sun:
        st.plotly_chart(dh.make_hierarchy_chart(df_analytics, "sunburst", None, _sb_sg, sb_date_from, sb_date_to),
                        width='stretch', key=f"sun_{_chart_key}")
    with tab_tree:
        st.plotly_chart(dh.make_hierarchy_chart(df_analytics, "treemap", None, _sb_sg, sb_date_from, sb_date_to),
                        width='stretch', key=f"tree_{_chart_key}")
    with tab_ice:
        st.plotly_chart(dh.make_hierarchy_chart(df_analytics, "icicle", None, _sb_sg, sb_date_from, sb_date_to),
                        width='stretch', key=f"ice_{_chart_key}")

    # ---- Filters (below charts, above transactions) ----
    st.markdown("---")
    _sb_years = sorted(df["year"].dropna().unique().tolist(), reverse=True)
    _sb_year_opts = [str(y) for y in _sb_years] + ["All"]
    col_yr, col_sg, col_d1, col_d2 = st.columns(4)
    with col_yr:
        st.selectbox("Year", _sb_year_opts, key="sb_year")
    with col_sg:
        st.selectbox("Supergroup", ["All", "Living Expenses", "Goals", "Basic Expenses"], key="sb_sg")
    with col_d1:
        sb_date_from = st.date_input("From", value=_lm_start, key="sb_date_from")
    with col_d2:
        sb_date_to = st.date_input("To", value=_lm_end, key="sb_date_to")

    # ---- Transaction Drill-Down ----
    st.markdown("#### Transaction Drill-Down")
    st.caption("Each dropdown narrows the next.")

    df_base = df[df["category_supergroup"].isin(["Living Expenses", "Goals", "Basic Expenses"])].copy()
    df_base = df_base[(df_base["date"] >= pd.Timestamp(sb_date_from)) &
                      (df_base["date"] <= pd.Timestamp(sb_date_to))]
    if _sb_sg and _sb_sg != "All":
        df_base = df_base[df_base["category_supergroup"] == _sb_sg]

    if _sb_sg and _sb_sg != "All":
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

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Transactions", f"{len(df_tx):,}")
    col_m2.metric("Total Spend", f"${df_tx['amount'].sum():,.0f}")
    col_m3.metric("Avg per Transaction", f"${df_tx['amount'].mean():,.0f}" if len(df_tx) > 0 else "—")

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

elif selected_section == "Actual vs. Plan":
    st.subheader("Actual vs. Right Capital Plan")

    rc_goals = dh.load_rc_goals()
    _target_rows = {dh.LE_TARGET_ROW, dh.HC_TARGET_ROW}
    goal_names = [g for g in rc_goals["Goal"].tolist() if g not in _target_rows]
    _yr_cols = [c for c in rc_goals.columns if isinstance(c, int)]

    _cur_preset = st.session_state.get("gvp_preset", str(today.year))
    _prev_preset = st.session_state.get("_gvp_year_prev")
    _gvp_preset_changed = (_cur_preset != _prev_preset)

    # When preset changes to a named year, update dates immediately (before widget renders)
    if _gvp_preset_changed and _cur_preset != "Custom":
        _py = int(_cur_preset)
        st.session_state["gvp_date_from"] = date(_py, 1, 1)
        st.session_state["gvp_date_to"] = min(date(_py, 12, 31), today.date())

    # Auto-clear to Custom only when dates were manually edited, not when preset just changed
    if not _gvp_preset_changed and _cur_preset != "Custom":
        _cur_from = st.session_state.get("gvp_date_from", date(today.year, 1, 1))
        _cur_to   = st.session_state.get("gvp_date_to",   today.date())
        try:
            _chk_yr = int(_cur_preset)
            if _cur_from != date(_chk_yr, 1, 1) or _cur_to != min(date(_chk_yr, 12, 31), today.date()):
                st.session_state["gvp_preset"] = "Custom"
        except (ValueError, TypeError):
            pass

    st.session_state["_gvp_year_prev"] = _cur_preset

    col_pre, col_d1, col_d2 = st.columns([1, 1, 1])
    with col_pre:
        _preset_opts = [str(today.year)] + [str(y) for y in sorted(_yr_cols, reverse=True) if y != today.year] + ["Custom"]
        _preset = st.selectbox("Year Preset", _preset_opts, key="gvp_preset")

    with col_d1:
        gvp_from = st.date_input("From", value=date(today.year, 1, 1), key="gvp_date_from")
    with col_d2:
        gvp_to = st.date_input("To", value=today.date(), key="gvp_date_to")

    tab_compare, tab_monthly, tab_hc, tab_living, tab_edit = st.tabs(["Comparison Table", "Goals", "Health Care", "Living Expenses", "Edit Plan Amounts"])

    with tab_compare:
        compare = dh.build_goals_comparison(df, rc_goals, gvp_from, gvp_to)

        _hc_target_cmp = dh.load_hc_target(rc_goals, today.year)
        _hc_sum_cmp = dh.build_health_care_comparison(df, _hc_target_cmp, gvp_from, gvp_to)
        _hc_row = pd.DataFrame([{
            "Goal": "Health Care",
            "Plan": _hc_sum_cmp["plan"],
            "Actual": _hc_sum_cmp["total_actual"],
            "% of Plan": _hc_sum_cmp["pct_of_plan"],
            "Over/Under": _hc_sum_cmp["over_under"],
        }])

        _le_target_cmp = dh.load_living_target(rc_goals, today.year)
        _le_sum_cmp = dh.build_living_expenses_comparison(df, _le_target_cmp, gvp_from, gvp_to)
        _le_row = pd.DataFrame([{
            "Goal": "Living Expenses",
            "Plan": _le_sum_cmp["plan"],
            "Actual": _le_sum_cmp["total_actual"],
            "% of Plan": _le_sum_cmp["pct_of_plan"],
            "Over/Under": _le_sum_cmp["over_under"],
        }])

        compare = (
            pd.concat([compare, _hc_row, _le_row], ignore_index=True)
            .sort_values("Goal")
            .reset_index(drop=True)
        )

        st.caption(f"Plan prorated to selected period ({gvp_from} – {gvp_to}).")

        def _color_goal(val):
            if pd.isna(val):
                return ""
            return "color: red" if val > 0 else "color: green"

        def _color_pct_goal(val):
            if pd.isna(val):
                return ""
            return "color: red" if val > 1.0 else ("color: green" if val < 0.85 else "")

        st.dataframe(
            compare[["Goal", "Plan", "Actual", "% of Plan", "Over/Under"]].style
                .format({
                    "Plan": "${:,.0f}",
                    "Actual": "${:,.0f}",
                    "% of Plan": "{:.1%}",
                    "Over/Under": "${:+,.0f}",
                }, na_rep="-")
                .map(_color_goal, subset=["Over/Under"])
                .map(_color_pct_goal, subset=["% of Plan"]),
            hide_index=True,
            width='stretch',
        )

    with tab_monthly:
        col_goal, col_cumul = st.columns([2, 1])
        with col_goal:
            sel_goal = st.selectbox("Goal", goal_names, key="gvp_goal")
        with col_cumul:
            st.write("")
            st.write("")
            cumulative = st.checkbox("Cumulative", key="gvp_cumul")

        # Base transactions for this goal + date range (includes reimbursements/credits)
        _goal_group = sel_goal
        _df_goal_tx = df[
            (df["category_group"] == _goal_group) &
            (df["date"] >= pd.Timestamp(gvp_from)) &
            (df["date"] <= pd.Timestamp(gvp_to))
        ].copy()

        # Cascading filters — category narrows payee options
        col_cat, col_pay = st.columns(2)
        with col_cat:
            _cat_opts = sorted(_df_goal_tx["category_name"].dropna().unique().tolist())
            sel_cats = st.multiselect("Filter by Category", _cat_opts, key="gvp_cats")
        _df_cat_filtered = _df_goal_tx[_df_goal_tx["category_name"].isin(sel_cats)] if sel_cats else _df_goal_tx
        with col_pay:
            _pay_opts = sorted(_df_cat_filtered["payee_name"].dropna().unique().tolist())
            sel_pays = st.multiselect("Filter by Payee", _pay_opts, key="gvp_pays")

        fig_monthly = dh.make_goals_monthly_chart(
            df, rc_goals, sel_goal, gvp_from, gvp_to, cumulative,
            categories=sel_cats or None, payees=sel_pays or None,
        )
        st.plotly_chart(fig_monthly, width='stretch',
                        key=f"gvp_chart_{sel_goal}_{gvp_from}_{gvp_to}_{cumulative}_{sel_cats}_{sel_pays}")

        # Transaction detail — respect both filters
        _df_goal_tx = _df_cat_filtered.copy()
        if sel_pays:
            _df_goal_tx = _df_goal_tx[_df_goal_tx["payee_name"].isin(sel_pays)]
        _df_goal_tx = _df_goal_tx.sort_values("date", ascending=False)
        _net = _df_goal_tx["amount"].sum()
        _credits = _df_goal_tx[_df_goal_tx["amount"] < 0]["amount"].sum()
        _caption = f"{len(_df_goal_tx):,} transactions · net ${_net:,.0f}"
        if _credits < 0:
            _caption += f" (includes ${abs(_credits):,.0f} in reimbursements/credits)"
        st.caption(_caption)
        _tx_cols = ["date", "category_name", "payee_name", "amount"]
        if "memo" in _df_goal_tx.columns:
            _tx_cols.append("memo")
        _df_goal_tx["date"] = _df_goal_tx["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            _df_goal_tx[_tx_cols].style.format({"amount": "${:,.0f}"}),
            hide_index=True, width='stretch',
        )

    with tab_hc:
        _hc_target = dh.load_hc_target(rc_goals, today.year)
        _hc_comp = dh.build_health_care_comparison(df, _hc_target, gvp_from, gvp_to)

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Actual",      f"${_hc_comp['total_actual']:,.0f}")
        col_b.metric("Target",      f"${_hc_comp['plan']:,.0f}")
        col_c.metric("% of Target", f"{_hc_comp['pct_of_plan']:.1%}" if _hc_comp["pct_of_plan"] else "—")
        col_d.metric("Over/Under",  f"${_hc_comp['over_under']:+,.0f}")
        st.caption(f"Period: {gvp_from} – {gvp_to} · Monthly target: ${_hc_target:,}")

        _hc_all_cats = sorted(
            df[df["category_group"] == dh.HC_GROUP]["category_name"]
            .dropna().unique().tolist()
        )
        col_filt, col_cumul_col = st.columns([4, 1])
        with col_filt:
            sel_hc_cats = st.multiselect("Filter by Category", _hc_all_cats, key="hc_cats")
        with col_cumul_col:
            st.write("")
            _hc_cumul = st.checkbox("Cumulative", key="hc_cumul")

        st.plotly_chart(
            dh.make_health_care_monthly_chart(
                df, _hc_target, gvp_from, gvp_to,
                categories=sel_hc_cats or None, cumulative=_hc_cumul,
            ),
            width='stretch',
            key=f"hc_chart_{gvp_from}_{gvp_to}_{_hc_target}_{_hc_cumul}_{sel_hc_cats}",
        )

        st.markdown("**Spending by Category**")
        st.dataframe(
            _hc_comp["by_category"].style.format({
                "Actual": "${:,.0f}",
                "Avg Monthly": "${:,.0f}",
            }),
            hide_index=True, width='stretch',
        )

        st.markdown("**Month-to-Month Trend by Category**")
        st.caption(f"Based on data through {last_month.strftime('%B %Y')}.")
        _hc_trend = dh.prepare_summary(
            df_analytics[df_analytics["category_group"] == dh.HC_GROUP],
            windows, first_of_year, last_month, group_col="category_name",
        )
        st.dataframe(dh.style_summary(_hc_trend), hide_index=True, width='stretch')

        st.markdown("#### Transactions")
        _hc_tx = df[
            (df["category_group"] == dh.HC_GROUP) &
            (df["date"] >= pd.Timestamp(gvp_from)) &
            (df["date"] <= pd.Timestamp(gvp_to))
        ].copy()
        if sel_hc_cats:
            _hc_tx = _hc_tx[_hc_tx["category_name"].isin(sel_hc_cats)]

        col_hc_cat, col_hc_pay = st.columns(2)
        with col_hc_cat:
            _hc_tx_cat_opts = sorted(_hc_tx["category_name"].dropna().unique())
            sel_hc_tx_cat = st.selectbox("Filter by Category", ["All"] + list(_hc_tx_cat_opts), key="hc_tx_cat")
        _hc_tx = _hc_tx if sel_hc_tx_cat == "All" else _hc_tx[_hc_tx["category_name"] == sel_hc_tx_cat]
        with col_hc_pay:
            _hc_tx_pay_opts = sorted(_hc_tx["payee_name"].dropna().unique())
            sel_hc_tx_pay = st.selectbox("Filter by Payee", ["All"] + list(_hc_tx_pay_opts), key="hc_tx_pay")
        _hc_tx = _hc_tx if sel_hc_tx_pay == "All" else _hc_tx[_hc_tx["payee_name"] == sel_hc_tx_pay]

        _hc_tx = _hc_tx.sort_values("date", ascending=False)
        st.caption(f"{len(_hc_tx):,} transactions · ${_hc_tx['amount'].sum():,.0f} total")
        _hc_tx_cols = ["date", "category_name", "payee_name", "amount"]
        if "memo" in _hc_tx.columns:
            _hc_tx_cols.append("memo")
        _hc_tx_show = _hc_tx[_hc_tx_cols].copy()
        _hc_tx_show["date"] = _hc_tx_show["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            _hc_tx_show.style.format({"amount": "${:,.0f}"}),
            hide_index=True, width='stretch',
        )

    with tab_living:
        _le_target = dh.load_living_target(rc_goals, today.year)
        _le_comp = dh.build_living_expenses_comparison(df, _le_target, gvp_from, gvp_to)

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Actual",      f"${_le_comp['total_actual']:,.0f}")
        col_b.metric("Target",      f"${_le_comp['plan']:,.0f}")
        col_c.metric("% of Target", f"{_le_comp['pct_of_plan']:.1%}" if _le_comp["pct_of_plan"] else "—")
        col_d.metric("Over/Under",  f"${_le_comp['over_under']:+,.0f}")
        st.caption(f"Period: {gvp_from} – {gvp_to} · Monthly target: ${_le_target:,}")

        _le_all_groups = sorted(
            df[df["category_supergroup"] == "Living Expenses"]["category_group"]
            .dropna().unique().tolist()
        )
        col_filt, col_cumul_col = st.columns([4, 1])
        with col_filt:
            sel_le_groups = st.multiselect("Filter by Category Group", _le_all_groups, key="le_groups")
        with col_cumul_col:
            st.write("")
            _le_cumul = st.checkbox("Cumulative", key="le_cumul")

        st.plotly_chart(
            dh.make_living_expenses_monthly_chart(
                df, _le_target, gvp_from, gvp_to,
                groups=sel_le_groups or None, cumulative=_le_cumul,
            ),
            width='stretch',
            key=f"le_chart_{gvp_from}_{gvp_to}_{_le_target}_{_le_cumul}_{sel_le_groups}",
        )

        st.markdown("**Spending by Category Group**")
        st.dataframe(
            _le_comp["by_group"].style.format({
                "Actual": "${:,.0f}",
                "Avg Monthly": "${:,.0f}",
            }),
            hide_index=True, width='stretch',
        )

        st.markdown("**Month-to-Month Trend by Category Group**")
        st.caption(f"Based on data through {last_month.strftime('%B %Y')}.")
        _le_trend = dh.prepare_summary(
            df_analytics[df_analytics["category_supergroup"] == "Living Expenses"],
            windows, first_of_year, last_month, group_col="category_group",
        )
        st.dataframe(dh.style_summary(_le_trend), hide_index=True, width='stretch')

        st.markdown("#### Transactions")
        _le_tx = df[
            (df["category_supergroup"] == "Living Expenses") &
            (df["date"] >= pd.Timestamp(gvp_from)) &
            (df["date"] <= pd.Timestamp(gvp_to))
        ].copy()
        if sel_le_groups:
            _le_tx = _le_tx[_le_tx["category_group"].isin(sel_le_groups)]

        col_le_cat, col_le_pay = st.columns(2)
        with col_le_cat:
            _le_tx_cat_opts = sorted(_le_tx["category_name"].dropna().unique())
            sel_le_tx_cat = st.selectbox("Filter by Category", ["All"] + list(_le_tx_cat_opts), key="le_tx_cat")
        _le_tx = _le_tx if sel_le_tx_cat == "All" else _le_tx[_le_tx["category_name"] == sel_le_tx_cat]
        with col_le_pay:
            _le_tx_pay_opts = sorted(_le_tx["payee_name"].dropna().unique())
            sel_le_tx_pay = st.selectbox("Filter by Payee", ["All"] + list(_le_tx_pay_opts), key="le_tx_pay")
        _le_tx = _le_tx if sel_le_tx_pay == "All" else _le_tx[_le_tx["payee_name"] == sel_le_tx_pay]

        _le_tx = _le_tx.sort_values("date", ascending=False)
        st.caption(f"{len(_le_tx):,} transactions · ${_le_tx['amount'].sum():,.0f} total")
        _le_tx_cols = ["date", "category_group", "category_name", "payee_name", "amount"]
        if "memo" in _le_tx.columns:
            _le_tx_cols.append("memo")
        _le_tx_show = _le_tx[_le_tx_cols].copy()
        _le_tx_show["date"] = _le_tx_show["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            _le_tx_show.style.format({"amount": "${:,.0f}"}),
            hide_index=True, width='stretch',
        )

    with tab_edit:
        col_le_sect, col_hc_sect = st.columns(2)
        with col_le_sect:
            st.markdown("**Living Expenses Monthly Target**")
            _le_cur = dh.load_living_target(rc_goals, today.year)
            col_le_inp, col_le_btn = st.columns([3, 1])
            with col_le_inp:
                _le_edit_val = st.number_input(
                    "LE Target", value=_le_cur,
                    min_value=0, step=500, key="le_target_edit_input",
                    label_visibility="collapsed",
                )
            with col_le_btn:
                if st.button("Save", key="le_target_save"):
                    dh.save_living_target(_le_edit_val)
                    st.session_state["_le_target_saved"] = _le_edit_val
                    st.rerun()
            if (v := st.session_state.pop("_le_target_saved", None)) is not None:
                st.success(f"Saved ${v:,}/month.")

        with col_hc_sect:
            st.markdown("**Health Care Monthly Target**")
            _hc_cur = dh.load_hc_target(rc_goals, today.year)
            col_hc_inp, col_hc_btn = st.columns([3, 1])
            with col_hc_inp:
                _hc_edit_val = st.number_input(
                    "HC Target", value=_hc_cur,
                    min_value=0, step=100, key="hc_target_edit_input",
                    label_visibility="collapsed",
                )
            with col_hc_btn:
                if st.button("Save", key="hc_target_save"):
                    dh.save_hc_target(_hc_edit_val)
                    st.session_state["_hc_target_saved"] = _hc_edit_val
                    st.rerun()
            if (v := st.session_state.pop("_hc_target_saved", None)) is not None:
                st.success(f"Saved ${v:,}/month.")

        st.markdown("---")
        st.markdown("**Goal Plan Amounts**")
        st.caption("Edit annual plan amounts and click Save to update the file.")
        _rc_display = rc_goals[~rc_goals["Goal"].isin(_target_rows)].reset_index(drop=True).copy()
        _rc_edit = _rc_display[["Goal"]].copy()
        for c in _yr_cols:
            _rc_edit[str(c)] = _rc_display[c].apply(lambda x: f"{int(x):,}")
        _col_cfg = {str(c): st.column_config.TextColumn(str(c)) for c in _yr_cols}
        edited = st.data_editor(
            _rc_edit,
            hide_index=True,
            num_rows="fixed",
            width='stretch',
            column_config=_col_cfg,
            key="gvp_editor",
        )
        if st.button("Save Plan Amounts", key="gvp_save"):
            try:
                save_df = rc_goals.copy()
                for _, erow in edited.iterrows():
                    goal = erow["Goal"]
                    mask = save_df["Goal"] == goal
                    for c in _yr_cols:
                        val = int(str(erow[str(c)]).replace(",", "").replace("$", "").strip() or 0)
                        save_df.loc[mask, c] = val
                dh.save_rc_goals(save_df)
                st.success("Saved to right_capital_goals.xlsx.")
            except Exception as e:
                st.error(f"Save failed: {e}")

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
    _le_tab_charts, _le_tab_detail = st.tabs(["Charts", "Monthly Detail"])
    with _le_tab_charts:
        dh.render_chart_pair("Living Expenses Category Groups", key_prefix="living_expenses_group", charts=charts)
        dh.render_chart_pair("Household Expenses Category Group", key_prefix="living_expenses_household", charts=charts)
        dh.render_chart_pair("Other Discretionary Expenses Category Group", key_prefix="living_expenses_other_discretionary", charts=charts)
        dh.render_chart_pair("Other Non-Discretionary Expenses Category Group", key_prefix="living_expenses_other_non_discretionary", charts=charts)
        dh.render_chart_pair("Insurance Expenses Category Group", key_prefix="living_expenses_insurance", charts=charts)
        dh.render_chart_pair("Auto/Transport Expenses Category Group", key_prefix="living_expenses_auto_transport", charts=charts)
    with _le_tab_detail:
        st.subheader("🏠 Living Expenses Details")
        st.dataframe(df_cl_living_summary_styled)

elif selected_section == "Goals":
    _g_tab_charts, _g_tab_travel, _g_tab_summary = st.tabs(["Charts", "Travel Details", "Summary Table"])
    with _g_tab_charts:
        dh.render_chart_pair("Goals Category Groups", key_prefix="goal_group", charts=charts)
        dh.render_chart_pair("Chris on Payroll Goal Category Group", key_prefix="goal_chris_on_payroll", charts=charts)
        dh.render_chart_pair("Travel Goal Category Group", key_prefix="goal_travel", charts=charts)
        dh.render_chart_pair("Children - Non Academic Goal Category Group", key_prefix="goal_children_non_academic", charts=charts)
        dh.render_chart_pair("Home Improvement Goal Category Group", key_prefix="goal_home_improvement", charts=charts)
    with _g_tab_travel:
        st.subheader("✈️ Travel Spending Details")
        st.dataframe(df_cl_travel_summary_styled)
    with _g_tab_summary:
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
    st.subheader("Inflows")
    st.caption("Income transactions (Inflow: Ready to Assign), shown as positive amounts.")

    # Date range — same year-preset pattern used elsewhere
    _inf_default_from = date(today.year, 1, 1)
    _inf_default_to = today.date()
    _inf_yr_cols = sorted(df[df["category_name"] == "Inflow: Ready to Assign"]["year"]
                          .dropna().astype(int).unique().tolist(), reverse=True)

    _inf_cur_preset = st.session_state.get("inf_preset", str(today.year))
    _inf_prev = st.session_state.get("_inf_year_prev")
    _inf_preset_changed = (_inf_cur_preset != _inf_prev)

    if _inf_preset_changed and _inf_cur_preset != "Custom":
        _py = int(_inf_cur_preset)
        st.session_state["inf_date_from"] = date(_py, 1, 1)
        st.session_state["inf_date_to"] = min(date(_py, 12, 31), today.date())

    if not _inf_preset_changed and _inf_cur_preset != "Custom":
        _inf_cur_from = st.session_state.get("inf_date_from", _inf_default_from)
        _inf_cur_to   = st.session_state.get("inf_date_to",   _inf_default_to)
        try:
            _chk = int(_inf_cur_preset)
            if _inf_cur_from != date(_chk, 1, 1) or _inf_cur_to != min(date(_chk, 12, 31), today.date()):
                st.session_state["inf_preset"] = "Custom"
        except (ValueError, TypeError):
            pass

    st.session_state["_inf_year_prev"] = _inf_cur_preset

    col_pre, col_d1, col_d2 = st.columns([1, 1, 1])
    with col_pre:
        _inf_preset_opts = [str(today.year)] + [str(y) for y in _inf_yr_cols if y != today.year] + ["Custom"]
        _inf_preset = st.selectbox("Year Preset", _inf_preset_opts, key="inf_preset")

    with col_d1:
        inf_from = st.date_input("From", value=_inf_default_from, key="inf_date_from")
    with col_d2:
        inf_to = st.date_input("To", value=_inf_default_to, key="inf_date_to")

    # Build base filtered df (sign-flipped) to populate payee options
    _df_inf_base = df[
        (df["category_name"] == "Inflow: Ready to Assign") &
        (df["date"] >= pd.Timestamp(inf_from)) &
        (df["date"] <= pd.Timestamp(inf_to))
    ].copy()
    _df_inf_base["amount"] = (_df_inf_base["amount"] * -1).round(2)
    _df_inf_base = _df_inf_base[_df_inf_base["amount"] > 0]

    _inf_payee_opts = sorted(_df_inf_base["payee_name"].dropna().unique().tolist())
    sel_inf_pays = st.multiselect("Filter by Payee", _inf_payee_opts, key="inf_payees")

    # Chart
    st.plotly_chart(
        dh.make_inflows_chart(df, inf_from, inf_to, payees=sel_inf_pays or None),
        width='stretch', key=f"inf_chart_{inf_from}_{inf_to}_{sel_inf_pays}",
    )

    # Transaction table
    _df_inf = _df_inf_base.copy()
    if sel_inf_pays:
        _df_inf = _df_inf[_df_inf["payee_name"].isin(sel_inf_pays)]
    _df_inf = _df_inf.sort_values("date", ascending=False)
    st.caption(f"{len(_df_inf):,} transactions · ${_df_inf['amount'].sum():,.0f} total")
    _inf_tx_cols = ["date", "payee_name", "amount"]
    if "memo" in _df_inf.columns:
        _inf_tx_cols.append("memo")
    _df_inf = _df_inf[_inf_tx_cols].copy()
    _df_inf["date"] = _df_inf["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(
        _df_inf.style.format({"amount": "${:,.0f}"}),
        hide_index=True, width='stretch',
    )

elif selected_section == "Other Expenses":
    st.subheader("Other Expenses")
    st.caption("Transactions in categories not tracked by Right Capital: Taxes, Flo's Expenses, Pact Work Expenses, Abt Expenses, and Other.")

    # Date range — same year-preset pattern used in Inflows and Actual vs. Plan
    _oe_default_from = date(today.year, 1, 1)
    _oe_default_to = today.date()
    _oe_yr_cols = sorted(
        df[df["category_group"] == "Other - Non Right Capital"]["year"]
        .dropna().astype(int).unique().tolist(), reverse=True
    )

    _oe_cur_preset = st.session_state.get("oe_preset", str(today.year))
    _oe_prev = st.session_state.get("_oe_year_prev")
    _oe_preset_changed = (_oe_cur_preset != _oe_prev)

    if _oe_preset_changed and _oe_cur_preset != "Custom":
        _py = int(_oe_cur_preset)
        st.session_state["oe_date_from"] = date(_py, 1, 1)
        st.session_state["oe_date_to"] = min(date(_py, 12, 31), today.date())

    if not _oe_preset_changed and _oe_cur_preset != "Custom":
        _oe_cur_from = st.session_state.get("oe_date_from", _oe_default_from)
        _oe_cur_to   = st.session_state.get("oe_date_to",   _oe_default_to)
        try:
            _chk = int(_oe_cur_preset)
            if _oe_cur_from != date(_chk, 1, 1) or _oe_cur_to != min(date(_chk, 12, 31), today.date()):
                st.session_state["oe_preset"] = "Custom"
        except (ValueError, TypeError):
            pass

    st.session_state["_oe_year_prev"] = _oe_cur_preset

    col_pre, col_d1, col_d2 = st.columns([1, 1, 1])
    with col_pre:
        _oe_preset_opts = [str(today.year)] + [str(y) for y in _oe_yr_cols if y != today.year] + ["Custom"]
        _oe_preset = st.selectbox("Year Preset", _oe_preset_opts, key="oe_preset")
    with col_d1:
        oe_from = st.date_input("From", value=_oe_default_from, key="oe_date_from")
    with col_d2:
        oe_to = st.date_input("To", value=_oe_default_to, key="oe_date_to")

    # Chart
    st.plotly_chart(
        dh.make_other_expenses_chart(df, oe_from, oe_to),
        width='stretch', key=f"oe_chart_{oe_from}_{oe_to}",
    )

    # Transaction drill-down
    st.markdown("#### Transactions")
    _df_oe = df[
        (df["category_group"] == "Other - Non Right Capital") &
        (df["date"] >= pd.Timestamp(oe_from)) &
        (df["date"] <= pd.Timestamp(oe_to))
    ].copy()

    col_cat, col_pay = st.columns(2)
    with col_cat:
        _oe_cat_opts = sorted(_df_oe["category_name"].dropna().unique().tolist())
        sel_oe_cat = st.selectbox("Filter by Category", ["All"] + _oe_cat_opts, key="oe_drill_cat")
    _df_oe_cat = _df_oe if sel_oe_cat == "All" else _df_oe[_df_oe["category_name"] == sel_oe_cat]
    with col_pay:
        _oe_pay_opts = sorted(_df_oe_cat["payee_name"].dropna().unique().tolist())
        sel_oe_pay = st.selectbox("Filter by Payee", ["All"] + _oe_pay_opts, key="oe_drill_pay")
    _df_oe_tx = _df_oe_cat if sel_oe_pay == "All" else _df_oe_cat[_df_oe_cat["payee_name"] == sel_oe_pay]
    _df_oe_tx = _df_oe_tx.sort_values("date", ascending=False)

    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Transactions", f"{len(_df_oe_tx):,}")
    col_m2.metric("Total", f"${_df_oe_tx['amount'].sum():,.0f}")

    _oe_tx_cols = ["date", "category_name", "payee_name", "amount"]
    if "memo" in _df_oe_tx.columns:
        _oe_tx_cols.append("memo")
    _df_oe_tx = _df_oe_tx[_oe_tx_cols].copy()
    _df_oe_tx["date"] = _df_oe_tx["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(
        _df_oe_tx.style.format({"amount": "${:,.0f}"}),
        hide_index=True, width='stretch',
    )

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
| **Inflows** | Income and transfer inflows over time. |
| **Other Expenses** | Transactions outside the Right Capital plan: Taxes, Flo's, Pact, Abt, and Other. |
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


