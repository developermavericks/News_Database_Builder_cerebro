import asyncio
from datetime import date
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "MorningTracker", "backend"))

from scraper.engine import run_scrape_job
from db.database import get_db_sync, ScrapeJob
import uuid

async def test_pool():
    job_id = str(uuid.uuid4())
    print(f"Starting test job: {job_id}")
    
    # Create a dummy job in DB
    with get_db_sync() as db:
        from db.database import ScrapeJob
        db.add(ScrapeJob(id=job_id, sector="Technology", region="India", status="pending", user_id="test_user"))
        db.commit()

    # Run discovery for 1 day, 2 keywords
    # This should spawn 2 tasks in the queue and min(2, 495) workers
    result = await run_scrape_job(
        job_id=job_id,
        sector="Technology",
        region="India",
        date_from=date.today(),
        date_to=date.today(),
        search_mode="sector",
        user_id="test_user"
    )
    
    print(f"Job result: {result}")

if __name__ == "__main__":
    asyncio.run(test_pool())
