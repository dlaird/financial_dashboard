# Financial Dashboard

A Streamlit dashboard for visualizing and analyzing personal spending patterns from YNAB, with an email-to-YNAB transaction pipeline for quick transaction entry.

## Features

- Dynamic charts with progressive disclosure
- Trend summaries with deviation alerts (>15% highlight, >20% alert)
- Drillable sunburst/treemap/icicle hierarchy charts
- Transaction drill-down by supergroup, group, and category
- Pending transaction inbox: approve/reject transactions parsed from email
- Payee cleanup tools and name-variant detection

## Setup

### 1. Clone and enter the project

```bash
git clone https://github.com/dalairds/financial_dashboard.git
cd financial_dashboard
```

### 2. Create a virtual environment

**Linux / macOS / WSL:**
```bash
python3 -m venv .venv
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

**Linux / macOS / WSL:**
```bash
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables: `YNAB_API_KEY`, `YNAB_BUDGET_ID`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `DEFAULT_YNAB_ACCOUNT`.

## Running the dashboard

**With cached data (default — fast):**

Linux / macOS / WSL:
```bash
streamlit run financial_dashboard.py
```

Windows (PowerShell):
```powershell
streamlit run financial_dashboard.py
```

**Fetch fresh data from YNAB:**

Linux / macOS / WSL:
```bash
streamlit run financial_dashboard.py -- --refresh-data
```

Windows (PowerShell):
```powershell
streamlit run financial_dashboard.py -- --refresh-data
```

## Running the email poller

The email poller checks Gmail for new YNAB transaction emails and writes them to the pending transactions queue.

Linux / macOS / WSL:
```bash
.venv/bin/python email_poller.py
```

Windows (PowerShell):
```powershell
.venv\Scripts\python.exe email_poller.py
```

To run on a schedule, use Windows Task Scheduler (Windows) or cron (Linux) pointing at the Python interpreter inside `.venv`.

**Windows Task Scheduler example:**
- Program: `C:\path\to\financial_dashboard\.venv\Scripts\python.exe`
- Arguments: `C:\path\to\financial_dashboard\email_poller.py`

**Linux cron example (every 15 min):**
```
*/15 * * * * /path/to/financial_dashboard/.venv/bin/python /path/to/financial_dashboard/email_poller.py
```

## Email format for transaction entry

See `ynab email text format.txt` for the expected email body structure. Subject line must contain "ynab" (case-insensitive).
