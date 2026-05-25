import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add the backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'backend'))

from db.database import ScrapeJob, get_sync_url

def stop_everything():
    load_dotenv(os.path.join(BASE_DIR, 'backend', '.env.local'))
    
    try:
        # 1. Update Database
        url = get_sync_url()
        print(f"Connecting to {url}...")
        engine = create_engine(url)
        with Session(engine) as session:
            # Cancel all jobs that are not completed or failed
            res = session.query(ScrapeJob).filter(
                ScrapeJob.status.in_(['running', 'processing', 'pending', 'interrupted', 'Resuming'])
            ).all()
            
            if not res:
                print("No active or interrupted jobs found in database.")
            else:
                print(f"Cancelling {len(res)} jobs in database...")
                for job in res:
                    job.status = 'cancelled'
                    job.error = 'Stopped by user request'
                    job.current_phase = 'Terminated'
                session.commit()
                print("Database updated: All active jobs marked as cancelled.")

        # 2. Purge Celery Queue (via command line to avoid dependency issues in script if any)
        print("To purge Celery, you might need to run: celery -A celery_app purge -f")
        
    except Exception as e:
        print(f"Error during shutdown: {e}")

if __name__ == "__main__":
    stop_everything()
