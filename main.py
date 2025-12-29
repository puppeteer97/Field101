import requests
import time
import random
import os
import threading
from datetime import datetime
from flask import Flask

# -----------------------------------
# Configuration
# -----------------------------------
SD_MESSAGES = ["ld", "lD", "Ld", "Lw3"]        # Channel 1 messages
NS_MESSAGES = ["NS", "ns", "Ns", "nS"]        # Channel 2 messages

SD_MIN = 1140
SD_MAX = 1440

NS_MIN = 610
NS_MAX = 730

MAX_RETRIES = 5
RETRY_DELAY = 5

# -----------------------------------
# Setup
# -----------------------------------
app = Flask(__name__)
session = requests.Session()
message_counts = {}

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# -----------------------------------
# Load Account + Channels (NS optional)
# -----------------------------------
def get_account():
    token = os.environ.get("DISCORD_TOKEN")
    channel_sd = os.environ.get("DISCORD_CHANNEL_ID")
    channel_ns = os.environ.get("DISCORD_CHANNEL_ID_2")

    if not token:
        log("❌ Missing DISCORD_TOKEN")
        return None

    if not channel_sd:
        log("❌ Missing DISCORD_CHANNEL_ID (SD channel). Cannot run.")
        return None

    try:
        channel_sd = int(channel_sd)
    except ValueError:
        log("⚠ DISCORD_CHANNEL_ID must be a number")
        return None

    # Track SD channel messages
    message_counts[channel_sd] = 0

    # Handle NS channel (optional)
    ns_available = True
    if not channel_ns:
        log("⚠ DISCORD_CHANNEL_ID_2 missing. NS messages disabled.")
        ns_available = False
    else:
        try:
            channel_ns = int(channel_ns)
            message_counts[channel_ns] = 0
        except ValueError:
            log("⚠ DISCORD_CHANNEL_ID_2 must be a number. NS disabled.")
            ns_available = False

    account = {
        "token": token,
        "channel_sd": channel_sd,
        "channel_ns": channel_ns if ns_available else None,
        "ns_enabled": ns_available,
        "id": 1
    }

    return account

# -----------------------------------
# Send Message Function
# -----------------------------------
def send_message(account, channel_id, msg):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": account["token"],
        "Content-Type": "application/json"
    }
    data = {"content": msg}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.post(url, headers=headers, json=data, timeout=10)
            if r.status_code in [200, 204]:
                message_counts[channel_id] += 1
                log(f"✅ Sent '{msg}' to channel {channel_id}")
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

    log(f"❌ Failed to send '{msg}' after {MAX_RETRIES} attempts")
    return False

# -----------------------------------
# SD Loop
# -----------------------------------
def sd_loop(account):
    cycle = 0
    while True:
        msg = random.choice(SD_MESSAGES)
        send_message(account, account["channel_sd"], msg)
        cycle += 1
        wait = random.randint(SD_MIN, SD_MAX)
        log(f"🔵 SD cycle {cycle} done. Waiting {wait} seconds...")
        time.sleep(wait)

# -----------------------------------
# NS Loop (only if enabled)
# -----------------------------------
def ns_loop(account):
    cycle = 0
    while True:
        msg = random.choice(NS_MESSAGES)
        send_message(account, account["channel_ns"], msg)
        cycle += 1
        wait = random.randint(NS_MIN, NS_MAX)
        log(f"🟣 NS cycle {cycle} done. Waiting {wait} seconds...")
        time.sleep(wait)

# -----------------------------------
# Web Monitor
# -----------------------------------
@app.route("/ping")
def ping():
    return "OK"

@app.route("/")
def status():
    return f"Messages sent: {message_counts}"

# -----------------------------------
# Launch
# -----------------------------------
def schedule_job():
    account = get_account()
    if not account:
        log("❌ No account loaded. Exiting.")
        return

    # Always start SD
    threading.Thread(target=sd_loop, args=(account,), daemon=True).start()

    # Start NS only if available
    if account["ns_enabled"]:
        threading.Thread(target=ns_loop, args=(account,), daemon=True).start()

def run_server():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# -----------------------------------
# Main
# -----------------------------------
if __name__ == "__main__":
    log("🚀 Starting bot (SD always active, NS optional)")

    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(1)

    schedule_job()

    while True:
        time.sleep(1)






