import os
import sqlalchemy
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def purge_junk():
    backend_dir = os.path.join(os.getcwd(), "backend")
    load_dotenv(os.path.join(backend_dir, ".env.local"))
    
    db_url = os.getenv("DATABASE_URL", "sqlite:///news_scraper.db")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            print("--- DATABASE JUNK PURGE STARTED ---")
            
            # Find articles containing CSS patterns
            patterns = ["%@font-face%", "%unicode-range:%", "%/* armenian */%", "%U+1F%"]
            total_deleted = 0
            
            for pattern in patterns:
                # Count before delete
                count = conn.execute(text(f"SELECT count(*) FROM articles WHERE full_body LIKE :pat OR summary LIKE :pat"), {"pat": pattern}).scalar()
                if count > 0:
                    conn.execute(text(f"DELETE FROM articles WHERE full_body LIKE :pat OR summary LIKE :pat"), {"pat": pattern})
                    total_deleted += count
                    print(f"Deleted {count} articles matching pattern: {pattern}")
            
            conn.commit()
            print(f"------------------------------------")
            print(f"PURGE COMPLETE. Total Articles Removed: {total_deleted}")
            print("Your dashboard will now only show clean results from new runs.")
            
    except Exception as e:
        print(f"Error purging junk: {e}")

if __name__ == "__main__":
    purge_junk()
