import pandas as pd
import plotly.express as px
import numpy as np
import streamlit as st

def sort_and_cast(df, group_col, time_col, ascending_order=True):
    """
    Sorts a DataFrame by group size and time, and casts the group column as ordered categorical.
    
    Parameters:
        df (pd.DataFrame): The input DataFrame.
        group_col (str): The column to group and rank by (e.g., 'category_group').
        time_col (str): The time column to sort within groups (e.g., 'month_start').
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
