from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv('backend/.env.local')
url = os.getenv("DATABASE_URL", "postgresql://postgres:password@127.0.0.1:5432/news_scraper").replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(url)

with engine.connect() as conn:
    print("--- Searching for missing jobs by sector ---")
    sectors = ['sports', 'life style']
    for sector in sectors:
        res = conn.execute(text("SELECT id, sector, status FROM scrape_jobs WHERE lower(sector) = :sector ORDER BY started_at DESC LIMIT 3"), {"sector": sector})
        for r in res:
            print(f"ID: {r[0]} | Sector: {r[1]} | Status: {r[2]}")
