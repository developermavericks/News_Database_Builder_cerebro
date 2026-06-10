import requests
import json
import argparse
from datetime import date, timedelta
import os
import time
from dotenv import load_dotenv

# Load env for credentials
load_dotenv('backend/.env.local')

BASE_URL = "http://127.0.0.1:8000/api"
EMAIL = os.environ.get("ADMIN_EMAIL", "divyansh@gmail.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "12345")

# The 11 sectors to scrape overnight
SECTORS = [
    "AI", "Tech", "Foods and Drinks", "Healthcare", "Travel",
    "Consultancies", "Startups", "Lifestyle", "Policies", 
    "Stock Market", "Real Estate"
]

def wait_for_queue(token):
    headers = {"Authorization": f"Bearer {token}"}
    print("Checking if workers are free...", end=" ")
    while True:
        try:
            resp = requests.get(f"{BASE_URL}/scrape/jobs", headers=headers)
            jobs = resp.json()
            active = sum(1 for j in jobs if j.get('status') in ['pending', 'running', 'processing'])
            if active == 0:
                print("Workers are free!")
                return
            print(f"[{active} active jobs remaining] Waiting 60s...", end=" ", flush=True)
            time.sleep(60)
        except Exception as e:
            print(f"Error checking jobs: {e}")
            time.sleep(60)

def trigger_mission(lookback_days: int, skip_sectors: list):
    print(f"--- Triggering Sequential Mega Mission (11 Sectors) [Lookback: {lookback_days} days] ---")
    if skip_sectors:
        print(f"User requested to explicitly skip: {', '.join(skip_sectors)}")
    
    # 1. Login
    print(f"Logging in as {EMAIL}...")
    try:
        login_resp = requests.post(f"{BASE_URL}/auth/login", data={
            "username": EMAIL,
            "password": PASSWORD
        })
        login_resp.raise_for_status()
        token = login_resp.json()["access_token"]
        print("Login Successful.\n")
    except Exception as e:
        print(f"Login Failed: {e}")
        return

    # 2. Date Setup
    today = date.today()
    # If the user selects a 1-day lookback, subtract 0 (today only).
    # If they select 30 days, subtract 29 (to include today).
    date_from = today - timedelta(days=max(0, lookback_days - 1))
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 3. Sequential Dispatch
    for i, sector in enumerate(SECTORS, 1):
        print(f"\n--- Mission {i}/{len(SECTORS)}: {sector.upper()} ---")
        
        # Explicitly skip if specified in command line args
        if sector.lower() in skip_sectors:
            print(f"Skipping {sector.upper()} as explicitly requested by --skip argument.")
            continue
            
        # Check if this sector was already processed TODAY
        try:
            resp = requests.get(f"{BASE_URL}/scrape/jobs", headers=headers)
            jobs = resp.json()
            
            # Check if there is any job for this sector created today
            today_str = date.today().isoformat()
            already_done = False
            for j in jobs:
                if j.get("sector", "").lower() == sector.lower():
                    status = j.get("status")
                    started_at = j.get("started_at") or ""
                    
                    # If it is currently active, skip it
                    if status in ['pending', 'running', 'processing']:
                        already_done = True
                        break
                    
                    # If ANY job was started for this sector today (even if completed or interrupted), skip it
                    if started_at.startswith(today_str):
                        already_done = True
                        break
                        
            if already_done:
                print(f"Skipping {sector.upper()} because a job for it already exists today.")
                continue
        except Exception as e:
            pass

        wait_for_queue(token)
        
        payload = {
            "sector": sector,
            "region": "global",
            "date_from": str(date_from),
            "date_to": str(today),
            "search_mode": "broad"
        }
        
        try:
            scrape_resp = requests.post(f"{BASE_URL}/scrape/start", headers=headers, json=payload)
            scrape_resp.raise_for_status()
            data = scrape_resp.json()
            print(f"Job Enqueued! ID: {data['job_id']}")
        except Exception as e:
            print(f"Failed to start mission for {sector}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")

    print("\n✅ All 11 sectors have been successfully sequenced and processed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger Sequential Mega Mission")
    parser.add_argument("--lookback", type=int, default=30, help="Number of days to look back (default: 30)")
    parser.add_argument("--skip", type=str, default="", help="Comma-separated list of sectors to skip (e.g., 'ai,consultancies')")
    args = parser.parse_args()
    
    skip_list = [s.strip().lower() for s in args.skip.split(",")] if args.skip else []
    trigger_mission(args.lookback, skip_list)
