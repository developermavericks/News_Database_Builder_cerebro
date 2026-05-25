
import os
import sys
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add the backend directory to sys.path to import models
sys.path.append(os.path.abspath(r"f:\Divyansh-Tech-folder\zNews_Database_Builder_updated_final\MorningTracker\backend"))

from db.database import Article, ScrapeJob, get_database_url

async def analyze_job(job_id):
    engine = create_async_engine(get_database_url())
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        # Check job status with partial match
        job_stmt = select(ScrapeJob).where(ScrapeJob.id.like(f"%{job_id}%"))
        job_result = await session.execute(job_stmt)
        job = job_result.scalar_one_or_none()
        
        if not job:
            # Fallback: check if any articles have this job ID as a foreign key prefix
            article_stmt = select(Article).where(Article.scrape_job_id.like(f"%{job_id}%"))
            article_result = await session.execute(article_stmt)
            articles = article_result.scalars().all()
            
            if articles:
                found_id = articles[0].scrape_job_id
                job_stmt = select(ScrapeJob).where(ScrapeJob.id == found_id)
                job_result = await session.execute(job_stmt)
                job = job_result.scalar_one_or_none()
                if job:
                    print(f"Found job {job.id} matching {job_id} via articles.")
                else:
                    print(f"Found {len(articles)} articles but no corresponding job record for {found_id}.")
                    # Create a dummy job object for the report
                    from dataclasses import dataclass
                    @dataclass
                    class DummyJob:
                        id: str
                        sector: str = "Unknown"
                        region: str = "Unknown"
                        status: str = "Inferred"
                        total_scraped: int = 0
                    job = DummyJob(id=found_id, total_scraped=len(articles))
            else:
                print(f"Job {job_id} not found in jobs or articles.")
                return

        print(f"Job ID: {job.id}")
        print(f"Sector: {job.sector}")
        print(f"Region: {job.region}")
        print(f"Status: {job.status}")
        print(f"Total Scraped: {job.total_scraped}")
        
        # Get articles
        article_stmt = select(Article).where(Article.scrape_job_id == job.id)
        article_result = await session.execute(article_stmt)
        articles = article_result.scalars().all()
        
        print(f"Found {len(articles)} articles in database for this job.")
        
        if not articles:
            return

        # Generate Report
        report_path = os.path.join(os.getcwd(), f"job_{job_id}_analysis.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Analysis Report for Job {job_id}\n\n")
            f.write(f"**Sector:** {job.sector}\n")
            f.write(f"**Region:** {job.region}\n")
            f.write(f"**Status:** {job.status} (Interrupted by power cut)\n")
            f.write(f"**Total Articles Extracted:** {len(articles)}\n\n")
            f.write("## Extracted Articles\n\n")
            
            for idx, art in enumerate(articles, 1):
                f.write(f"### {idx}. {art.title}\n")
                f.write(f"- **URL:** {art.url}\n")
                f.write(f"- **Source:** {art.agency or 'Unknown'}\n")
                f.write(f"- **Published At:** {art.published_at}\n")
                if art.summary:
                    f.write(f"- **Summary:** {art.summary}\n")
                else:
                    # If no summary, maybe show a snippet of full_body
                    snippet = (art.full_body[:200] + "...") if art.full_body else "No content extracted."
                    f.write(f"- **Snippet:** {snippet}\n")
                f.write("\n---\n\n")
        
        print(f"Report generated at: {report_path}")

if __name__ == "__main__":
    job_id = "70b4612f"
    asyncio.run(analyze_job(job_id))
