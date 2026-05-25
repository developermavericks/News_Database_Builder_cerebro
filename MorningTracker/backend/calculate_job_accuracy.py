
import asyncio
import os
import sys
from sqlalchemy import select, func
from dotenv import load_dotenv

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import get_db_sync, Article, ScrapeJob

load_dotenv('.env.local')

JOB_ID = "e257bff6-8e1d-455b-8059-1fc21c791ace"

def calculate_accuracy(job_id):
    with get_db_sync() as db:
        # Get job info
        job = db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id)).scalars().first()
        if not job:
            print(f"Job {job_id} not found.")
            return

        # Total articles linked to this job
        total_count = db.execute(
            select(func.count(Article.id)).where(Article.scrape_job_id == job_id)
        ).scalar() or 0

        # Articles with "readable" content (full_body exists and > 200 chars)
        readable_count = db.execute(
            select(func.count(Article.id))
            .where(Article.scrape_job_id == job_id)
            .where(Article.full_body.isnot(None))
            .where(func.length(Article.full_body) > 200)
        ).scalar() or 0

        print(f"--- Accuracy Report for Job: {job_id} ---")
        print(f"Sector: {job.sector}")
        print(f"Status: {job.status}")
        print(f"Total Articles Scraped: {total_count}")
        print(f"Articles with Readable Content: {readable_count}")
        
        if total_count > 0:
            accuracy = (readable_count / total_count) * 100
            print(f"Accuracy Rate: {accuracy:.2f}%")
        else:
            print("Accuracy Rate: N/A (No articles scraped)")

if __name__ == "__main__":
    calculate_accuracy(JOB_ID)
