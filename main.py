import requests
import time
import random
import os
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask

# Configuration
MESSAGES = ["ld", "LDROP", "ldrop","lDrop"]
INTERVAL = 15 * 60  # 15 minutes
STAGGER = 5 * 60   # 5 minutes between accounts

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

def send_message(account):
    url = f"https://discord.com/api/v10/channels/{account['channel_id']}/messages"
    headers = {"Authorization": account['token'], "Content-Type": "application/json"}
    data = {"content": random.choice(MESSAGES)}
    
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
    time.sleep((account['id'] - 1) * STAGGER)
    while True:
        send_message(account)
        time.sleep(INTERVAL)

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
            time.sleep(3600)  # Sleep for 1 hour chunks