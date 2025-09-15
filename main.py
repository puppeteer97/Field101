import requests
import time
import random
import os
import threading
from datetime import datetime
from flask import Flask

# Configuration
MESSAGES = ["ld", "LDROP", "ldrop", "lDrop", "Ldrop"]
DAILY_MESSAGE = "ldaily"
CYCLES = [
    {"stagger": 5 * 60},  # Cycle 1 stagger of 5 minutes
    {"stagger": 6 * 60},  # Cycle 2 stagger of 6 minutes
    {"stagger": 7 * 60}   # Cycles 3 stagger of 7 minutes
]
MAX_RETRIES = 3
RETRY_DELAY = 10

# Setup
app = Flask(__name__)
session = requests.Session()
message_counts = {}

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
                    "id": i
                })
                message_counts[channel_id] = 0
            except:
                pass
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
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Sent '{msg}' for account {account['id']}")
                return True
            elif r.status_code == 429:
                retry_after = int(r.headers.get('Retry-After', 60))
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Failed with status {r.status_code}")
        except requests.exceptions.Timeout:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏱ Timeout on attempt {attempt}")
        except requests.exceptions.ConnectionError:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔌 Connection error on attempt {attempt}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Unexpected error on attempt {attempt}: {e}")
        
        if attempt < MAX_RETRIES:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Failed to send '{msg}' after {MAX_RETRIES} attempts for account {account['id']}")
    return False

def run_bot(accounts):
    cycle_index = 0
    last_send_times = [0] * len(accounts)  # ✅ CHANGED: Track last send time per account

    while True:
        cycle = CYCLES[cycle_index]
        stagger = cycle["stagger"]
        
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Starting Cycle {cycle_index + 1} with stagger {stagger//60} mins\n")

        for idx, account in enumerate(accounts):
            # ✅ CHANGED: Wait until last send time plus previous stagger
            if idx == 0:
                wait_time = 0 if last_send_times[idx] == 0 else stagger
            else:
                wait_time = stagger
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏳ Account {account['id']} waiting {wait_time} seconds before sending")
            time.sleep(wait_time)

            msg = random.choice(MESSAGES)
            send_message(account, msg)
            last_send_times[idx] = time.time()  # ✅ CHANGED: Update last send time

        # ✅ CHANGED: Prepare for next cycle
        cycle_index = (cycle_index + 1) % len(CYCLES)

@app.route("/ping")
def ping():
    return "OK"

@app.route("/")
def status():
    return f"Active: {len(message_counts)} | Total: {sum(message_counts.values())}"

def run_server():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    accounts = get_accounts()
    if accounts:
        threading.Thread(target=run_server, daemon=True).start()
        time.sleep(1)
        
        threading.Thread(target=run_bot, args=(accounts,), daemon=True).start()
        
        while True:
            time.sleep(3600)

