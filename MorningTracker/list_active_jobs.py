
import asyncio
import os
import sys
from sqlalchemy import select

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'backend')))

from db.database import get_db, ScrapeJob

async def main():
    async with get_db() as db:
        res = await db.execute(select(ScrapeJob).where(ScrapeJob.status.in_(['pending', 'running', 'processing'])))
        jobs = res.scalars().all()
        print(f"Found {len(jobs)} active jobs:")
        for j in jobs:
            print(f"{j.id} | {j.sector} | {j.status}")

if __name__ == "__main__":
    asyncio.run(main())
