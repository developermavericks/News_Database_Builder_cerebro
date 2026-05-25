import asyncio
import os
import sys
import psutil
from sqlalchemy import create_engine, text, update, select
from sqlalchemy.orm import Session
from datetime import datetime

# Add the backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'backend'))

from db.database import ScrapeJob, get_sync_url, get_db
from celery_app import app as celery_app
from dotenv import load_dotenv

async def precise_restart():
    load_dotenv(os.path.join(BASE_DIR, "backend", ".env.local"))
    
    # IDs from the screenshot
    target_ids = [
        "7d25b07f-ed59-4372-842d-17f18bfd9e11",
        "828bbb10-6f4e-42f2-81b7-1b807caad732",
        "5d89e0fc-22eb-4417-a470-0f7d307a7511",
        "8ccd5c19-21db-463a-b1a0-283803c2efb4",
        "578fb84c-0f66-41ff-b815-73431287abbd",
        "74713898-0193-4a66-9956-fa4087ee9a6e",
        "aff4e894-cbd8-4b60-b781-98cf844e6466",
        "2ae06289-b81c-4680-963b-759d7ce07462",
        "3710be40-a9d8-4ece-b9de-d1a8377c0a31",
        "af36fb4a-310c-47b4-81bd-be8e87849d88"
    ]

    # 1. Hard Kill removed to prevent stopping user-initiated workers
    print("Preparing targeted jobs for restart...")

    # 2. Purge Celery queue
    print("Purging Celery queue...")
    # We'll do this via command line after the script or using celery_app if it works
    try:
        celery_app.control.purge()
        print("Purged successfully.")
    except Exception as e:
        print(f"Purge error: {e}")

    # 3. Database Cleanup
    engine = create_engine(get_sync_url())
    with Session(engine) as session:
        # Find all jobs that are not in our target list and cancel them
        # We use a pattern match for each target prefix
        all_jobs = session.query(ScrapeJob).filter(ScrapeJob.status.in_(['running', 'processing', 'pending', 'interrupted', 'Resuming'])).all()
        
        cancelled_count = 0
        resumed_count = 0
        
        for job in all_jobs:
            is_target = job.id in target_ids
            if not is_target:
                print(f"Cancelling non-target job: {job.id} ({job.sector})")
                job.status = 'cancelled'
                job.error = 'Stopped for precise job focus'
                cancelled_count += 1
            else:
                # Target job - ensure it's ready for restart
                job.status = 'pending'
                job.error = None
                job.current_phase = 'Resuming'
                resumed_count += 1
        
        session.commit()
        print(f"Cancelled {cancelled_count} jobs. Prepared {resumed_count} jobs for restart.")

    # 4. Dispatch Targeted Jobs
    async with get_db() as db:
        for job_id in target_ids:
            res = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
            job = res.scalar_one_or_none()
            
            if not job:
                print(f"Target job {job_id} NOT FOUND in DB.")
                continue

            print(f"Dispatching Job: {job.id} ({job.sector})")
            
            # Re-dispatch orchestrator
            celery_app.send_task(
                "scraper.tasks.run_scrape_task",
                args=[
                    job.id, 
                    job.sector, 
                    job.region, 
                    job.date_from.isoformat(), 
                    job.date_to.isoformat(), 
                    job.search_mode, 
                    job.user_id
                ]
            )
            print(f" - Successfully queued {job.sector}")

if __name__ == "__main__":
    asyncio.run(precise_restart())
