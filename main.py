import requests
import time
import random
import os
import threading
from datetime import datetime
from flask import Flask

# --- Configuration ---
MESSAGES = ["SD", "sd", "Sd", "sD"]
GAP_BETWEEN_ACCOUNTS = 180      # 3 minutes
TOTAL_CYCLE = 3 * GAP_BETWEEN_ACCOUNTS  # 9 minutes (3 accounts * 180s)
MAX_RETRIES = 5
RETRY_DELAY = 5

app = Flask(__name__)
message_counts = {}

# --- Helpers ---
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# --- Load Accounts ---
def get_accounts():
    accounts = []
    shared_channel_id = os.environ.get("DISCORD_CHANNEL_ID")
    if not shared_channel_id:
        log("❌ No DISCORD_CHANNEL_ID found in environment!")
        return accounts
    
    for i in range(1, 4):
        token = os.environ.get(f"DISCORD_TOKEN_{i}")
        if token:
            accounts.append({
                "token": token,
                "channel_id": shared_channel_id,
                "id": i
            })
            message_counts[shared_channel_id] = 0
        else:
            log(f"⚠ Missing DISCORD_TOKEN_{i}")
    return accounts

# --- Message Sending ---
def send_message(account, msg):
    url = f"https://discord.com/api/v10/channels/{account['channel_id']}/messages"
    headers = {
        "Authorization": account["token"],
        "Content-Type": "application/json"
    }
    data = {"content": msg}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(url, headers=headers, json=data, timeout=10)
            if r.status_code in [200, 204]:
                message_counts[account['channel_id']] += 1
                log(f"✅ Account {account['id']} sent '{msg}'")
                return True
            elif r.status_code == 429:
                retry_after = int(r.headers.get('Retry-After', 60))
                log(f"⚠ Rate limited (Acc {account['id']}). Retrying after {retry_after}s...")
                time.sleep(retry_after)
            else:
                log(f"⚠ Acc {account['id']} failed with status {r.status_code}")
        except Exception as e:
            log(f"❌ Error for account {account['id']} on attempt {attempt}: {e}")

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
    log(f"❌ Failed to send '{msg}' for account {account['id']} after {MAX_RETRIES} retries.")
    return False

# --- Worker Thread for Each Account ---
def account_loop(account, start_delay):
    """Each account sends every TOTAL_CYCLE seconds, staggered by start_delay"""
    time.sleep(start_delay)  # Stagger start
    while True:
        send_message(account, random.choice(MESSAGES))
        log(f"🕒 Next message for Account {account['id']} in {TOTAL_CYCLE}s (9 min total cycle)")
        time.sleep(TOTAL_CYCLE)

# --- Flask Monitoring ---
@app.route("/ping")
def ping():
    return "OK"

@app.route("/")
def status():
    total = sum(message_counts.values())
    return f"Active accounts: {len(message_counts)} | Total messages sent: {total}"

# --- Main Logic ---
def schedule_jobs():
    accounts = get_accounts()
    if not accounts:
        log("❌ No valid accounts found. Exiting.")
        return

    for i, acc in enumerate(accounts):
        delay = i * GAP_BETWEEN_ACCOUNTS  # 0s, 180s, 360s
        threading.Thread(target=account_loop, args=(acc, delay), daemon=True).start()
        log(f"🧩 Started thread for Account {acc['id']} (starts in {delay}s)")

def run_server():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    log("🚀 Starting bot (3min stagger between accounts, 9min cycle total)")
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(1)
    schedule_jobs()
    while True:
        time.sleep(1)
