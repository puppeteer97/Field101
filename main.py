import requests
import time
import random
import os
import threading
from datetime import datetime
from flask import Flask

# Configuration
MESSAGES = ["SD", "sd", "Sd", "sD"]  # ✅ Message set
STAGGER_BETWEEN_ACCOUNTS = 180       # ✅ 180 seconds between each account
MAX_RETRIES = 5                      # Retry attempts
RETRY_DELAY = 5                      # Delay between retries

# Setup
app = Flask(__name__)
session = requests.Session()
message_counts = {}

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# --- Load Accounts (all share the same channel) ---
def get_accounts():
    accounts = []
    shared_channel_id = os.environ.get("DISCORD_CHANNEL_ID")
    if not shared_channel_id:
        log("❌ No DISCORD_CHANNEL_ID found in environment!")
        return accounts
    
    try:
        shared_channel_id = int(shared_channel_id)
    except ValueError:
        log("⚠ Invalid DISCORD_CHANNEL_ID (must be a number)")
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
            r = session.post(url, headers=headers, json=data, timeout=10)
            if r.status_code in [200, 204]:
                message_counts[account['channel_id']] += 1
                log(f"✅ Sent '{msg}' for account {account['id']}")
                return True
            elif r.status_code == 429:
                retry_after = int(r.headers.get('Retry-After', 60))
                log(f"⚠ Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                log(f"⚠ Failed with status {r.status_code}")
        except requests.exceptions.Timeout:
            log(f"⏱ Timeout on attempt {attempt}")
        except requests.exceptions.ConnectionError:
            log(f"🔌 Connection error on attempt {attempt}")
        except Exception as e:
            log(f"❌ Unexpected error on attempt {attempt}: {e}")
        
        if attempt < MAX_RETRIES:
            log(f"🔄 Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
    log(f"❌ Failed to send '{msg}' after {MAX_RETRIES} attempts for account {account['id']}")
    return False

# --- Cycle Logic ---
def run_cycle(accounts):
    for i, account in enumerate(accounts):
        send_message(account, random.choice(MESSAGES))
        log(f"🕒 Sent message for account {account['id']}")
        if i < len(accounts) - 1:
            log(f"⏱ Waiting {STAGGER_BETWEEN_ACCOUNTS} seconds before next account")
            time.sleep(STAGGER_BETWEEN_ACCOUNTS)

def run_cycles(accounts):
    cycle_index = 0
    while True:
        log(f"🔄 Starting cycle {cycle_index + 1} (180-second stagger)")
        run_cycle(accounts)
        log(f"✅ Cycle {cycle_index + 1} complete. Restarting...")
        cycle_index += 1

# --- Web Monitoring ---
@app.route("/ping")
def ping():
    return "OK"

@app.route("/")
def status():
    return f"Active accounts: {len(message_counts)} | Total messages sent: {sum(message_counts.values())}"

def run_server():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# --- Job Scheduling ---
def schedule_jobs():
    accounts = get_accounts()
    if not accounts:
        log("❌ No valid accounts found. Exiting.")
        return
    threading.Thread(target=run_cycles, args=(accounts,), daemon=True).start()

# --- Main ---
if __name__ == "__main__":
    log("🚀 Starting bot (shared channel, SD messages, 180s stagger)")
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(1)
    schedule_jobs()
    while True:
        time.sleep(1)
