from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv('backend/.env.local')
url = os.getenv("DATABASE_URL", "postgresql://postgres:password@127.0.0.1:5432/news_scraper").replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(url)

job_ids = [
    "f50a8365", "cc32cf35", "7f75857e", "55cb26d9", "63845bdd",
    "5828af9d", "3f1109d7", "1dc53851", "55fd3aa3", "cc318e18"
]

with engine.connect() as conn:
    print("--- Status of Jobs from Screenshot ---")
    for jid in job_ids:
        res = conn.execute(text("SELECT id, sector, status, total_found, total_scraped FROM scrape_jobs WHERE id LIKE :jid"), {"jid": f"{jid}%"})
        job = res.fetchone()
        if job:
            print(f"ID: {job[0]} | Sector: {job[1]} | Status: {job[2]} | Found: {job[3]} | Scraped: {job[4]}")
        else:
            print(f"ID: {jid} | NOT FOUND")
