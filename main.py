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

# Cycle configurations
CYCLES = [
    {"interval": 15 * 60, "stagger": 5 * 60},
    {"interval": 18 * 60, "stagger": 6 * 60},
    {"interval": 21 * 60, "stagger": 7 * 60}
]

MIN_DAILY_INTERVAL = 3 * 60 * 60  # 3 hours between ldailys
MAX_RETRIES = 3           # Number of retries if message fails
RETRY_DELAY = 10          # Delay between retries in seconds

# Flask setup
app = Flask(__name__)
session = requests.Session()
message_counts = {}

# Load accounts from environment variables
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

# Send a message with retry logic
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

# Run normal messages in alternating cycles
def run_normal(account):
    cycle_index = 0  # Start with first cycle
    while True:
        cycle = CYCLES[cycle_index]
        interval = cycle["interval"]
        stagger = cycle["stagger"]
        
        # Initial delay based on account id
        time.sleep((account['id'] - 1) * stagger)
        
        # Send normal message
        msg = random.choice(MESSAGES)
        send_message(account, msg)
        
        # Start ldaily thread after sending message
        threading.Thread(target=send_ldaily, args=(account,), daemon=True).start()
        
        # Wait for the interval before the next message
        time.sleep(interval)
        
        # Move to next cycle
        cycle_index = (cycle_index + 1) % len(CYCLES)

# Send ldaily 3 minutes after normal message
def send_ldaily(account):
    time.sleep(3 * 60)
    now = time.time()
    if now - account["last_daily"] >= MIN_DAILY_INTERVAL:
        send_message(account, DAILY_MESSAGE)
        account["last_daily"] = now
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 Sent ldaily for account {account['id']}")

# Flask routes
@app.route("/ping")
def ping():
    return "OK"

@app.route("/")
def status():
    return f"Active: {len(message_counts)} | Total: {sum(message_counts.values())}"

def run_server():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# Main program
if __name__ == "__main__":
    accounts = get_accounts()
    if accounts:
        threading.Thread(target=run_server, daemon=True).start()
        time.sleep(1)
        
        for account in accounts:
            threading.Thread(target=run_normal, args=(account,), daemon=True).start()
        
        while True:
            time.sleep(3600)  # Keep running indefinitely
