"""
One-time migration: bring the PostgreSQL schema in line with models.py
WITHOUT losing any data.

1. Takes a fresh full backup (backup/postgres_backup_<timestamp>.db)
2. Adds ONLY missing columns (farm_id, car_registry.active)
3. Backfills existing rows: farm_id = 1 (Murang'a - all existing data),
   active = TRUE
4. Sets user 'Mbuthia' (role user) to farm_id = 1 (admin/finance stay NULL)
5. Verifies row counts are identical before/after

Usage: python migrate_pg.py
"""

import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backup_pg_to_sqlite import load_env_file, normalize_url, split_query_params, sanitize_url, main as run_backup

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed")
    sys.exit(1)

load_env_file()
URL = os.environ.get("DATABASE_URL")
if not URL:
    print("ERROR: DATABASE_URL not found (set it or add to .env)")
    sys.exit(1)

# ---------- 1. FRESH BACKUP BEFORE ANY CHANGE ----------
print("=" * 70)
print("STEP 1: Fresh backup BEFORE migration")
print("=" * 70)
run_backup()

# ---------- 2. CONNECT ----------
pg_url, pg_kwargs = split_query_params(normalize_url(URL))
pg = psycopg2.connect(pg_url, connect_timeout=20, **pg_kwargs)
pg.autocommit = True
c = pg.cursor()

print()
print("=" * 70)
print("STEP 2: Schema migration (additive only)")
print("=" * 70)

# tables needing farm_id, and default value for existing rows
FARM_ID_TABLES = [
    "animal_registry",
    "milk_registry",
    "milk_sales_registry",
    "insemination",
    "treatment",
    "feeds_registry",
    "feeds_order_v2",
]

def column_exists(table, column):
    c.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return c.fetchone() is not None

def row_count(table):
    c.execute("SELECT COUNT(*) FROM %s" % table)
    return c.fetchone()[0]

before_counts = {}

# farm_id columns
for t in FARM_ID_TABLES:
    before_counts[t] = row_count(t)
    if column_exists(t, "farm_id"):
        print("skip  farm_id   already present on %s" % t)
    else:
        c.execute("ALTER TABLE %s ADD COLUMN farm_id INTEGER" % t)
        c.execute("UPDATE %s SET farm_id = 1 WHERE farm_id IS NULL" % t)
        print("added farm_id -> 1  on %s" % t)

# admin.farm_id (nullable; users handled separately)
before_counts["admin"] = row_count("admin")
if column_exists("admin", "farm_id"):
    print("skip  farm_id   already present on admin")
else:
    c.execute("ALTER TABLE admin ADD COLUMN farm_id INTEGER")
    print("added farm_id   on admin (users assigned below)")

# car_registry.active
before_counts["car_registry"] = row_count("car_registry")
if column_exists("car_registry", "active"):
    print("skip  active    already present on car_registry")
else:
    c.execute("ALTER TABLE car_registry ADD COLUMN active BOOLEAN DEFAULT TRUE")
    c.execute("UPDATE car_registry SET active = TRUE WHERE active IS NULL")
    print("added active = TRUE  on car_registry")

# ---------- 3. USER FARM ASSIGNMENTS ----------
print()
print("=" * 70)
print("STEP 3: User farm assignments")
print("=" * 70)

# kepha (finance) and admin: keep farm_id NULL (see all farms)
c.execute("UPDATE admin SET farm_id = NULL WHERE username IN ('admin', 'kepha')")
print("admin + kepha (finance): farm_id = NULL (all farms)")

# Mbuthia (role user): all existing data is Murang'a (farm 1)
c.execute("UPDATE admin SET farm_id = 1 WHERE username = 'Mbuthia' AND role = 'user'")
print("Mbuthia (user): farm_id = 1 (Murang'a)")

c.execute("SELECT id, username, role, farm_id FROM admin ORDER BY id")
print("admin users now:")
for r in c.fetchall():
    print("   ", r)

# ---------- 4. VERIFY ----------
print()
print("=" * 70)
print("STEP 4: Verification (row counts unchanged)")
print("=" * 70)

ok = True
c.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_type = 'BASE TABLE'
      AND table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY table_name
""")
all_tables = [r[0] for r in c.fetchall()]

for t in all_tables:
    after = row_count(t)
    before = before_counts.get(t)
    if before is None:
        print("note  %-24s %7d rows (untouched)" % (t, after))
        continue
    good = before == after
    ok &= good
    print(("PASS" if good else "FAIL"), "| %-24s before=%7d after=%7d" % (t, before, after))

for t in FARM_ID_TABLES + ["admin"]:
    if column_exists(t, "farm_id"):
        c.execute("SELECT COUNT(*) FROM %s WHERE farm_id IS NULL" % t)
        nulls = c.fetchone()[0]
        if t == "admin":
            continue
        print("check %s: %d rows with farm_id = 1" % (t, row_count(t) - nulls))

c.execute("SELECT COUNT(*) FROM car_registry WHERE active = TRUE")
print("check car_registry: %d active cars" % c.fetchone()[0])

pg.close()

print()
if ok:
    print("MIGRATION COMPLETE - all row counts preserved, backup taken first")
else:
    print("WARNING: count mismatch detected - investigate before deploying!")
    sys.exit(1)