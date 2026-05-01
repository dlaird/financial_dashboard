# enhacements
## possible
* drill down to merchant/transaction level

## pending
## ============
### RC Goals — future visualization options
**Option 2: Bar Chart — Plan vs. Actual**
Grouped bar chart: one bar = RC plan, one = actual (annualized for current year). Easy to see
over/under at a glance across all goals for a selected year. Could be added as a tab alongside
the existing comparison table in Goals vs. Plan.

Demo mode:  Rather than randomizing, how about multiplying by a large number

Does the email import process change the read status of the email in the inbox?  Ideally it would set to Read those it imports and would leave as Unread those that it doesn't.

## next/current
## ============
On the bar charts on Goals, Health Care and Living Expense tabs, I think the largest categories are stacked on top.  Please put largest categories on the bottom, smallest on top.



## done
## ============

I'd like to add another tab to  the Actual vs Plan page.  It should be called "Health Care" and reflect the spending made in all categories under the "Basic Expenses - Health Care" category group.  It should have functionality consistent with the Goals and Living expenses tabs.  Add a "Health Care Monthly Target" input tool next to the one for Living Expenses.  The Health Care tab can be between Goals and Living Expenses.  A row for Health Care should be added to the Comparison Table, and table rows should be alphabetized so they are consistent with tab order.

A small request and three related ones for a bigger enhancement:
> The banner at the top of the page when it loads, which reads "Spending Dashboard" is taller than necessary and the font in those words is also larger than necessary.  Is it possible to take those down a bit?
> There's another comparison I want to make in the Actual vs Plan pages.  In addition to the Goals we're comparing, each of which have their own annual, target dollar amount, I also want to review spending on all "Living Expenses - " categories, but their combined total will be compared to a single monthly, target dollar amount.
> This comparison adds a higher level of aggregation, since the "Goals -" category groups are handled individually, and now we want to aggregate across multiple "Living Expenses - " category groups.  In the charts, we'll want a way to select one or more category groups when we're elooking at Living Expenses.
> I want to update the goal names in the Edit Plan Amounts table to match their names in YNAB, i.e., give them back their prefix "Goal - ".  I think this will require a code change, what's simplest way to do this?

Two sections of links on dashboard each show an active page, but only one is actually active so other one should be disabled.  The Pending Transactions shows active but clicking it does nothing.  Have to click another in the same group and then Pending Transactions for it to work.

Import Right Capital goal amounts and provide reference comparisons.

Each of the Goals spending categories map to spending goals in Right Capital, the program that our financial manager uses to build our financial plan and forecast our possible outcomes.  The spending goals in Right Capital are annual.  I'd like a way to compare those planned goal amounts to actual spending in those categories, maybe by grossing up actuals into yearly amounts or converting annual plan amounts to monthly to compare to monthly actuals.  Please suggest some approaches.

The Right Capital goals amounts for 2025-2031 are in the file: right_capital_goals.xlsx.  It would be nice to have a way in the dashboard to view and edit these amounts.

A couple requests on Spending Breakdown:
- Default "Select Time" setting to current year (to speed things)
- Move option for Custom to the top and All to the bottom
- Selecting Custom on my Samsung tablet does not trigger anything to open the Start/End date boxes, so it doesn't work.

On Spending Breakdown charts (sunburst/treemap/icicle):
After clicking to drill down into a subcategory, when I change dates, my drill down selections are lost.  Is it possible to preserve my choices so category selections stay the same at date range is updated?

On Spending Breakdown charts (sunburst/treemap/icicle):
> display both dollars and percentages, if possible.  Dollars in $XX,XXX format.
> Ability to select custom date date ranges for display.

Also, I tried updating phase2_sources for my internet bill from Spectrum but it's not importing.  Can you see what I'm doing wrong?
* after clicking "Check for new transactions" disable and show greyed out until first request is done running
1-trigger logic: sender either me or my wife, but forwarding from a list of possible addresses included a configurable list.
2-ok
3-Amazon order confirmations may include different orders.  Claude will have to determine number of orders, and for each the amount and category.  Each order, even if it includes multiple different items, should be one transaction, categorized as the largest in dollar terms.
4-Account could be set by payee, Amazon with Visa, Electric with Checking, etc.


* obfuscate amounts
After clearing a transaction, do not return to spending alerts
Want to add some documentation, either directly to tab or new tab, starting with format of ynab email, but providing overview of process and basic instructions
* quick entry to ynab
- ability to select account/category from confirmation drop down menus
* on importer, date is not polled date but email date
* on importer, reverse order of payee and account, amount/payee/account/category/memo