import calendar
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import streamlit as st

HIGHLIGHT_THRESHOLD = 0.15  # pct change cell turns red/green in summary tables
ALERT_THRESHOLD = 0.10      # category appears in Spending Alerts section

def sort_and_cast(df, group_col, time_col, ascending_order=True):
    """
    Sorts a DataFrame by group size and time, and casts the group column as ordered categorical.
    
    Parameters:
        df (pd.DataFrame): The input DataFrame.
        group_col (str): The column to group and rank by (e.g., 'category_group').
        time_col (str): The time column to sort within groups (e.g., 'month').
        ascending_order (bool): Whether to sort group totals ascending (bottom-up stacking).
    
    Returns:
        pd.DataFrame: A sorted and cast DataFrame.
    """
    order = (
        df.groupby(group_col)[ "amount" ]
        .sum()
        .sort_values(ascending=ascending_order)
        .index.tolist()
    )

    df[group_col] = pd.Categorical(df[group_col], categories=order, ordered=True)

    return df.sort_values(by=[group_col, time_col], ascending=[not ascending_order, True]).copy()

def keys_exist(d, *keys):
    for key in keys:
        if not isinstance(d, dict) or key not in d:
            return False
        d = d[key]
    return True

def group_sum(df, group_cols):
    """
    Groups a DataFrame by specified columns and sums the 'amount' column.
    """
    return df.groupby(group_cols, as_index=False)["amount"].sum()

def filter_group(df, col, values=None, startswith=None):
    """
    Filters a DataFrame based on exact values or prefix match in a column.
    """
    if values:
        return df[df[col].isin(values)].copy()
    if startswith:
        return df[df[col].str.startswith(startswith, na=False)].copy()
    return df.copy()

def make_chart(df, chart_type, x, y, color, title, cumulative=False, force_year_ticks=False):
    if chart_type == "bar":
        fig = px.bar(df, x=x, y=y, color=color, title=title)
    elif chart_type == "line":
        fig = px.line(df, x=x, y=y, color=color, title=title)
    elif chart_type == "area":
        fig = px.area(df, x=x, y=y, color=color, title=title)
    else:
        raise ValueError(f"Unsupported chart_type: {chart_type}")

    if cumulative and chart_type == "bar":
        fig.update_traces(marker_line_width=0)

    if force_year_ticks and x in df.columns:
        x_series = df[x]
        if pd.api.types.is_integer_dtype(x_series) and not x_series.isna().all():
            tick_start = x_series.min()
            if not np.isnan(tick_start):
                fig.update_layout(
                    xaxis=dict(
                        tickmode="linear",
                        tick0=int(tick_start),
                        dtick=1
                    )
                )
    return fig

def render_chart_pair(title, chart1=None, chart2=None, key_prefix=None, charts=None):
    if chart1 and chart2:
        c1, c2 = chart1, chart2
    elif key_prefix and charts:
        c1 = charts[f"{key_prefix}_line"]
        c2 = charts[f"{key_prefix}_bar"]
    else:
        raise ValueError("Must provide either chart1/chart2 or key_prefix/charts")

    st.subheader(title)
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(c1, width='stretch')
        with col2:
            st.plotly_chart(c2, width='stretch')
        st.markdown("<hr style='border:2px solid #bbb'>", unsafe_allow_html=True)

# compute monthly average spend over a window
def monthly_avg(df_cat, start_date, end_date):
    df_window = df_cat[(df_cat["date"] >= start_date) & (df_cat["date"] <= end_date)].copy()
    df_window["month"] = df_window["date"].dt.to_period("M").dt.to_timestamp()

    # Create full month range
    all_months = pd.date_range(start=start_date, end=end_date, freq="MS")

    # Group and reindex to include zero months
    monthly_totals = df_window.groupby("month")["amount"].sum().reindex(all_months, fill_value=0)

    return monthly_totals.mean()

