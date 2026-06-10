import psycopg2

conn = psycopg2.connect('postgresql://postgres:password@127.0.0.1:5432/news_scraper')
c = conn.cursor()
job_id = '4d3897bb-5748-4f3d-b97b-b01ff34384be'

print(f"--- Accuracy Analysis for Job {job_id} ---")

c.execute(f"SELECT total_found, total_scraped FROM scrape_jobs WHERE id::text LIKE '%{job_id}%'")
row = c.fetchone()
if row:
    found, scraped = row
    print(f"Total Links Found (Discovery Phase): {found}")
    print(f"Extraction Attempts (Processed Phase): {scraped}")
    if found > 0:
        print(f"Processing Progress: {(scraped/found)*100:.2f}%")

print("\n--- Content Extraction Accuracy ---")
c.execute(f"SELECT count(*) FROM articles WHERE scrape_job_id LIKE '%{job_id}%' AND full_body IS NOT NULL")
extracted = c.fetchone()[0]

c.execute(f"SELECT count(*) FROM articles WHERE scrape_job_id LIKE '%{job_id}%'")
total_saved = c.fetchone()[0]

print(f"Total Unique Articles Discovered & Saved to DB: {total_saved}")
print(f"Articles with Extracted Content (full_body): {extracted}")

if scraped > 0:
    print(f"\nWorker Success Rate (Content Extracted / Attempts): {(extracted/scraped)*100:.2f}%")
