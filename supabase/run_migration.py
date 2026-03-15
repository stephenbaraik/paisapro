"""
Applies the initial schema migration to Supabase.
Run once: python supabase/run_migration.py

Requires in .env either:
  DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
OR both:
  SUPABASE_URL=https://PROJECT.supabase.co
  SUPABASE_DB_PASSWORD=your_password
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    os.system(f"{sys.executable} -m pip install psycopg2-binary")
    import psycopg2

# Accept either a full DATABASE_URL or derive from SUPABASE_URL + SUPABASE_DB_PASSWORD
db_url = os.getenv("DATABASE_URL", "")

if not db_url:
    supabase_url = os.getenv("SUPABASE_URL", "")
    db_password = os.getenv("SUPABASE_DB_PASSWORD", "")

    if not supabase_url or not db_password:
        print("ERROR: Add one of the following to your .env:")
        print("  DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres")
        print("  OR: SUPABASE_URL + SUPABASE_DB_PASSWORD")
        sys.exit(1)

    project_ref = supabase_url.replace("https://", "").split(".")[0]
    db_url = f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres"

host = db_url.split("@")[-1].split(":")[0]
print(f"Connecting to: {host}")

sql_file = Path(__file__).parent / "migrations" / "001_initial_schema.sql"
sql = sql_file.read_text(encoding="utf-8")

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql)
    cur.close()
    conn.close()
    print("Migration applied successfully!")
except Exception as e:
    print(f"Migration failed: {e}")
    sys.exit(1)
