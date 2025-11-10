import requests
import time
import random
import os
import threading
from datetime import datetime
from flask import Flask

# Configuration
MESSAGES = ["SD", "sd", "Sd", "sD"]  # ✅ Message set
STAGGER_BETWEEN_ACCOUNTS = 500       # ✅ 500 seconds between each message
MAX_RETRIES = 5                      # Retry attemptss
RETRY_DELAY = 5                      # Delay between retries

# Setup
app = Flask(__name__)
session = requests.Session()
message_counts = {}

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# --- Load Single Account ---
def get_account():
    account = None
    channel_id = os.environ.get("DISCORD_CHANNEL_ID")
    token = os.environ.get("DISCORD_TOKEN")

    if not channel_id:
        log("❌ No DISCORD_CHANNEL_ID found in environment!")
        return None

    try:
        channel_id = int(channel_id)
    except ValueError:
        log("⚠ Invalid DISCORD_CHANNEL_ID (must be a number)")
        return None

    if not token:
        log("⚠ Missing DISCORD_TOKEN")
        return None

    message_counts[channel_id] = 0
    account = {
        "token": token,
        "channel_id": channel_id,
        "id": 1
    }

    return account

# --- Message Sending ---
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

# --- Single Account Loop ---
def run_cycle(account):
    cycle_index = 0
    while True:
        msg = random.choice(MESSAGES)
        send_message(account, msg)
        cycle_index += 1
        log(f"✅ Cycle {cycle_index} complete. Waiting {STAGGER_BETWEEN_ACCOUNTS} seconds before next message...")
        time.sleep(STAGGER_BETWEEN_ACCOUNTS)

# --- Web Monitoring ---
@app.route("/ping")
def ping():
    return "OK"

@app.route("/")
def status():
    return f"Active account: 1 | Total messages sent: {sum(message_counts.values())}"

def run_server():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# --- Job Scheduling ---
def schedule_job():
    account = get_account()
    if not account:
        log("❌ No valid account found. Exiting.")
        return
    threading.Thread(target=run_cycle, args=(account,), daemon=True).start()

# --- Main ---
if __name__ == "__main__":
    log("🚀 Starting bot (single account, SD messages, 500s interval)")
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(1)
    schedule_job()
    while True:
        time.sleep(1)

