from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv('backend/.env.local')
url = os.getenv("DATABASE_URL", "postgresql://postgres:password@127.0.0.1:5432/news_scraper").replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(url)

with engine.connect() as conn:
    res = conn.execute(text("SELECT id, sector, total_found, total_scraped, status, error, started_at FROM scrape_jobs ORDER BY started_at DESC LIMIT 5"))
    jobs = [dict(r._mapping) for r in res]
    
    print("--- Recent Jobs ---")
    for j in jobs:
        print(f"ID: {j['id']} | Sector: {j['sector']} | Found: {j['total_found']} | Scraped: {j['total_scraped']} | Status: {j['status']} | Error: {j['error']}")
    
    if jobs:
        latest_id = jobs[0]['id']
        print(f"\n--- Analysis for Latest Job {latest_id} ---")
        # Check unique articles count for this job
        count_res = conn.execute(text("SELECT count(*) FROM articles WHERE scrape_job_id = :jid"), {"jid": latest_id})
        count = count_res.scalar()
        print(f"Unique Articles in DB for this job: {count}")
        
        # Check if articles have body
        body_res = conn.execute(text("SELECT count(*) FROM articles WHERE scrape_job_id = :jid AND full_body IS NOT NULL AND length(full_body) > 100"), {"jid": latest_id})
        with_body = body_res.scalar()
        print(f"Articles with readable body (>100 chars): {with_body}")
