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

=============================================================================================

Session Summary — 2026-03-20
New feature: Email-to-YNAB Transaction Pipeline

New files added
- email_poller.py: IMAP poller (polls k2udal@gmail.com). Triggers on subject containing "ynab" (case-insensitive). Parses body positionally — no keywords needed:
    Line 1: amount
    Line 2: account shortcut
    Line 3: payee
    Line 4: category shortcut
    Line 5+: memo (optional)
  Writes parsed transactions to pending_transactions.db. Marks emails as read after processing. Designed to run on a schedule via Windows Task Scheduler.
- pending_db.py: SQLite helpers — insert_pending, get_pending, approve_transaction, reject_transaction. Schema: id, date, amount_milliunits, payee, account_id, account_name, category_id, category_name, memo, raw_email, status, created_at.
- ynab_writer.py: Fetches accounts and categories from YNAB API, resolves shortcuts to IDs, checks for duplicate transactions (same date/payee/amount within 5 days), POSTs approved transactions. CLI: --list-accounts, --list-categories.
- category_shortcuts.json: Maps short aliases (e.g. "grocs", "dining") to YNAB category names. Values use [Group] 'Name' format; resolver strips the bracket/quote wrapper automatically. Case-insensitive.
- account_shortcuts.json: Maps short aliases (e.g. "usaae", "chase") to exact YNAB account names. Case-insensitive. Multiple shortcuts can point to the same account.
- pending_transactions.db: SQLite database file (not committed).

financial_dashboard.py changes
- Added Pending Transactions section (now last item in sidebar nav, below Inflows)
- Shows all pending transactions with editable fields: payee, amount, date, account (dropdown), category (dropdown), memo
- Approve button: POSTs to YNAB via ynab_writer.py, marks record approved in DB
- Reject button: marks record rejected in DB
- Duplicate warning shown if a matching transaction is detected in YNAB before posting

.env.example changes
- Added GMAIL_ADDRESS, GMAIL_APP_PASSWORD, DEFAULT_YNAB_ACCOUNT

Architecture notes
- Gmail access uses IMAP with an app password (not OAuth) — simpler for a single-user personal tool
- Phase 1 only (structured manual emails). Phase 2 (AI parsing of real-world HTML emails like utility bills) requires an Anthropic API key — not yet implemented.
- YNAB write confirmed working via API; end-to-end save to YNAB not yet tested by user

Next logical steps
- End-to-end test: approve a pending transaction and confirm it lands in YNAB
- Set up Windows Task Scheduler to run email_poller.py on a schedule (e.g. every 15–30 min)
- Phase 2: parse real-world HTML emails (utility bills, Amazon invoices) using Claude API — requires Anthropic API key
- Possibly explore auto-importing from emailed bank/credit card statements

=============================================================================================

Session Summary — 2026-04-06
Fixes and enhancements implemented

email_poller.py
- Changed email field order to: amount / payee / account / category / memo (payee and account swapped)
- Transaction date now defaults to the email's sent date (RFC 2822 Date header) instead of today's date
- Added _parse_email_date() helper using email.utils.parsedate_to_datetime
- _parse_date() now takes a default parameter instead of hardcoding date_cls.today()
- Updated module docstring to reflect new field order and date behavior
- Fixed usage line in docstring: python → .venv/bin/python

financial_dashboard.py
- Fixed post-action navigation: after approve, reject, or duplicate-check rerun, dashboard now stays on
  Pending Transactions instead of jumping back to Spending Alerts
  - Sidebar nav selection is persisted as an index (st.session_state["nav_idx"]) rather than by label value
  - All three st.rerun() calls in the pending section set nav_idx to the Pending Transactions index first
  - _pending_label (which includes a live count) is the display label only; canonical key "Pending Transactions"
    is used for section routing, so label changes on rerun don't break selection
- Added "How to Use" section to sidebar nav (between Inflows and Pending Transactions) covering:
  - Dashboard overview and Right Capital context
  - Table of all sections with descriptions
  - How to refresh data (--refresh-data flag)
  - Email-to-YNAB pipeline instructions (field order, example email body)
  - Running the poller manually (Linux/WSL and Windows commands)
  - Scheduling the poller via cron or Windows Task Scheduler
  - Account and category shortcuts reference

README.md
- Fixed poller run commands: python → .venv/bin/python (Linux) and .venv\Scripts\python.exe (Windows)

requirements.txt (new file)
- Added to repo; includes openpyxl==3.1.5 (required by pandas .to_excel in ynab_data_pipeline.py)

ynab email text format.txt
- Updated to reflect new field order: amount / payee / account / category / memo
- Added note that transaction date = email sent date

