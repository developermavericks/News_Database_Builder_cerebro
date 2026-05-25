import os
import sys
import psutil
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add the backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'backend'))

from db.database import ScrapeJob, get_sync_url

def hard_kill():
    load_dotenv(os.path.join(BASE_DIR, 'backend', '.env.local'))
    
    # 1. Update Database (just in case)
    try:
        url = get_sync_url()
        engine = create_engine(url)
        with Session(engine) as session:
            active_jobs = session.query(ScrapeJob).filter(
                ScrapeJob.status.in_(['running', 'processing', 'pending', 'Resuming'])
            ).all()
            for job in active_jobs:
                job.status = 'cancelled'
            session.commit()
            print(f"Marked {len(active_jobs)} jobs as cancelled in DB.")
    except Exception as e:
        print(f"DB Update error: {e}")

    # 2. Kill all python processes that look like workers/scrapers
    print("Searching for active worker/scraper processes...")
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if not cmdline: continue
            
            cmd_str = " ".join(cmdline).lower()
            # Look for celery or scraper related keywords
            if 'python' in cmd_str and ('celery' in cmd_str or 'worker' in cmd_str or 'scraper' in cmd_str or 'start.py' in cmd_str):
                if proc.info['pid'] != current_pid:
                    print(f"Killing process {proc.info['pid']}: {cmd_str}")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    print("Hard kill complete.")

if __name__ == "__main__":
    hard_kill()
