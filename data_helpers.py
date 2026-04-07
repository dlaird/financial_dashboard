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
def make_hierarchy_chart(df, chart_type="sunburst", year=None, supergroup=None):
    """Build a hierarchy chart (sunburst, treemap, or icicle) of spending.

    Args:
        df: raw transactions DataFrame
        chart_type: "sunburst", "treemap", or "icicle"
        year: year value to filter, or None / "All" for all years
        supergroup: one of the supergroup names to filter, or None / "All" for all
    """
    df_sb = df[df["category_supergroup"].isin(["Living Expenses", "Goals", "Basic Expenses"])].copy()
    if year and year != "All":
        df_sb = df_sb[df_sb["year"] == year]
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

    year_label = year if year and year != "All" else "All Years"
    sg_label = supergroup if supergroup and supergroup != "All" else None
    title_parts = [p for p in [sg_label, year_label] if p]
    title = "Spending Breakdown" + (" — " + " — ".join(str(p) for p in title_parts) if title_parts else "")

    if chart_type == "treemap":
        fig = px.treemap(df_sb, path=path, values="amount", title=title)
        fig.update_traces(textinfo="label+value+percent parent")
    elif chart_type == "icicle":
        fig = px.icicle(df_sb, path=path, values="amount", title=title)
        fig.update_traces(textinfo="label+value+percent parent")
    else:  # sunburst (default)
        fig = px.sunburst(df_sb, path=path, values="amount", title=title)
        fig.update_traces(textinfo="label+percent parent")

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