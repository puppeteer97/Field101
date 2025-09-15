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
INTERVAL = 15 * 60      # 15 minutes between normal messages
STAGGER = 5 * 60        # 5 minutes stagger between accounts
MAX_RETRIES = 3
RETRY_DELAY = 10

# Flask setup
app = Flask(__name__)
session = requests.Session()
message_counts = {}

# ✅ CHANGED: Initialize last_daily to 0 for each account
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
                    "last_daily": 0  # ✅ CHANGED: Track last time ldaily was sent
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

# ✅ CHANGED: Normal messages loop now triggers ldaily in a separate thread
def run_normal(account):
    time.sleep((account['id'] - 1) * STAGGER)
    while True:
        start_time = time.time()
        msg = random.choice(MESSAGES)
        send_message(account, msg)
        
        # ✅ ADDED: Schedule ldaily check 5 minutes after normal message
        threading.Thread(target=schedule_ldaily, args=(account,), daemon=True).start()
        
        elapsed = time.time() - start_time
        wait_time = INTERVAL - elapsed
        if wait_time > 0:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏳ Waiting {int(wait_time)} seconds until next normal message (account {account['id']})")
            time.sleep(wait_time)

# ✅ ADDED: Separate function to handle ldaily timing independently
def schedule_ldaily(account):
    time.sleep(5 * 60)  # ✅ Wait 5 minutes after normal message
    now = time.time()
    if now - account["last_daily"] >= 2 * 60 * 60:  # ✅ Check if last ldaily was at least 2 hours ago
        send_message(account, DAILY_MESSAGE)
        account["last_daily"] = now
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 Sent ldaily for account {account['id']}")
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏱ Skipped ldaily for account {account['id']} (sent recently)")

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
        
        for account in accounts:
            threading.Thread(target=run_normal, args=(account,), daemon=True).start()
        
        while True:
            time.sleep(3600)
