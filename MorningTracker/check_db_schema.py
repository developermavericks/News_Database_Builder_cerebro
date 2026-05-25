import sqlite3
import os

db_path = "f:\\Divyansh-Tech-folder\\zNews_Database_Builder_updated_final\\MorningTracker\\news_scraper.db"

if not os.path.exists(db_path):
    print(f"Database file not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"- {table[0]}")

# If we have tables, try to search for the ID in all of them if possible, 
# but first let's just see what tables we have.
conn.close()
