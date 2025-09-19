import pandas

chart_specs = [
    # Super Groups
    {
        "name": "category_supergroups_monthly",
        "df_name": "df_sgrp_monthly",
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
        "df_name": "df_sgrp_yearly",
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
        "df_name": "df_grp_yearly",
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
        "name": "basic_expenses_housing",
        "df_name": "df_cat_yearly",
        "filter_col": "category_group",
        "filter": {"values": ["Basic Expenses - Housing"]},
        "color_col": "category_name",
        "time_col": "year",
        "chart_type": ["line", "bar"],
        "title": [
            "Basic Expenses - Housing Group by Category",
            "Basic Expenses - Housing Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "basic_expenses_rental_home",
        "df_name": "df_cat_yearly",
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
        "df_name": "df_cat_yearly",
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
        "df_name": "df_grp_yearly",
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
        "name": "goal_chris_on_payroll",
        "df_name": "df_cat_monthly",
        "filter_col": "category_group",
        "filter": {"values": ["Goal - Chris on Payroll"]},
        "color_col": "category_name",
        "time_col": "month_start",
        "chart_type": ["line", "bar"],
        "title": [
            "Goal - Chris on Payroll Group by Category",
            "Goal - Chris on Payroll Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "goal_travel",
        "df_name": "df_cat_yearly",
        "filter_col": "category_group",
        "filter": {"values": ["Goal - Travel"]},
        "color_col": "category_name",
        "time_col": "year",
        "chart_type": ["line", "bar"],
        "title": [
            "Goal - Travel Group by Category",
            "Goal - Travel Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },
    {
        "name": "goal_children_non_academic",
        "df_name": "df_cat_yearly",
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
    {
        "name": "goal_home_improvement",
        "df_name": "df_cat_monthly",
        "filter_col": "category_group",
        "filter": {"values": ["Goal - Home Improvement"]},
        "color_col": "category_name",
        "time_col": "month_start",
        "chart_type": ["line", "bar"],
        "title": [
            "Goal - Home Improvement Group by Category",
            "Goal - Home Improvement Group by Category, Cumulative"
        ],
        "force_year_ticks": [True, False]
    },

    # Living Expenses
    {
        "name": "living_expenses_group",
        "df_name": "df_grp_monthly",
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
        "df_name": "df_cat_yearly",
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
        "df_name": "df_cat_monthly",
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
        "df_name": "df_cat_yearly",
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
        "df_name": "df_cat_monthly",
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
        "df_name": "df_cat_monthly",
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
    },
    # Inflow: Internal Master Category / Ready to Assign
    {
        "name": "inflow",
        "df_name": "df_pyn_monthly",
        "filter_col": "category_name",
        "filter": {"values": ["Inflow: Ready to Assign"]},
        "color_col": "payee_name",
        "time_col": "month_start",
        "chart_type": ["line", "bar"],
        "title": [
            "Inflow Category by Source",
            "Inflow Category by Source, Cumulative"
        ],
        "force_year_ticks": [True, False]
    }
]
