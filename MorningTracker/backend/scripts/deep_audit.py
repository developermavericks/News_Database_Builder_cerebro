import os
import re
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def deep_audit():
    load_dotenv("backend/.env.local")
    target_job_id = "101c11fb-809f-4811-bf19-e78801d8e240"
    
    db_url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+psycopg2://")
    engine = create_engine(db_url)
    
    print(f"--- DEEP AUDIT: JOB {target_job_id} ---")
    
    # 1. Total in Job Record
    with engine.connect() as conn:
        job = conn.execute(text("SELECT total_found, total_scraped FROM scrape_jobs WHERE id = :jid"), {"jid": target_job_id}).fetchone()
        if job:
            print(f"Total Discovered (Feed): {job[0]}")
            print(f"Total Scraped (Report): {job[1]}")
            
        # 2. Duplicate Check
        # We check the total unique URLs in the articles table vs the job total
        # This is harder without a full log, but we can look for "Fetch failures" in logs
        
    # 3. Log Analysis (Worker Logs)
    # We look for "Skipping duplicate", "Content too thin", and "Fetch failed"
    log_file = "worker.log"
    if not os.path.exists(log_file):
        log_file = os.path.join("backend", "worker.log")
        
    stats = {"duplicate": 0, "thin": 0, "failed": 0, "saved": 0}
    
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            # Only look at the last 100,000 lines to be fast
            lines = f.readlines()[-100000:]
            for line in lines:
                if "Skipping duplicate" in line: stats["duplicate"] += 1
                elif "rejected: too short" in line or "Content too thin" in line: stats["thin"] += 1
                elif "Fetch failed" in line or "Scrape Proxy Tunnel Failed" in line: stats["failed"] += 1
                elif "Successfully saved article" in line: stats["saved"] += 1

    print("\n--- CAUSE ANALYSIS (Estimated from Worker Logs) ---")
    print(f"Saved: {stats['saved']}")
    print(f"Duplicate (Skipped): {stats['duplicate']}")
    print(f"Rejected (Too Short): {stats['thin']}")
    print(f"Failed (Network): {stats['failed']}")
    
    total = sum(stats.values())
    if total > 0:
        print(f"\nEfficiency: {(stats['saved']/total)*100:.1f}% conversion of unique attempts.")

if __name__ == "__main__":
    deep_audit()
