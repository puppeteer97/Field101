import requests
import time
import random
import os
import threading
import schedule
from datetime import datetime
from flask import Flask

# Configuration
MESSAGES = ["ld", "LDROP", "ldrop", "lDrop", "Ldrop"]
DAILY_MESSAGE = "ldaily"
STAGGERS = [5 * 60, 6 * 60, 7 * 60]  # 5, 6, 7 minutes in each cycle
MIN_DAILY_INTERVAL = 2 * 60 * 60  # 2 hours between ldailys
LDAY_DELAY_AFTER_NORMAL = 3 * 60   # 3 minutes delay after normal message
MAX_RETRIES = 5                    # More retries for robustness
RETRY_DELAY = 5                    # Shorter delay between retries

# Setup
app = Flask(__name__)
session = requests.Session()
message_counts = {}

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def get_accounts():
    accounts = []
    for i in range(1, 4):
        token = os.environ.get(f"DISCORD_TOKEN_{i}")
        channel_id = os.environ.get(f"DISCORD_CHANNEL_ID_{i}")
        if token and channel_id:
            try:
                channel_id = int(channel_id)
                accounts.append({
                    "token": token,
                    "channel_id": channel_id,
                    "id": i,
                    "last_daily": 0,
                    "pending_ldaily": False
                })
                message_counts[channel_id] = 0
            except ValueError:
                log(f"⚠ Invalid channel ID for account {i}")
    return accounts

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

def run_ldaily(account):
    while True:
        if account["pending_ldaily"]:
            now = time.time()
            if now - account["last_daily"] >= MIN_DAILY_INTERVAL:
                log(f"⏳ Waiting {LDAY_DELAY_AFTER_NORMAL//60} mins before sending ldaily for account {account['id']}")
                time.sleep(LDAY_DELAY_AFTER_NORMAL)
                send_message(account, DAILY_MESSAGE)
                account["last_daily"] = time.time()
                log(f"📊 Sent ldaily for account {account['id']}")
            account["pending_ldaily"] = False
        time.sleep(10)

def run_cycle(accounts, stagger):
    for i, account in enumerate(accounts):
        send_message(account, random.choice(MESSAGES))
        account["pending_ldaily"] = True
        log(f"🕒 Normal message sent for account {account['id']}")
        if i < len(accounts) - 1:
            log(f"⏱ Waiting {stagger//60} mins before next account")
            time.sleep(stagger)

def run_cycles(accounts):
    cycle_index = 0
    while True:
        stagger = STAGGERS[cycle_index % len(STAGGERS)]
        log(f"🔄 Starting cycle {cycle_index + 1} with stagger {stagger//60} minutes")
        run_cycle(accounts, stagger)
        log(f"⏱ Waiting {stagger//60} minutes before next cycle")
        time.sleep(stagger)
        cycle_index += 1

@app.route("/ping")
def ping():
    return "OK"

@app.route("/")
def status():
    return f"Active: {len(message_counts)} | Total: {sum(message_counts.values())}"

def run_server():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def schedule_jobs():
    accounts = get_accounts()
    for account in accounts:
        threading.Thread(target=run_ldaily, args=(account,), daemon=True).start()
    threading.Thread(target=run_cycles, args=(accounts,), daemon=True).start()

if __name__ == "__main__":
    log("🚀 Starting bot")
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(1)
    schedule_jobs()
    while True:
        schedule.run_pending()
        time.sleep(1)
