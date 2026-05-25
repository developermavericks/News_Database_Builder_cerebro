import os
import sqlalchemy
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import redis

def run_diagnostic():
    backend_dir = os.path.join(os.getcwd(), "backend")
    load_dotenv(os.path.join(backend_dir, ".env.local"))
    
    target_job_id = "f663cfd4-0221-4659-9f11-325ecee4d347" 
    
    db_url = os.getenv("DATABASE_URL", "sqlite:///news_scraper.db")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            print(f"--- DIAGNOSTIC FOR JOB: {target_job_id} ---")
            
            # Total Articles for this job
            query = text("SELECT count(*) FROM articles WHERE scrape_job_id = :jid")
            count = conn.execute(query, {"jid": target_job_id}).scalar()
            print(f"Successfully saved articles for this job: {count}")
            
            # Junk check for this job
            junk_keywords = ["Access Denied", "Forbidden", "Robot Check", "Cloudflare"]
            for kw in junk_keywords:
                j_query = text("SELECT count(*) FROM articles WHERE scrape_job_id = :jid AND full_body LIKE :pat")
                j_count = conn.execute(j_query, {"jid": target_job_id, "pat": f"%{kw}%"}).scalar()
                print(f" - Contains '{kw}': {j_count}")

            # Average length for this job
            avg_len = conn.execute(text("SELECT avg(length(full_body)) FROM articles WHERE scrape_job_id = :jid"), {"jid": target_job_id}).scalar()
            print(f"Average Article Length: {int(avg_len or 0)} chars")

    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    run_diagnostic()
