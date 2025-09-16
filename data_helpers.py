import pandas as pd

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
