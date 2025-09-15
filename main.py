import requests
import time
import random
import os
import threading
from datetime import datetime

# Configuration
MESSAGES = ["ld", "LDROP", "ldrop", "lDrop", "Ldrop"]  # Normal messages
DAILY_MESSAGE = "ldaily"  # Special daily message
MIN_DAILY_INTERVAL = 3 * 60 * 60  # 3 hours between ldailys
CYCLE_STAGGERS = [5 * 60, 6 * 60, 7 * 60]  # 5, 6, 7 minutes stagger for each cycle
# Setup
session = requests.Session()
message_counts = {}

# Load accounts
def get_accounts():
    accounts = []
    for i in range(1, 4):  # 3 accounts
        token = os.environ.get(f"DISCORD_TOKEN_{i}")
        channel_id = os.environ.get(f"DISCORD_CHANNEL_ID_{i}")
        if token and channel_id:
            try:
                channel_id = int(channel_id)
                accounts.append({
                    "token": token,
                    "channel_id": channel_id,
                    "id": i,
                    "last_daily": 0  # Track last time ldaily was sent
                })
                message_counts[channel_id] = 0
            except:
                pass
    return accounts

# Send a message
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
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Sent '{msg}' for account {account['id']}")
            return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error sending '{msg}': {e}")
    return False

# New ldaily timer function
def schedule_ldaily(account):
    def send_ldaily():
        now = time.time()
        if now - account["last_daily"] >= MIN_DAILY_INTERVAL:
            send_message(account, DAILY_MESSAGE)
            account["last_daily"] = now
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Sent ldaily for account {account['id']}")
    # Schedule ldaily after 3 minutes (180 seconds)
    threading.Timer(3 * 60, send_ldaily).start()

# Run cycles indefinitely
def run_cycles(accounts):
    cycle_index = 0
    last_time = time.time()
    while True:
        stagger = CYCLE_STAGGERS[cycle_index]
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔁 Starting cycle {cycle_index + 1} with stagger {stagger//60} minutes")

        # Send messages in this cycle
        for account in accounts:
            send_message(account, random.choice(MESSAGES))
            schedule_ldaily(account)  # Schedule ldaily independently
            time.sleep(stagger)  # Stagger between accounts

        # Prepare for next cycle
        last_time += stagger * len(accounts)
        cycle_index = (cycle_index + 1) % len(CYCLE_STAGGERS)

        # Wait until it's time to start the next cycle
        now = time.time()
        wait_time = max(0, last_time + stagger - now)
        if wait_time > 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Waiting {int(wait_time)} seconds before next cycle")
            time.sleep(wait_time)

if __name__ == "__main__":
    accounts = get_accounts()
    if accounts:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Bot started with {len(accounts)} accounts")
        run_cycles(accounts)
