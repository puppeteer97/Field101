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
STAGGER = 5 * 60        # 5 minutes between accounts for normal messages
MIN_DAILY_INTERVAL = 60 * 60  # 1 hour minimum between ldailys
LDROP_TRIGGER = ["LDROP", "ldrop", "lDrop", "Ldrop"]  # Messages that trigger ldaily

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
                    "id": i,
                    "last_daily": 0  # Track last ldaily time
                })
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
        elif r.status_code == 429:  # Rate limited
            time.sleep(int(r.headers.get('Retry-After', 60)))
    except:
        pass
    return False

def run_account(account):
    time.sleep((account['id'] - 1) * STAGGER)  # stagger normal messages
    
    while True:
        msg = random.choice(MESSAGES)
        send_message(account, msg)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sent '{msg}' for account {account['id']}")
        
        # Check if message triggers ldaily
        now = time.time()
        if msg in LDROP_TRIGGER and now - account["last_daily"] >= MIN_DAILY_INTERVAL:
            time.sleep(2 * 60)  # wait 2 minutes after LDROP
            send_message(account, DAILY_MESSAGE)
            account["last_daily"] = time.time()
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
            time.sleep(3600)  # Keep main thread alive
