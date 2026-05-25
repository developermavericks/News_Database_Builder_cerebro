import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add the backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'backend'))

from db.database import ScrapeJob, get_sync_url

def cleanup_database():
    load_dotenv(os.path.join(BASE_DIR, 'backend', '.env.local'))
    
    try:
        url = get_sync_url()
        print(f"Connecting to {url}...")
        engine = create_engine(url)
        
        with engine.connect() as conn:
            # 1. Count jobs to delete
            res = conn.execute(text("SELECT count(*) FROM scrape_jobs WHERE status IN ('cancelled', 'interrupted')"))
            job_count = res.scalar()
            
            if job_count == 0:
                print("No cancelled or interrupted jobs found.")
                return

            print(f"Found {job_count} jobs to delete.")
            
            # 2. Delete associated articles first (just in case cascade is not set)
            print("Deleting associated articles...")
            article_del = conn.execute(text("""
                DELETE FROM articles 
                WHERE scrape_job_id IN (
                    SELECT id FROM scrape_jobs WHERE status IN ('cancelled', 'interrupted')
                )
            """))
            print(f"Deleted {article_del.rowcount} articles.")

            # 3. Delete the jobs
            print("Deleting jobs...")
            job_del = conn.execute(text("DELETE FROM scrape_jobs WHERE status IN ('cancelled', 'interrupted')"))
            print(f"Deleted {job_del.rowcount} jobs.")
            
            conn.commit()
            print("Database cleanup complete. You can now start fresh.")

    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup_database()
