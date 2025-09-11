import requests
import time
import random
import os
import threading
from datetime import datetime
from flask import Flask

# Configuration
MESSAGES = ["ld", "LDROP", "ldrop", "lDrop", "Ldrop"]  # Normal messages
DAILY_MESSAGE = "ldaily"  # Special daily message
INTERVAL = 15 * 60        # 15 minutes between normal messages
STAGGER = 5 * 60          # 5 minutes delay between starting each account
MIN_DAILY_INTERVAL = 3 * 60 * 60  # 3 hours between ldailys
MAX_RETRIES = 3           # Number of retries if message fails
RETRY_DELAY = 10          # Delay between retries in seconds

# Flask setup to keep the script running online
app = Flask(__name__)
session = requests.Session()  # Reuse HTTP session
message_counts = {}  # Track how many messages sent per channel

# Load all accounts from environment variables
def get_accounts():
    accounts = []
    for i in range(1, 4):  # Supports 3 accounts
        token = os.environ.get(f"DISCORD_TOKEN_{i}")
        channel_id = os.environ.get(f"DISCORD_CHANNEL_ID_{i}")
        if token and channel_id:
            try:
                channel_id = int(channel_id)
                accounts.append({
                    "token": token,
                    "channel_id": channel_id,
                    "id": i,
                    "last_daily": 0  # Last time ldaily was sent
                })
                message_counts[channel_id] = 0
            except:
                pass
    return accounts

# Send a message to a Discord channel with retry logic
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
            elif r.status_code == 429:  # Rate limit error
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

# Normal messages running in the main loop
def run_normal(account):
    time.sleep((account['id'] - 1) * STAGGER)  # Delay start for each account
    
    while True:
        start_time = time.time()
        msg = random.choice(MESSAGES)
        send_message(account, msg)
        
        elapsed = time.time() - start_time
        wait_time = INTERVAL - elapsed
        if wait_time > 0:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏳ Waiting {int(wait_time)} seconds until next normal message (account {account['id']})")
            time.sleep(wait_time)

# ldaily messages running in a separate loop for each account
def run_ldaily(account):
    while True:
        now = time.time()
        if now - account["last_daily"] >= MIN_DAILY_INTERVAL:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏳ Waiting 5 minutes before sending ldaily (account {account['id']})")
            time.sleep(5 * 60)  # Delay before sending ldaily
            send_message(account, DAILY_MESSAGE)
            account["last_daily"] = time.time()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 Sent ldaily for account {account['id']}")
        time.sleep(60)  # Check every minute

# Flask routes
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
            threading.Thread(target=run_ldaily, args=(account,), daemon=True).start()
        
        while True:
            time.sleep(3600)  # Keep the script running indefinitely
