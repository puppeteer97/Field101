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
INTERVAL = 15 * 60           # 15 minutes
STAGGER = 5 * 60             # 5 minutes between accounts
DAILY_INTERVAL = 24*60*60 + 30*60  # 24 hours 30 minutes
DAILY_STAGGER = 3 * 60       # 3 minutes gap between accounts for daily message

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
                accounts.append({"token": token, "channel_id": channel_id, "id": i})
                message_counts[channel_id] = 0
            except:
                pass
    return accounts

def send_message(account, msg):
    url = f"https://discord.com/api/v10/channels/{account['channel_id']}/messages"
    headers = {"Authorization": account['token'], "Content-Type": "application/json"}
    data = {"content": msg}
    
    try:
        r = session.post(url, headers=headers, json=data, timeout=10)
        if r.status_code in [200, 204]:
            message_counts[account['channel_id']] += 1
            return True
        elif r.status_code == 429:
            time.sleep(int(r.headers.get('Retry-After', 60)))
    except:
        pass
    return False

def run_account(account):
    last_daily = time.time() - DAILY_INTERVAL  # allow sending daily immediately on first run
    
    # Stagger start for normal messages
    time.sleep((account['id'] - 1) * STAGGER)
    
    while True:
        # Send normal random message
        send_message(account, random.choice(MESSAGES))
        
        # Check if it's time to send daily message
        now = time.time()
        if now - last_daily >= DAILY_INTERVAL:
            # Additional stagger for daily message between accounts
            time.sleep((account['id'] - 1) * DAILY_STAGGER)
            send_message(account, DAILY_MESSAGE)
            last_daily = now
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sent DAILY '{DAILY_MESSAGE}' for account {account['id']}")
        
        # Wait until next normal message
        time.sleep(INTERVAL)

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
        
        for account in accounts:
            threading.Thread(target=run_account, args=(account,), daemon=True).start()
        
        while True:
            time.sleep(3600)
