
import requests
import os
from dotenv import load_dotenv

load_dotenv('backend/.env.local')

BASE_URL = "http://127.0.0.1:8000/api"
EMAIL = os.environ.get("ADMIN_EMAIL", "divyansh@gmail.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "12345")
JOB_ID = "ad77b7e7-f24d-4ad6-a863-29401468cb64"

def stop_job():
    print(f"--- Stopping Job {JOB_ID} ---")
    
    # 1. Login
    try:
        login_resp = requests.post(f"{BASE_URL}/auth/login", data={
            "username": EMAIL,
            "password": PASSWORD
        })
        login_resp.raise_for_status()
        token = login_resp.json()["access_token"]
    except Exception as e:
        print(f"Login Failed: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Delete/Cancel Job
    try:
        # The DELETE endpoint signals cancellation via Redis
        resp = requests.delete(f"{BASE_URL}/scrape/job/{JOB_ID}", headers=headers)
        resp.raise_for_status()
        print(f"Job successfully cancelled and cleaned up.")
    except Exception as e:
        print(f"Failed to cancel job: {e}")

if __name__ == "__main__":
    stop_job()
