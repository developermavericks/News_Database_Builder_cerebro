import os
import sys
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

# Get the directory of this script (F:\...\MorningTracker)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'backend'))

try:
    from db.database import Article, get_sync_url
except ImportError:
    # Fallback for different folder structures
    sys.path.append(BASE_DIR)
    from backend.db.database import Article, get_sync_url

def calculate_accuracy(job_id_part):
    try:
        engine = create_engine(get_sync_url())
        with Session(engine) as session:
            # Find articles for this job
            total = session.query(func.count(Article.id)).filter(Article.scrape_job_id.like(f'%{job_id_part}%')).scalar()
            
            # Readable: full_body length > 200 characters
            readable = session.query(func.count(Article.id)).filter(
                Article.scrape_job_id.like(f'%{job_id_part}%'),
                Article.full_body != None,
                func.length(Article.full_body) > 200
            ).scalar()
            
            accuracy = (readable / total * 100) if total > 0 else 0
            
            print("==================================================")
            print(f" REPORT FOR JOB: {job_id_part}")
            print("==================================================")
            print(f" Total Articles Captured: {total}")
            print(f" Readable Articles:       {readable}")
            print(f" Scraping Accuracy:       {accuracy:.2f}%")
            print("==================================================")
    except Exception as e:
        print(f"Error calculating accuracy: {e}")

if __name__ == "__main__":
    target_job = '0d0e1765'
    if len(sys.argv) > 1:
        target_job = sys.argv[1]
    calculate_accuracy(target_job)
