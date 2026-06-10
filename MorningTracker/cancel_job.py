import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:password@127.0.0.1:5432/news_scraper')
    c = conn.cursor()
    job_id_prefix = 'abab1503'
    
    # Check the job first
    c.execute(f"SELECT id, sector, status, total_found, total_scraped FROM scrape_jobs WHERE id::text LIKE '{job_id_prefix}%'")
    job = c.fetchone()
    
    if job:
        print(f"Found Job: {job[0]} | Sector: {job[1]} | Status: {job[2]} | Found: {job[3]} | Extracted: {job[4]}")
        # Cancel it
        c.execute(f"UPDATE scrape_jobs SET status = 'cancelled' WHERE id::text LIKE '{job_id_prefix}%'")
        conn.commit()
        print("Job has been forcefully stopped/cancelled.")
    else:
        print("Job not found.")
except Exception as e:
    print(f"Error: {e}")
