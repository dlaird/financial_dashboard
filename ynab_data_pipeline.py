import requests
import pandas as pd
import os
from data_helpers import keys_exist

from dotenv import load_dotenv
load_dotenv()

def get_ynab_data():
    # get ynab access token and budget id
    token = os.getenv("YNAB_API_TOKEN")
    budget_id = os.getenv("YNAB_BUDGET_ID")  # or use 'last-used'
    if not token or not budget_id:
        raise ValueError("Missing YNAB_API_TOKEN or YNAB_BUDGET_ID. Check your .env file and variable names.")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # --- Pull Transactions ---
    tx_url = f"https://api.youneedabudget.com/v1/budgets/{budget_id}/transactions"
    tx_response = requests.get(tx_url, headers=headers)
    tx_data = tx_response.json()

    # check tx_data response
    if not keys_exist(tx_data, "data", "transactions"):
        raise ValueError("API response missing expected structure")

    # populate transactions
    transactions = tx_data['data']['transactions']

    # Convert to DataFrame and keep relevant columns
    df_tx = pd.DataFrame(transactions)[[
        "date", "amount", "payee_name", "memo", "category_id", "cleared", "approved", "account_name", "import_payee_name", "import_payee_name_original"
    ]]

    # --- Pull Categories ---
    cat_url = f"https://api.youneedabudget.com/v1/budgets/{budget_id}/categories"
    cat_response = requests.get(cat_url, headers=headers)
    cat_data = cat_response.json()
    category_groups = cat_data['data']['category_groups']

    # Flatten and filter hidden categories
    categories_flat = []
    for group in category_groups:
        group_name = group['name']
        for cat in group['categories']:
            categories_flat.append({
                "category_id": cat["id"],
                "category_name": cat["name"],
                "category_group": group_name,
                "hidden": cat.get("hidden", False)
                })

    df_cat = pd.DataFrame(categories_flat)

    # --- Join on category_id (more reliable than name) ---
    df_tx_enriched = df_tx.merge(df_cat, on="category_id", how="left")
    # reorder columns
    df = df_tx_enriched[['date', 'payee_name', 'memo', 'category_group','category_name', 'amount', 'import_payee_name','import_payee_name_original', 'category_id', 'cleared','approved', 'account_name', 'hidden']] 
    # data mods
    df = df.convert_dtypes()
    df['amount'] = df['amount'] / 1000  # Convert from milliunits
    df['amount'] = df['amount'] * -1
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['month'] = df['date'].dt.to_period('M').dt.to_timestamp()
    df['year'] = df['date'].dt.year.astype(str)
    # Add 'category_supergroup' column based on prefix logic
    df["category_supergroup"] = df["category_group"].apply(
        lambda x: (
            "Basic Expenses" if str(x).startswith("Basic Expenses -") else
            "Goals" if str(x).startswith("Goal -") else
            "Living Expenses" if str(x).startswith("Living Expenses -") else
            "Other"
        )
    )

    # remove not-needed transactions 
    # maybe should happen above to avoid running above logic unnecessarily
    # remove transfers between accounts
    # df = df[~df["payee_name"].str.startswith("Transfer :",na=False)].copy()

    # go ahead and remove records from hidden categories until more time to investigate them
    df = df[df["hidden"] != True].copy()
    # df = df[not df["hidden"]].copy()
    
    # remove records from irrelevant accounts
    excluded_accounts = [
        '17008 WTR HELOC',
        'CapOne Education Savings',
        'CapOne LTC Savings',
        'CapOne Pet Savings',
        'CapOne Savings',
        'CapOne Special for M',
        'CapOne Taxes Savings',
        'Capital One REI MasterCard',
        "Chris's Checking - 8664",
        "Chris's Gifts",
        "Chris's Savings",
        'Say Hello USA',
        # "Sophie's Checking - 0991",
        "Sophie's Visa",
        'Vanguard Education Savings'
    ]
    df = df[~df["account_name"].isin(excluded_accounts)].copy()

    # set earliest date
    EarliestDate = pd.to_datetime('1/1/2018')
    df = df[df['date'] >= EarliestDate]

    # # # Save to CSV
    df.to_csv("ynab_extract.csv", index=False)
    # # # Save to Excel
    df.to_excel("ynab_extract.xlsx", index=False)

    return df