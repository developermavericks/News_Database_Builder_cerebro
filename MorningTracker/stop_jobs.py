import os
import sys
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session

# Get the directory of this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'backend'))

from db.database import ScrapeJob, get_sync_url

def stop_all_active_jobs():
    try:
        engine = create_engine(get_sync_url())
        with Session(engine) as session:
            # Find active jobs
            active_jobs = session.query(ScrapeJob).filter(ScrapeJob.status.in_(['running', 'processing', 'pending'])).all()
            
            if not active_jobs:
                print("No active jobs found to stop.")
                return

            print(f"Stopping {len(active_jobs)} active jobs...")
            for job in active_jobs:
                print(f" - Stopping Job: {job.id} ({job.sector} - {job.region})")
                job.status = 'cancelled'
                job.error = 'Stopped by user'
                job.current_phase = 'Terminated'
            
            session.commit()
            print("Successfully stopped all active jobs.")
            
    except Exception as e:
        print(f"Error stopping jobs: {e}")

if __name__ == "__main__":
    stop_all_active_jobs()
