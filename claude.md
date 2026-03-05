This project accesses my personal financial transaction data from YNAB via an API, then cleans it and summarizes it and then displays it graphically on a web site.  I'm doing this because YNAB has limited analytical tools, and I also want to connect the results from Right Capital, the financial planning software that our financial advisors use for our financial plan.  We can't access the Right Capital data directly, but I've re-named all my categories and sub categories in YNAB so that they are consistent with Right Capital groups, and in the case of Living Expense Categories, I've added the $8,000 monthly target number from Right Capital directly to the chart.

The results are ok but they have not made it that much easier for me to identify trends in my spending, or see how recent spending has deviated from historical spending.  It's all very static.

Do you have any suggestions for enhancing the code, both to improve what it's doing now but also to add new functionality such as:
- better identify trends
- identify deviations in recent spending compared to historical
- identify and flag outliers for review
- drill more deeply back into the transaction level data.  I know that's hard but seems like it should be possible. 

What is possible and how much is realistic for me to implement?

=============================================================================================

Session Summary — 2026-03-04
Enhancements implemented
data_helpers.py

Added HIGHLIGHT_THRESHOLD = 0.15 and ALERT_THRESHOLD = 0.20 as named constants at the top of the file
Refactored summarize_recent_trends / prepare_summary: replaced boolean by_category param with group_col=None — now works at any grouping level ("category_name", "category_group", etc.)
prepare_summary now sorts by pct_ch_3m descending (highest recent spike at top) instead of by recent_month
Added _color_pct helper and applied .map() in style_summary: cells go red (>15% above avg) or green (>15% below avg); na_rep="-" handles missing values cleanly
Added make_sunburst(df, year=None): builds a 4-level drillable sunburst chart (supergroup → group → category → payee), with optional year filter
Added payee_name_report(df, top_n=75): returns (1) top payees by transaction count, (2) payees grouped by normalized 10-char prefix to surface name variants for cleanup
Removed unused imports (datetime, timedelta, DateOffset)
Replaced deprecated use_container_width=True with width='stretch' throughout
financial_dashboard.py

Added import argparse; refresh_data is now a CLI flag defaulting to False: run with -- --refresh-data to fetch live from YNAB
Added filtered DataFrames and summary tables for Goals (category_group level) and Basic Expenses (category_group level)
Added alerts computation: all category groups >20% above 3M average
Added three new sidebar sections (in order): Spending Alerts, Spending Breakdown, Payee Cleanup
Spending Alerts: flags high-deviation groups, green success message if none
Spending Breakdown: year-selector dropdown + interactive sunburst chart
Payee Cleanup: two tables — top payees by volume, and detected name variant groups
Architecture notes
Data hierarchy: category_supergroup → category_group → category_name → payee_name
Main supergroups in use: "Living Expenses", "Goals", "Basic Expenses" (plus "Other", excluded from most analytics)
amounts are sign-flipped in the pipeline: expenses are positive, inflows are negative
df["year"] is a string column (e.g., "2025")
Next logical steps discussed but not yet implemented
Transaction-level drill-down from sunburst: click a segment → filter a st.dataframe of matching transactions below the chart (requires Streamlit on_select event handling, available in Streamlit ≥1.35)
Treemap / Icicle chart variants (same data as sunburst, one-word swap in px.sunburst → px.treemap / px.icicle)
Separate per-supergroup sunbursts going 4 levels deep within each supergroup

=============================================================================================

Session Summary — 2026-03-04 (Session 2)
Enhancements implemented

data_helpers.py

Removed dead filter_by_click() function (leftover from abandoned click-based drill-down attempt in prior session)
Removed clickmode="event+select" from make_hierarchy_chart (also leftover)
Added supergroup=None parameter to make_hierarchy_chart: when a supergroup is selected, it is dropped from the path hierarchy so category_group becomes the root node (3-level chart instead of 4-level); title updates accordingly
Added @st.cache_data decorator to make_hierarchy_chart, make_heatmap, and make_bubble_chart so they only recompute when inputs (df, filters) actually change
financial_dashboard.py

Spending Breakdown section restructured:
Added Select Supergroup dropdown alongside Select Year (two shared filters at top)
Changed from 3 chart tabs to 4 tabs: Sunburst | Treemap | Icicle | Transactions
Added key=f"{type}_{year}_{sg}" to each st.plotly_chart call to force full widget replacement on filter change (fixes Treemap not updating when path structure changes between All and single-supergroup views)
Transaction drill-down moved into the Transactions tab; when a supergroup is pre-selected above, the Supergroup dropdown is omitted (3 cascading dropdowns instead of 4)
Metric font size: injected global CSS (stMetricValue → 1.1rem, stMetricLabel → 0.8rem) to bring st.metric in line with surrounding content
Performance: wrapped all expensive top-level computations in @st.cache_data functions so Streamlit reruns (triggered by every user interaction) skip recomputation:
load_data(refresh) — caches CSV read / YNAB API call
build_static_charts(df) — caches all 8 groupby aggregations and ~20 Plotly chart builds from the chart_specs loop; eliminates the globals()[spec["df_name"]] lookup by using a local agg dict instead
compute_summaries(df, windows, first_of_year, last_month) — caches 5 prepare_summary calls (windowed average computation); cache key is stable within a calendar month
Architecture notes

build_static_charts now owns all groupby aggregations internally; the module-level df_sgrp_monthly etc. variables no longer exist
@st.cache_data on chart functions: first load populates all caches; subsequent interactions (tab switches, dropdown changes that don't affect cached parameters) are near-instant
load_data(True) and load_data(False) are cached separately, so --refresh-data data doesn't pollute the CSV-cached version
Next logical steps discussed but not yet implemented

None remaining from prior notes; all three original items are now complete