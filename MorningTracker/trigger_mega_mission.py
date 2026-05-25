
import requests
import json
from datetime import date, timedelta
import os
from dotenv import load_dotenv

# Load env for credentials
load_dotenv('backend/.env.local')

BASE_URL = "http://127.0.0.1:8000/api"
EMAIL = os.environ.get("ADMIN_EMAIL", "divyansh@gmail.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "12345")

def trigger_mission():
    print(f"--- Triggering Mega Intelligence Mission ---")
    
    # 1. Login
    print(f"Logging in as {EMAIL}...")
    try:
        login_resp = requests.post(f"{BASE_URL}/auth/login", data={
            "username": EMAIL,
            "password": PASSWORD
        })
        login_resp.raise_for_status()
        token = login_resp.json()["access_token"]
        print("Login Successful.")
    except Exception as e:
        print(f"Login Failed: {e}")
        return

    # 2. Setup Job Parameters
    today = date.today()
    date_from = today - timedelta(days=29) # Max 30 days
    
    payload = {
        "sector": "mega_intelligence",
        "region": "global",
        "date_from": str(date_from),
        "date_to": str(today),
        "search_mode": "broad"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 3. Start Scrape
    print(f"Starting Scrape for 'mega_intelligence' from {date_from} to {today}...")
    try:
        scrape_resp = requests.post(f"{BASE_URL}/scrape/start", headers=headers, json=payload)
        scrape_resp.raise_for_status()
        data = scrape_resp.json()
        print(f"Mission Enqueued Successfully!")
        print(f"Job ID: {data['job_id']}")
        print(f"Status: {data['status']}")
        print("\nMonitor the progress in the dashboard at http://localhost:5173")
    except Exception as e:
        print(f"Failed to start mission: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    trigger_mission()
