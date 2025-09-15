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
STAGGERS = [5 * 60, 6 * 60, 7 * 60]  # Stagger times for each cycle in seconds
MIN_DAILY_INTERVAL = 2 * 60 * 60  # 2 hours minimum between ldailys

# Setup
app = Flask(__name__)
session = requests.Session()
message_counts = {}

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

def send_message(account, msg):
    url = f"https://discord.com/api/v10/channels/{account['channel_id']}/messages"
    headers = {
        "Authorization": account["token"],
        "Content-Type": "application/json"
    }
    data = {"content": msg}
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
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error sending message: {e}")
    return False

def run_cycle(accounts, stagger):
    """Run one cycle with given stagger between accounts"""
    for account in accounts:
        msg = random.choice(MESSAGES)
        send_message(account, msg)
        
        # Check ldaily after 5 minutes if allowed
        threading.Thread(target=check_ldaily, args=(account,), daemon=True).start()
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏳ Waiting {stagger//60} minutes before next account")
        time.sleep(stagger)

def check_ldaily(account):
    """Check and send ldaily if 2 hours have passed since last"""
    time.sleep(5 * 60)  # Wait 5 minutes after normal message
    now = time.time()
    if now - account["last_daily"] >= MIN_DAILY_INTERVAL:
        send_message(account, DAILY_MESSAGE)
        account["last_daily"] = now
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 Sent ldaily for account {account['id']}")

def run_cycles(accounts):
    """Continuously run cycles with stagger changes"""
    cycle_index = 0
    while True:
        stagger = STAGGERS[cycle_index]
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Starting cycle {cycle_index + 1} with stagger {stagger//60} minutes\n")
        run_cycle(accounts, stagger)
        
        # Move to next cycle
        cycle_index = (cycle_index + 1) % len(STAGGERS)

# Flask endpoints
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
        
        threading.Thread(target=run_cycles, args=(accounts,), daemon=True).start()
        
        while True:
            time.sleep(3600)  # Keep the script alive
