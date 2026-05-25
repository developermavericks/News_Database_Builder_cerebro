import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add the backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'backend'))

from db.database import ScrapeJob, get_sync_url
from celery_app import app as celery_app

def cancel_and_revoke(job_id_prefix):
    load_dotenv(os.path.join(BASE_DIR, 'backend', '.env.local'))
    
    try:
        # 1. Update Database
        engine = create_engine(get_sync_url())
        with Session(engine) as session:
            job = session.query(ScrapeJob).filter(ScrapeJob.id.like(f"{job_id_prefix}%")).first()
            
            if not job:
                print(f"Job prefix {job_id_prefix} not found in DB.")
            else:
                full_id = job.id
                print(f"Cancelling Job in DB: {full_id} ({job.sector})")
                job.status = 'cancelled'
                job.error = 'Stopped by user from queue'
                job.current_phase = 'Terminated'
                session.commit()
                print("Database status updated to cancelled.")

                # 2. Revoke active tasks in Celery
                print(f"Attempting to revoke active tasks for job {full_id}...")
                inspect = celery_app.control.inspect()
                active = inspect.active()
                
                if active:
                    for worker, tasks in active.items():
                        for task in tasks:
                            # Look for job_id in args
                            if full_id in str(task.get('args', '')):
                                print(f"Revoking active task {task['id']} on {worker}")
                                celery_app.control.revoke(task['id'], terminate=True)
                
                # 3. Purge reserved tasks (just in case)
                reserved = inspect.reserved()
                if reserved:
                    for worker, tasks in reserved.items():
                        for task in tasks:
                            if full_id in str(task.get('args', '')):
                                print(f"Revoking reserved task {task['id']} on {worker}")
                                celery_app.control.revoke(task['id'], terminate=True)

                print("Revoke signals sent.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        jid = sys.argv[1]
    else:
        jid = "cc32cf35"
    cancel_and_revoke(jid)
