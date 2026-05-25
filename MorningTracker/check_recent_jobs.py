import os
import sys
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session

# Get the directory of this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'backend'))

from db.database import ScrapeJob, get_sync_url

def check_recent_jobs():
    try:
        engine = create_engine(get_sync_url())
        with Session(engine) as session:
            jobs = session.query(ScrapeJob).order_by(desc(ScrapeJob.started_at)).limit(5).all()
            
            print("==================================================")
            print(" MOST RECENT JOBS")
            print("==================================================")
            for job in jobs:
                print(f" ID: {job.id} | Status: {job.status} | Phase: {job.current_phase}")
                print(f" Sector: {job.sector} | Region: {job.region}")
                print(f" Started: {job.started_at}")
                print("-" * 50)
            
    except Exception as e:
        print(f"Error checking jobs: {e}")

if __name__ == "__main__":
    check_recent_jobs()