# function to aggregate by category name
def summarize_recent_trends(df, windows, ytd_start, last_month, group_col=None):
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    last_month_last_day = last_month + pd.offsets.MonthEnd(0)
    summaries = []

    if group_col is not None:
        for cat in df[group_col].unique():
            df_cat = df[df[group_col] == cat]

            recent = df_cat[df_cat["month"] == last_month]["amount"].sum()
            avg_3m = monthly_avg(df_cat, windows["3M"], last_month_last_day)
            avg_6m = monthly_avg(df_cat, windows["6M"], last_month_last_day)
            avg_12m = monthly_avg(df_cat, windows["12M"], last_month_last_day)

            pct_ch_3m = float((recent - avg_3m))/float(avg_3m) if avg_3m else None
            pct_ch_6m = float((recent - avg_6m))/float(avg_6m) if avg_6m else None
            pct_ch_12m = float((recent - avg_12m))/float(avg_12m) if avg_12m else None

            ytd = df_cat[df_cat["date"] >= ytd_start]["amount"].sum()

            summaries.append({
                "category_name": cat,
                "recent_month": recent,
                "avg_3m": avg_3m,
                "avg_6m": avg_6m,
                "avg_12m": avg_12m,
                "ytd": ytd,
                "pct_ch_3m": pct_ch_3m,
                "pct_ch_6m": pct_ch_6m,
                "pct_ch_12m": pct_ch_12m
            })
    else:
        recent = df[df["month"] == last_month]["amount"].sum()
        avg_3m = monthly_avg(df, windows["3M"], last_month_last_day)
        avg_6m = monthly_avg(df, windows["6M"], last_month_last_day)
        avg_12m = monthly_avg(df, windows["12M"], last_month_last_day)

        pct_ch_3m = float((recent - avg_3m))/float(avg_3m) if avg_3m else None
        pct_ch_6m = float((recent - avg_6m))/float(avg_6m) if avg_6m else None
        pct_ch_12m = float((recent - avg_12m))/float(avg_12m) if avg_12m else None

        ytd = df[df["date"] >= ytd_start]["amount"].sum()

        summaries.append({
            "category_name": "All Categories",
            "recent_month": recent,
            "avg_3m": avg_3m,
            "avg_6m": avg_6m,
            "avg_12m": avg_12m,
            "ytd": ytd,
            "pct_ch_3m": pct_ch_3m,
            "pct_ch_6m": pct_ch_6m,
            "pct_ch_12m": pct_ch_12m
        })

    return pd.DataFrame(summaries)


def prepare_summary(df, windows, first_of_year, last_month, group_col=None):
    summary = summarize_recent_trends(df, windows, first_of_year, last_month, group_col)
    summary = summary[summary["ytd"] != 0].sort_values(by="pct_ch_3m", ascending=False, na_position="last")
    summary = summary.round({
        "recent_month": 0, "avg_3m": 0, "avg_6m": 0, "avg_12m": 0, "ytd": 0
    }).reset_index(drop=True)
    return summary

def _color_pct(val):
    try:
        if pd.isna(val):
            return ''
    except (TypeError, ValueError):
        return ''
    if val > HIGHLIGHT_THRESHOLD:
        return 'background-color: #ffcccc'
    if val < -HIGHLIGHT_THRESHOLD:
        return 'background-color: #ccffcc'
    return ''

def style_summary(df):
    return (
        df.style
        .format({
            "recent_month": "{:,.0f}",
            "avg_3m": "{:,.0f}",
            "pct_ch_3m": "{:.1%}",
            "avg_6m": "{:,.0f}",
            "pct_ch_6m": "{:.1%}",
            "avg_12m": "{:,.0f}",
            "pct_ch_12m": "{:.1%}",
            "ytd": "{:,.0f}"
        }, na_rep="-")
        .map(_color_pct, subset=["pct_ch_3m", "pct_ch_6m", "pct_ch_12m"])
        .set_properties(**{"font-size": "16px", "font-weight": "bold"})
        .set_table_styles([
            {'selector': 'th', 'props': [('min-width', '60px')]},
            {'selector': 'td', 'props': [('min-width', '60px')]}
        ])
    )

@st.cache_data
def make_hierarchy_chart(df, chart_type="sunburst", year=None, supergroup=None,
                         date_from=None, date_to=None):
    """Build a hierarchy chart (sunburst, treemap, or icicle) of spending.

    Args:
        df: raw transactions DataFrame
        chart_type: "sunburst", "treemap", or "icicle"
        year: year string filter, or None / "All" for all years (ignored when date_from/to set)
        supergroup: one of the supergroup names to filter, or None / "All" for all
        date_from: optional date lower bound (overrides year when provided)
        date_to: optional date upper bound (overrides year when provided)
    """
    df_sb = df[df["category_supergroup"].isin(["Living Expenses", "Goals", "Basic Expenses"])].copy()

    if date_from and date_to:
        df_sb = df_sb[(df_sb["date"] >= pd.Timestamp(date_from)) &
                      (df_sb["date"] <= pd.Timestamp(date_to))]
        date_label = f"{pd.Timestamp(date_from).strftime('%b %d %Y')} – {pd.Timestamp(date_to).strftime('%b %d %Y')}"
    elif year and year != "All":
        df_sb = df_sb[df_sb["year"] == year]
        date_label = str(year)
    else:
        date_label = "All Years"

    if supergroup and supergroup != "All":
        df_sb = df_sb[df_sb["category_supergroup"] == supergroup]

    df_sb = df_sb[df_sb["amount"] > 0]
    df_sb["payee_name"] = df_sb["payee_name"].fillna("Unknown")

    # When filtered to one supergroup, drop it from the path so Group is the root
    if supergroup and supergroup != "All":
        path = ["category_group", "category_name", "payee_name"]
    else:
        path = ["category_supergroup", "category_group", "category_name", "payee_name"]

    df_sb = df_sb.groupby(path, as_index=False)["amount"].sum()

    sg_label = supergroup if supergroup and supergroup != "All" else None
    title_parts = [p for p in [sg_label, date_label] if p]
    title = "Spending Breakdown" + (" — " + " — ".join(str(p) for p in title_parts) if title_parts else "")

    # Show label, formatted dollar amount, and % of parent on each segment
    text_template = "<b>%{label}</b><br>$%{value:,.0f}<br>%{percentParent:.1%} of parent"

    if chart_type == "treemap":
        fig = px.treemap(df_sb, path=path, values="amount", title=title)
        fig.update_traces(texttemplate=text_template, textinfo="text")
    elif chart_type == "icicle":
        fig = px.icicle(df_sb, path=path, values="amount", title=title)
        fig.update_traces(texttemplate=text_template, textinfo="text")
    else:  # sunburst (default)
        fig = px.sunburst(df_sb, path=path, values="amount", title=title)
        fig.update_traces(texttemplate=text_template, textinfo="text")

    fig.update_layout(height=700)
    return fig

