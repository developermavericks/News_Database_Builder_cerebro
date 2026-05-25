import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Get the directory of this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'backend'))

from db.database import ScrapeJob, get_sync_url

def cancel_specific_job(job_id_part):
    try:
        engine = create_engine(get_sync_url())
        with Session(engine) as session:
            job = session.query(ScrapeJob).filter(ScrapeJob.id.like(f'%{job_id_part}%')).first()
            
            if not job:
                print(f"Job {job_id_part} not found.")
                return

            print(f"Targeting Job: {job.id} | Current Status: {job.status}")
            job.status = 'cancelled'
            job.error = 'Stopped by user'
            job.current_phase = 'Terminated'
            
            session.commit()
            print(f"Successfully marked Job {job.id} as CANCELLED.")
            
    except Exception as e:
        print(f"Error cancelling job: {e}")

if __name__ == "__main__":
    cancel_specific_job('70b4612f')
