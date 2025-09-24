import pandas as pd
import plotly.express as px
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
from pandas.tseries.offsets import DateOffset

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
            st.plotly_chart(c1, use_container_width=True)
        with col2:
            st.plotly_chart(c2, use_container_width=True)
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
def summarize_recent_trends(df, windows, ytd_start, last_month, by_category = False):
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    last_month_last_day = last_month + pd.offsets.MonthEnd(0)
    summaries = []

    if by_category:
        for cat in df["category_name"].unique():
            df_cat = df[df["category_name"] == cat]

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


def prepare_summary(df, windows, first_of_year, last_month, by_category):
    summary = summarize_recent_trends(df, windows, first_of_year, last_month, by_category)
    summary = summary[summary["ytd"] != 0].sort_values(by="recent_month", ascending=False)
    summary = summary.round({
        "recent_month": 0, "avg_3m": 0, "avg_6m": 0, "avg_12m": 0, "ytd": 0
    }).reset_index(drop=True)
    return summary

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
        })
        .set_properties(**{"font-size": "16px", "font-weight": "bold"})
        .set_table_styles([
            {'selector': 'th', 'props': [('min-width', '60px')]},
            {'selector': 'td', 'props': [('min-width', '60px')]}
        ])
    )

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