def payee_name_report(df, top_n=75):
    df_exp = df[df["amount"] > 0].copy()
    df_exp["payee_name"] = df_exp["payee_name"].fillna("Unknown")

    # Top payees by transaction count
    top_payees = (
        df_exp.groupby("payee_name")
        .agg(transactions=("amount", "count"), total_spent=("amount", "sum"))
        .reset_index()
        .sort_values("transactions", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    # Name variants: normalize to first 10 chars (lowercase, alphanumeric only)
    df_exp["_prefix"] = (
        df_exp["payee_name"]
        .str.lower()
        .str.replace(r"[^a-z0-9 ]", " ", regex=True)
        .str.strip()
        .str[:10]
    )
    variants = (
        df_exp.groupby("_prefix")
        .agg(
            variants=("payee_name", lambda x: sorted(x.unique().tolist())),
            transactions=("amount", "count"),
        )
        .reset_index()
    )
    variants["variant_count"] = variants["variants"].apply(len)
    variants = (
        variants[variants["variant_count"] > 1]
        .sort_values(["variant_count", "transactions"], ascending=[False, False])
        .reset_index(drop=True)
        [["variants", "variant_count", "transactions"]]
    )

    return top_payees, variants

@st.cache_data
def make_heatmap(df, supergroup=None, year=None):
    """Monthly spend heatmap, color normalized per row (vs each category's own mean).

    Each cell's color shows how that month compares to that category's average,
    so small and large categories are both visible. Hover shows actual $ amounts.
    """
    df_h = df[df["category_supergroup"].isin(["Living Expenses", "Goals", "Basic Expenses"])].copy()
    if supergroup and supergroup != "All":
        df_h = df_h[df_h["category_supergroup"] == supergroup]
    if year and year != "All":
        df_h = df_h[df_h["year"] == year]
    df_h = df_h[df_h["amount"] > 0]

    df_h["month"] = df_h["date"].dt.to_period("M").dt.to_timestamp()
    grouped = df_h.groupby(["category_group", "month"])["amount"].sum().reset_index()
    pivot = grouped.pivot(index="category_group", columns="month", values="amount").fillna(0)
    pivot.columns = [col.strftime("%Y-%m") for col in pivot.columns]
    pivot = pivot.sort_index()

    year_str = str(year) if year and year != "All" else None
    parts = [p for p in [supergroup if supergroup != "All" else None, year_str] if p]
    title = "Monthly Spend Heatmap" + (f" — {', '.join(parts)}" if parts else " — All")

    # Normalize each row to its mean so all categories show relative variation equally
    row_means = pivot.mean(axis=1).replace(0, 1)
    pivot_norm = pivot.div(row_means, axis=0)

    customdata_fmt = np.array([[f"${v:,.0f}" for v in row] for row in pivot.values])

    fig = go.Figure(data=go.Heatmap(
        z=pivot_norm.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        customdata=customdata_fmt,
        hovertemplate="%{y}<br>%{x}<br>%{customdata}<extra></extra>",
        colorscale="RdYlGn_r",
        zmid=1.0,
        colorbar=dict(
            title="vs avg",
            tickvals=[0, 0.5, 1.0, 1.5, 2.0, 3.0],
            ticktext=["0×", "0.5×", "1× (avg)", "1.5×", "2×", "3×"],
        ),
    ))
    fig.update_xaxes(tickangle=45, title="Month")
    fig.update_yaxes(title="Category Group", autorange="reversed")
    fig.update_layout(title=title, height=max(400, len(pivot) * 28 + 100))
    return fig


@st.cache_data
def make_bubble_chart(df, windows, first_of_year, last_month):
    """Bubble chart: X=12m avg spend, Y=recent % change vs 3m avg, size=YTD, color=supergroup.

    High-spend + high-deviation categories appear in the top-right and jump out immediately.
    """
    df_main = df[df["category_supergroup"].isin(["Living Expenses", "Goals", "Basic Expenses"])].copy()
    supergroup_map = (
        df_main.groupby("category_group")["category_supergroup"]
        .agg(lambda x: x.mode()[0])
        .to_dict()
    )

    summary = prepare_summary(df_main, windows, first_of_year, last_month, group_col="category_group")
    summary["supergroup"] = summary["category_name"].map(supergroup_map)
    summary = summary[(summary["avg_12m"] > 0) & (summary["ytd"] > 0) & summary["pct_ch_3m"].notna()].copy()

    fig = px.scatter(
        summary,
        x="avg_12m",
        y="pct_ch_3m",
        size="ytd",
        color="supergroup",
        hover_name="category_name",
        hover_data={"avg_12m": ":,.0f", "pct_ch_3m": ":.1%", "ytd": ":,.0f", "supergroup": False},
        labels={
            "avg_12m": "12-Month Avg Monthly Spend ($)",
            "pct_ch_3m": "Recent Change vs 3M Avg",
            "ytd": "YTD Total ($)",
            "supergroup": "Supergroup",
        },
        title="Spending Deviation — Size = YTD Total",
        size_max=60,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="No change")
    fig.add_hline(y=ALERT_THRESHOLD, line_dash="dot", line_color="red",
                  annotation_text="Alert threshold", annotation_position="top right")
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(height=600)
    return fig


def apply_demo_scramble(df):
    """Scramble amounts and payee names for demo/presentation mode.

    Each category gets a stable random scale factor (0.55–1.45×) derived from
    a fixed seed, so numbers stay consistent while you interact with the
    dashboard.  Payee names are replaced with generic "Vendor NNN" labels.
    """
    df = df.copy()
    rng = np.random.default_rng(seed=42)
    categories = sorted(df["category_name"].dropna().unique())
    scale = {cat: rng.uniform(0.55, 1.45) for cat in categories}
    df["amount"] = df.apply(
        lambda r: r["amount"] * scale.get(r["category_name"], 1.0), axis=1
    )
    payees = sorted(df["payee_name"].dropna().unique())
    payee_map = {p: f"Vendor {i + 1:03d}" for i, p in enumerate(payees)}
    df["payee_name"] = df["payee_name"].map(payee_map).fillna("Unknown")
    return df


def make_inflows_chart(df: pd.DataFrame, date_from, date_to, top_n: int = 8,
                       payees: list | None = None):
    """
    Stacked monthly bar chart of income (Inflow: Ready to Assign), amounts sign-flipped to positive.
    When payees is provided, shows only those payees (no top-N / Other grouping).
    Otherwise, top N payees shown individually; remainder grouped as 'Other'.
    """
    date_from = pd.Timestamp(date_from)
    date_to = pd.Timestamp(date_to)

    dfi = df[
        (df["category_name"] == "Inflow: Ready to Assign") &
        (df["date"] >= date_from) &
        (df["date"] <= date_to)
    ].copy()
    dfi["amount"] = dfi["amount"] * -1          # flip to positive
    dfi = dfi[dfi["amount"] > 0]                # drop corrections/zero rows
    dfi["month"] = dfi["date"].dt.to_period("M").astype(str)

    if payees:
        dfi = dfi[dfi["payee_name"].isin(payees)]
        color_col = "payee_name"
        monthly = dfi.groupby(["month", color_col], as_index=False)["amount"].sum()
    else:
        top = (
            dfi.groupby("payee_name")["amount"].sum()
            .nlargest(top_n).index.tolist()
        )
        dfi["payee_label"] = dfi["payee_name"].where(dfi["payee_name"].isin(top), other="Other")
        color_col = "payee_label"
        monthly = dfi.groupby(["month", color_col], as_index=False)["amount"].sum()

    fig = px.bar(
        monthly,
        x="month", y="amount", color=color_col,
        title="Monthly Inflows by Source",
        labels={"amount": "Amount ($)", "month": "Month",
                "payee_label": "Source", "payee_name": "Payee"},
    )
    fig.update_layout(
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        xaxis_tickangle=45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=450,
        margin=dict(t=100),
    )
    return fig


RC_GOALS_PATH = "right_capital_goals.xlsx"


def load_rc_goals() -> pd.DataFrame:
    """Load Right Capital goal amounts from xlsx. Returns wide DataFrame with 'Goal' + year columns."""
    return pd.read_excel(RC_GOALS_PATH)


def save_rc_goals(df: pd.DataFrame) -> None:
    """Save edited Right Capital goals back to xlsx."""
    df.to_excel(RC_GOALS_PATH, index=False)


def _prorate_plan(rc_goals: pd.DataFrame, goal_name: str, date_from: pd.Timestamp, date_to: pd.Timestamp) -> float:
    """Prorate annual RC plan amounts to the selected date range, handling multi-year spans."""
    import calendar
    year_cols = [c for c in rc_goals.columns if isinstance(c, int)]
    plan_rows = rc_goals.set_index("Goal")
    if goal_name not in plan_rows.index:
        return 0.0
    total = 0.0
    for year in range(date_from.year, date_to.year + 1):
        if year not in year_cols:
            continue
        annual = float(plan_rows.loc[goal_name, year])
        yr_start = max(date_from, pd.Timestamp(year, 1, 1))
        yr_end = min(date_to, pd.Timestamp(year, 12, 31))
        if yr_start > yr_end:
            continue
        days_period = (yr_end - yr_start).days + 1
        days_year = 366 if calendar.isleap(year) else 365
        total += annual * days_period / days_year
    return total


def build_goals_comparison(df_ynab: pd.DataFrame, rc_goals: pd.DataFrame,
                           date_from, date_to) -> pd.DataFrame:
    """
    Compare actual Goals spending vs prorated Right Capital plan for a date range.

    Returns DataFrame: Goal, Plan (prorated), Actual, % of Plan, Over/Under
    """
    date_from = pd.Timestamp(date_from)
    date_to = pd.Timestamp(date_to)

    actuals = df_ynab[
        (df_ynab["category_supergroup"] == "Goals") &
        (df_ynab["date"] >= date_from) &
        (df_ynab["date"] <= date_to)
    ].copy()
    actuals["goal_name"] = actuals["category_group"]
    actuals = actuals.groupby("goal_name", as_index=False)["amount"].sum().rename(columns={"amount": "Actual"})

    all_goals = [g for g in rc_goals["Goal"].tolist() if g != LE_TARGET_ROW]
    plan_df = pd.DataFrame({
        "goal_name": all_goals,
        "Plan": [_prorate_plan(rc_goals, g, date_from, date_to) for g in all_goals],
    })

    compare = plan_df.merge(actuals, on="goal_name", how="outer").fillna(0)
    compare = compare.rename(columns={"goal_name": "Goal"})
    compare["Plan"] = compare["Plan"].astype(float)
    compare["Actual"] = compare["Actual"].astype(float)
    compare["% of Plan"] = compare.apply(lambda r: r["Actual"] / r["Plan"] if r["Plan"] > 0 else None, axis=1)
    compare["Over/Under"] = compare["Actual"] - compare["Plan"]
    return compare.sort_values("Goal").reset_index(drop=True)


def make_goals_monthly_chart(df_ynab: pd.DataFrame, rc_goals: pd.DataFrame,
                              goal_name: str, date_from, date_to, cumulative: bool = False,
                              categories: list | None = None, payees: list | None = None):
    """
    Monthly actual spend vs prorated monthly plan for a single goal.
    cumulative=True switches to running totals with an area fill.
    categories/payees: optional lists to filter transactions (plan line always shows full goal).
    """
    date_from = pd.Timestamp(date_from)
    date_to = pd.Timestamp(date_to)
    goal_group = goal_name

    actuals = df_ynab[
        (df_ynab["category_group"] == goal_group) &
        (df_ynab["date"] >= date_from) &
        (df_ynab["date"] <= date_to)
    ].copy()
    if categories:
        actuals = actuals[actuals["category_name"].isin(categories)]
    if payees:
        actuals = actuals[actuals["payee_name"].isin(payees)]
    actuals["month"] = actuals["date"].dt.to_period("M")
    monthly_actual = actuals.groupby("month")["amount"].sum()

    all_months = pd.period_range(date_from.to_period("M"), date_to.to_period("M"), freq="M")
    monthly_actual = monthly_actual.reindex(all_months, fill_value=0)

    # Monthly plan = annual_plan[year] / 12 for each month
    plan_rows = rc_goals.set_index("Goal")
    year_cols = [c for c in rc_goals.columns if isinstance(c, int)]
    monthly_plan = [
        float(plan_rows.loc[goal_name, m.year]) / 12
        if goal_name in plan_rows.index and m.year in year_cols else 0.0
        for m in all_months
    ]

    mdf = pd.DataFrame({
        "month": [str(m) for m in all_months],
        "Actual": monthly_actual.values,
        "Plan": monthly_plan,
    })
    mdf["Cum Actual"] = mdf["Actual"].cumsum()
    mdf["Cum Plan"] = mdf["Plan"].cumsum()

    fig = go.Figure()
    if cumulative:
        fig.add_trace(go.Scatter(
            x=mdf["month"], y=mdf["Cum Plan"],
            name="Cumulative Plan", mode="lines",
            line=dict(dash="dash", color="orange", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=mdf["month"], y=mdf["Cum Actual"],
            name="Cumulative Actual", mode="lines",
            fill="tozeroy", line=dict(color="steelblue", width=2),
        ))
        title = f"{goal_name} — Cumulative Actual vs. Plan"
    else:
        fig.add_trace(go.Bar(
            x=mdf["month"], y=mdf["Actual"],
            name="Monthly Actual", marker_color="steelblue",
        ))
        fig.add_trace(go.Scatter(
            x=mdf["month"], y=mdf["Plan"],
            name="Monthly Plan (full goal)", mode="lines+markers",
            line=dict(dash="dash", color="orange", width=2),
        ))
        title = f"{goal_name} — Monthly Actual vs. Plan"

    filter_parts = []
    if categories:
        filter_parts.append(f"Categories: {', '.join(categories)}")
    if payees:
        filter_parts.append(f"Payees: {', '.join(payees)}")
    if filter_parts:
        title += f"<br><sup>Filtered — {' · '.join(filter_parts)} · Plan line shows full goal</sup>"

    fig.update_layout(
        title=title,
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=420,
        margin=dict(t=80),
    )
    return fig


LE_TARGET_ROW = "Living Expenses Target"
HC_TARGET_ROW = "Health Care Target"


def load_living_target(rc_goals: pd.DataFrame, year: int | None = None) -> int:
    """Read monthly Living Expenses target from a dedicated row in rc_goals xlsx."""
    mask = rc_goals["Goal"] == LE_TARGET_ROW
    if not mask.any():
        return 8000
    row = rc_goals[mask].iloc[0]
    yr_cols = [c for c in rc_goals.columns if isinstance(c, int)]
    if not yr_cols:
        return 8000
    col = year if (year and year in yr_cols) else max(yr_cols)
    return int(row[col])


def save_living_target(amount: int) -> None:
    """Update the Living Expenses Target row in rc_goals xlsx (adds it if missing)."""
    df = pd.read_excel(RC_GOALS_PATH)
    yr_cols = [c for c in df.columns if isinstance(c, int)]
    mask = df["Goal"] == LE_TARGET_ROW
    if mask.any():
        for c in yr_cols:
            df.loc[mask, c] = amount
    else:
        new_row = {"Goal": LE_TARGET_ROW, **{c: amount for c in yr_cols}}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(RC_GOALS_PATH, index=False)


def load_hc_target(rc_goals: pd.DataFrame, year: int | None = None) -> int:
    """Read monthly Health Care target from a dedicated row in rc_goals xlsx."""
    mask = rc_goals["Goal"] == HC_TARGET_ROW
    if not mask.any():
        return 0
    row = rc_goals[mask].iloc[0]
    yr_cols = [c for c in rc_goals.columns if isinstance(c, int)]
    if not yr_cols:
        return 0
    col = year if (year and year in yr_cols) else max(yr_cols)
    return int(row[col])


def save_hc_target(amount: int) -> None:
    """Update the Health Care Target row in rc_goals xlsx (adds it if missing)."""
    df = pd.read_excel(RC_GOALS_PATH)
    yr_cols = [c for c in df.columns if isinstance(c, int)]
    mask = df["Goal"] == HC_TARGET_ROW
    if mask.any():
        for c in yr_cols:
            df.loc[mask, c] = amount
    else:
        new_row = {"Goal": HC_TARGET_ROW, **{c: amount for c in yr_cols}}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(RC_GOALS_PATH, index=False)


HC_GROUP = "Basic Expenses - Health Care"


def build_health_care_comparison(df_ynab: pd.DataFrame, monthly_target: int,
                                  date_from, date_to) -> dict:
    """Actual Health Care spending vs. prorated monthly target for a date range."""
    date_from = pd.Timestamp(date_from)
    date_to = pd.Timestamp(date_to)

    actuals = df_ynab[
        (df_ynab["category_group"] == HC_GROUP) &
        (df_ynab["date"] >= date_from) &
        (df_ynab["date"] <= date_to)
    ].copy()

    total = actuals["amount"].sum()
    n_months = _count_months(date_from, date_to)
    plan = monthly_target * n_months

    by_category = (
        actuals.groupby("category_name")["amount"].sum()
        .reset_index()
        .rename(columns={"amount": "Actual", "category_name": "Category"})
        .sort_values("Actual", ascending=False)
        .reset_index(drop=True)
    )
    by_category["Avg Monthly"] = (by_category["Actual"] / n_months).round(0) if n_months > 0 else 0

    return {
        "total_actual": total,
        "plan": plan,
        "over_under": total - plan,
        "pct_of_plan": total / plan if plan > 0 else None,
        "by_category": by_category,
    }


def make_health_care_monthly_chart(df_ynab: pd.DataFrame, monthly_target: int,
                                    date_from, date_to,
                                    categories: list | None = None,
                                    cumulative: bool = False):
    """Monthly Health Care spending vs. flat target, stacked by category."""
    date_from = pd.Timestamp(date_from)
    date_to = pd.Timestamp(date_to)

    actuals = df_ynab[
        (df_ynab["category_group"] == HC_GROUP) &
        (df_ynab["date"] >= date_from) &
        (df_ynab["date"] <= date_to)
    ].copy()
    if categories:
        actuals = actuals[actuals["category_name"].isin(categories)]

    actuals["month"] = actuals["date"].dt.to_period("M")
    all_months = pd.period_range(date_from.to_period("M"), date_to.to_period("M"), freq="M")
    month_strs = [str(m) for m in all_months]

    fig = go.Figure()

    if cumulative:
        monthly_total = actuals.groupby("month")["amount"].sum().reindex(all_months, fill_value=0)
        cum_actual = monthly_total.cumsum().values
        cum_plan = [float(monthly_target) * (i + 1) for i in range(len(all_months))]

        fig.add_trace(go.Scatter(x=month_strs, y=cum_plan,
            name="Cumulative Target", mode="lines",
            line=dict(dash="dash", color="orange", width=2)))
        fig.add_trace(go.Scatter(x=month_strs, y=cum_actual,
            name="Cumulative Actual", mode="lines",
            fill="tozeroy", line=dict(color="steelblue", width=2)))
        title = "Health Care — Cumulative Actual vs. Target"
    else:
        cat_monthly = actuals.groupby(["month", "category_name"])["amount"].sum().reset_index()
        cat_monthly["month"] = cat_monthly["month"].astype(str)

        # Largest category first → lands at bottom of stack
        cat_order = (
            cat_monthly.groupby("category_name")["amount"].sum()
            .sort_values(ascending=False).index.tolist()
        )
        for cat in cat_order:
            vals = (
                cat_monthly[cat_monthly["category_name"] == cat]
                .set_index("month")["amount"]
                .reindex(month_strs, fill_value=0)
            )
            fig.add_trace(go.Bar(x=month_strs, y=vals.values, name=cat))

        fig.add_trace(go.Scatter(
            x=month_strs,
            y=[float(monthly_target)] * len(month_strs),
            name=f"Monthly Target (${monthly_target:,.0f})",
            mode="lines+markers",
            line=dict(dash="dash", color="orange", width=2),
        ))
        fig.update_layout(barmode="stack")
        title = "Health Care — Monthly Actual vs. Target by Category"

    if categories:
        title += f"<br><sup>Filtered: {', '.join(categories)}</sup>"

    fig.update_layout(
        title=title,
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=500,
        margin=dict(t=100),
    )
    return fig


def _count_months(date_from: pd.Timestamp, date_to: pd.Timestamp) -> float:
    """Fractional months covered by [date_from, date_to]."""
    months = 0.0
    for year in range(date_from.year, date_to.year + 1):
        for month in range(1, 13):
            days_in_month = calendar.monthrange(year, month)[1]
            m_start = pd.Timestamp(year, month, 1)
            m_end = pd.Timestamp(year, month, days_in_month)
            o_start = max(date_from, m_start)
            o_end = min(date_to, m_end)
            if o_start <= o_end:
                months += (o_end - o_start).days / days_in_month
    return months


def build_living_expenses_comparison(df_ynab: pd.DataFrame, monthly_target: int,
                                      date_from, date_to) -> dict:
    """Actual Living Expenses vs. prorated monthly target for a date range."""
    date_from = pd.Timestamp(date_from)
    date_to = pd.Timestamp(date_to)

    actuals = df_ynab[
        (df_ynab["category_supergroup"] == "Living Expenses") &
        (df_ynab["date"] >= date_from) &
        (df_ynab["date"] <= date_to)
    ].copy()

    total = actuals["amount"].sum()
    plan = monthly_target * _count_months(date_from, date_to)

    n_months = _count_months(date_from, date_to)

    by_group = (
        actuals.groupby("category_group")["amount"].sum()
        .reset_index()
        .rename(columns={"amount": "Actual", "category_group": "Category Group"})
        .sort_values("Actual", ascending=False)
        .reset_index(drop=True)
    )
    by_group["Avg Monthly"] = (by_group["Actual"] / n_months).round(0) if n_months > 0 else 0

    return {
        "total_actual": total,
        "plan": plan,
        "over_under": total - plan,
        "pct_of_plan": total / plan if plan > 0 else None,
        "by_group": by_group,
    }


def make_living_expenses_monthly_chart(df_ynab: pd.DataFrame, monthly_target: int,
                                        date_from, date_to,
                                        groups: list | None = None,
                                        cumulative: bool = False):
    """Monthly Living Expenses vs. flat target, stacked by category_group."""
    date_from = pd.Timestamp(date_from)
    date_to = pd.Timestamp(date_to)

    actuals = df_ynab[
        (df_ynab["category_supergroup"] == "Living Expenses") &
        (df_ynab["date"] >= date_from) &
        (df_ynab["date"] <= date_to)
    ].copy()
    if groups:
        actuals = actuals[actuals["category_group"].isin(groups)]

    actuals["month"] = actuals["date"].dt.to_period("M")
    all_months = pd.period_range(date_from.to_period("M"), date_to.to_period("M"), freq="M")
    month_strs = [str(m) for m in all_months]

    fig = go.Figure()

    if cumulative:
        monthly_total = actuals.groupby("month")["amount"].sum().reindex(all_months, fill_value=0)
        cum_actual = monthly_total.cumsum().values
        cum_plan = [float(monthly_target) * (i + 1) for i in range(len(all_months))]

        fig.add_trace(go.Scatter(x=month_strs, y=cum_plan,
            name="Cumulative Target", mode="lines",
            line=dict(dash="dash", color="orange", width=2)))
        fig.add_trace(go.Scatter(x=month_strs, y=cum_actual,
            name="Cumulative Actual", mode="lines",
            fill="tozeroy", line=dict(color="steelblue", width=2)))
        title = "Living Expenses — Cumulative Actual vs. Target"
    else:
        grp_monthly = actuals.groupby(["month", "category_group"])["amount"].sum().reset_index()
        grp_monthly["month"] = grp_monthly["month"].astype(str)

        # Largest group first → lands at bottom of stack
        grp_order = (
            grp_monthly.groupby("category_group")["amount"].sum()
            .sort_values(ascending=False).index.tolist()
        )

        for grp in grp_order:
            vals = (
                grp_monthly[grp_monthly["category_group"] == grp]
                .set_index("month")["amount"]
                .reindex(month_strs, fill_value=0)
            )
            fig.add_trace(go.Bar(x=month_strs, y=vals.values, name=grp))

        fig.add_trace(go.Scatter(
            x=month_strs,
            y=[float(monthly_target)] * len(month_strs),
            name=f"Monthly Target (${monthly_target:,.0f})",
            mode="lines+markers",
            line=dict(dash="dash", color="orange", width=2),
        ))
        fig.update_layout(barmode="stack")
        title = "Living Expenses — Monthly Actual vs. Target by Category Group"

    if groups:
        title += f"<br><sup>Filtered: {', '.join(groups)}</sup>"

    fig.update_layout(
        title=title,
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=500,
        margin=dict(t=100),
    )
    return fig


def make_other_expenses_chart(df: pd.DataFrame, date_from, date_to):
    """Monthly stacked bar chart of Other - Non Right Capital spending by category."""
    date_from = pd.Timestamp(date_from)
    date_to = pd.Timestamp(date_to)

    dfo = df[
        (df["category_group"] == "Other - Non Right Capital") &
        (df["date"] >= date_from) &
        (df["date"] <= date_to) &
        (df["amount"] > 0)
    ].copy()
    dfo["month"] = dfo["date"].dt.to_period("M").astype(str)

    monthly = dfo.groupby(["month", "category_name"], as_index=False)["amount"].sum()

    fig = px.bar(
        monthly,
        x="month", y="amount", color="category_name",
        title="Other Expenses by Category",
        labels={"amount": "Amount ($)", "month": "Month", "category_name": "Category"},
    )
    fig.update_layout(
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        xaxis_tickangle=45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=450,
        margin=dict(t=100),
    )
    return fig


def get_time_anchors():
    today = pd.Timestamp.today()
    first_of_month = today.replace(day=1)
    last_month = (first_of_month - pd.DateOffset(months=1)).normalize()
    first_of_year = pd.Timestamp(year=today.year, month=1, day=1)
    windows = {
        "3M": last_month - pd.DateOffset(months=2),
        "6M": last_month - pd.DateOffset(months=5),
        "12M": last_month - pd.DateOffset(months=11),
    }
    return today, first_of_month, last_month, first_of_year, windows