Architecture notes
- Email field order is now: amount / payee / account / category / memo (matches user's mental model)
- Nav index persistence pattern: store index in session_state, set before any st.rerun(); display labels
  (which may include dynamic counts) are decoupled from routing keys

Next logical steps
- End-to-end test: approve a pending transaction and confirm it lands in YNAB
- Set up scheduled poller (cron or Windows Task Scheduler)
- Phase 2: parse real-world HTML emails using Claude API — requires Anthropic API key

=============================================================================================

Session Summary — 2026-04-07
Enhancements implemented

email_poller.py
- Fixed Gmail body parsing: _get_body now prefers text/plain when it has multiple lines; falls
  back to HTML part (parsing <br> tags) when Gmail collapses lines into a single space-separated string
- Fixed NoneType error: get_payload(decode=True) returns None for container MIME parts; now skipped
- Added IMAP SINCE filter: only fetches emails from the 1st of the prior month; prevents processing
  of very old unread emails and speeds up polling
- Phase 2 routing: poller now fetches all unread mail from trusted forwarders (not just subject-filtered);
  emails with "ynab" in subject → Phase 1; all others → Phase 2 if sender matches a rule
- Added _load_sources(), _match_sender_rule(), _extract_forwarded_from() helpers
- trusted_forwarders now maps address → memo prefix ("D" or "M")
- Added exc_info=True to error logging for full tracebacks

phase2_parser.py (new file)
- Claude-powered extraction for real-world HTML emails (Amazon, Whole Foods, utility bills)
- _category_list() fetches live YNAB categories (not shortcuts) as the authoritative list for Claude
- Prompt instructs Claude to return a JSON array; handles single-object response gracefully
- Memo prefix (D: / M:) applied based on which trusted forwarder sent the email
- Prompt instructs Claude to include order/receipt/invoice numbers in memo when present
- build_pending_records() resolves account from sender rule, category from Claude suggestion

phase2_sources.json (new file)
- trusted_forwarders: k2udal@gmail.com and dalairds@gmail.com → "D"; mbdvol@gmail.com → "M"
- sender_rules: Amazon (amazon.com), Whole Foods (wholefoodsmarket.com), City of Austin Utilities
  (name_contains match), West Travis County PUD (invoicecloud.net), Anthropic (mail.anthropic.com)
- Matching supports: domain, address, name_contains (for senders using third-party billing services)

financial_dashboard.py
- Demo Mode: sidebar checkbox scrambles amounts (stable per-category random scale 0.55–1.45×)
  and replaces payee names with "Vendor NNN"; Right Capital $8K target line hidden in demo mode;
  real and demo dataframes cached separately for instant toggle
- "Check for New Transactions" button in Pending Transactions section runs email_poller.run()
  on demand — no scheduled background process needed; page refreshes after completion
- df_analytics split: charts, summaries, alerts use df_analytics (capped at end of last full month)
  to avoid partial-month distortion; transaction drill-downs use full df (through today)
- Dashboard URL in sidebar now shows real LAN IP (UDP trick to 8.8.8.8) instead of loopback 127.0.1.1
- How to Use updated: Phase 2 AI parsing section, Demo Mode section, "Check for New Transactions"
  replaces scheduled poller instructions, Phase 1 renamed to "Manual Entry"

data_helpers.py
- apply_demo_scramble(df): scales amounts per category with fixed seed; maps payees to generic names

ynab_writer.py
- category_name_to_id: strips trailing whitespace before matching (fixes "Cloud - hosting..." with
  trailing space in YNAB)

requirements.txt
- Added anthropic==0.89.0

.env.example
- Added ANTHROPIC_API_KEY

.gitignore
- Removed enhacements.md; scratch.md added to repo instead

scratch.md (new file, replaces enhacements.md)
- Personal notes/scratch file, now tracked in repo

Architecture notes
- Phase 2 pipeline: forward bill/receipt email (no "ynab" in subject) → poller detects original
  sender via forwarded header → matches sender_rules in phase2_sources.json → Claude extracts
  transactions → pending queue → review and approve in dashboard
- df / df_analytics split: df is full dataset through today; df_analytics is capped at last full
  month end; use df_analytics for all aggregations/charts, df for transaction-level views
- Demo mode: apply_demo_scramble called inside load_data(refresh, demo); cached separately per
  demo flag so toggle is instant
- Poller is triggered on-demand from the dashboard button, not on a schedule

Next logical steps
- Phone/LAN access unresolved: Streamlit binds to 0.0.0.0 correctly; likely firewall (ufw) or
  router client isolation; run "sudo ufw allow 8501" to test
- Inline log output from "Check for New Transactions" button not yet shown in UI (visible in
  terminal only) — possible future enhancement
- Add more senders to phase2_sources.json as needed (see How to Use for instructions)
- start_dashboard.sh (tmux-based): created but not yet working from Windows SSH terminal;
  may not be worth pursuing since VS Code terminal works fine for normal use