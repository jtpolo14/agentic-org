import os
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# --- Anthropic cost check ---
# Requires Admin API key (sk-ant-admin...) — different from regular ANTHROPIC_API_KEY
# Get it at: https://console.anthropic.com → Settings → API Keys → Create Admin Key

ADMIN_KEY = os.getenv("ANTHROPIC_ADMIN_KEY")

def get_claude_usage(days=7):
    if not ADMIN_KEY:
        print("ANTHROPIC_ADMIN_KEY not set in .env")
        return

    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
    end   = datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59Z")

    # Try without group_by first to see raw data
    r = requests.get(
        "https://api.anthropic.com/v1/organizations/usage_report/messages",
        headers={
            "x-api-key": ADMIN_KEY,
            "anthropic-version": "2023-06-01",
        },
        params={
            "starting_at":  start,
            "ending_at":    end,
            "bucket_width": "1d",
        }
    )

    print(f"Claude usage ({days}d): {r.status_code}")
    if not r.ok:
        print(r.text)
        return

    data = r.json()
    buckets_with_data = [b for b in data.get("data", []) if b.get("results")]
    if not buckets_with_data:
        print("  No usage data found. The admin key may be scoped to a different workspace.")
        print("  Check: console.anthropic.com -> Settings -> Workspaces")
        print("  Make sure the admin key and ANTHROPIC_API_KEY are in the same workspace/org.")
        return

    totals = {}
    for bucket in data.get("data", []):
        for row in bucket.get("results", []):
            model = row.get("model", "all")
            inp   = row.get("uncached_input_tokens", 0) + row.get("cache_read_input_tokens", 0)
            out   = row.get("output_tokens", 0)
            if model not in totals:
                totals[model] = {"input": 0, "output": 0}
            totals[model]["input"]  += inp
            totals[model]["output"] += out

    for model, t in totals.items():
        print(f"  {model}: {t['input']:,} in / {t['output']:,} out tokens")


def get_claude_cost(days=7):
    if not ADMIN_KEY:
        return

    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
    end   = datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59Z")

    r = requests.get(
        "https://api.anthropic.com/v1/organizations/cost_report",
        headers={
            "x-api-key": ADMIN_KEY,
            "anthropic-version": "2023-06-01",
        },
        params={
            "starting_at":  start,
            "ending_at":    end,
            "bucket_width": "1d",
        }
    )

    print(f"Claude cost ({days}d): {r.status_code}")
    if not r.ok:
        print(r.text)
        return

    total = 0.0
    for bucket in r.json().get("data", []):
        for row in bucket.get("results", []):
            total += float(row.get("amount", 0))

    # amount is in cents (lowest currency unit)
    print(f"  Total: ${total / 100:.4f} USD")


# --- Google API quota check ---
# Uses the Service Usage API with existing OAuth credentials.
# Requires 'https://www.googleapis.com/auth/cloud-platform.read-only' scope
# (add to SCOPES in google_calendar.py if not present).

def get_google_billing():
    try:
        from google_auth import get_credentials
    except Exception as e:
        print(f"Could not import credentials: {e}")
        return

    creds = get_credentials()
    token = creds.token

    # Step 1: list billing accounts
    r = requests.get(
        "https://cloudbilling.googleapis.com/v1/billingAccounts",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Billing accounts: {r.status_code}")
    if not r.ok:
        print(f"  {r.text[:300]}")
        return

    accounts = r.json().get("billingAccounts", [])
    if not accounts:
        print("  No billing accounts found")
        return

    for account in accounts:
        name    = account.get("name")   # e.g. billingAccounts/012345-ABCDEF
        display = account.get("displayName")
        open_   = account.get("open")
        print(f"  {display}  ({name})  open={open_}")

        # Step 2: budgets for this account (shows spend vs limit if budgets are configured)
        rb = requests.get(
            f"https://billingbudgets.googleapis.com/v1/{name}/budgets",
            headers={"Authorization": f"Bearer {token}"}
        )
        if rb.ok:
            budgets = rb.json().get("budgets", [])
            if not budgets:
                print("    No budgets configured — set one in Cloud Console for spend tracking")
            for b in budgets:
                label  = b.get("displayName", "(unnamed)")
                limit  = b.get("amount", {}).get("specifiedAmount", {})
                amount = f"{limit.get('currencyCode', 'USD')} {limit.get('units', '?')}"
                print(f"    Budget '{label}': limit {amount}")
                for rule in b.get("thresholdRules", []):
                    pct = rule.get("thresholdPercent", 0) * 100
                    print(f"      Alert at {pct:.0f}%")
        else:
            print(f"    Budgets: {rb.status_code} {rb.text[:150]}")


if __name__ == "__main__":
    print("=== Claude Usage ===")
    get_claude_usage(days=7)

    print("\n=== Claude Cost ===")
    get_claude_cost(days=7)

    print("\n=== Google Billing ===")
    get_google_billing()
