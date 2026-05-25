
import asyncio
import os
import sys
from datetime import datetime
from sqlalchemy import select, update
from dotenv import load_dotenv

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(r"f:\Divyansh-Tech-folder\zNews_Database_Builder_updated_final\MorningTracker\backend"))

from db.database import get_db, ScrapeJob, Article
from celery_app import app as celery_app

async def resume_job(job_id_prefix):
    load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env.local"))
    
    async with get_db() as db:
        # Find the job
        res = await db.execute(select(ScrapeJob).where(ScrapeJob.id.like(f"{job_id_prefix}%")))
        job = res.scalar_one_or_none()
        
        if not job:
            print(f"Job with prefix {job_id_prefix} not found.")
            return

        print(f"Resuming Job: {job.id}")
        print(f"Sector: {job.sector} | Region: {job.region}")
        print(f"Current Status: {job.status}")
        
        # Reset job status to pending to allow orchestrator to start
        await db.execute(
            update(ScrapeJob)
            .where(ScrapeJob.id == job.id)
            .values(
                status='pending',
                current_phase='Resuming',
                error=None
            )
        )
        await db.commit()
        
        # Dispatch the orchestrator task
        # This will re-run discovery and streaming extraction
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
        
        print(f"Successfully dispatched resume task for job {job.id}")
        print("The orchestrator will re-discover articles and attempt to scrape those that are missing or incomplete.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        job_id = "70b4612f"
    
    asyncio.run(resume_job(job_id))
