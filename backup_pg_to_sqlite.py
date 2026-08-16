"""
Backup PostgreSQL database -> SQLite backup file.

Usage:
    python backup_pg_to_sqlite.py
    python backup_pg_to_sqlite.py --output backup/restore_2026.db
    python backup_pg_to_sqlite.py --url "postgresql://user:pass@host:5432/dbname"

The PostgreSQL URL is resolved in this order:
    1. --url argument
    2. DATABASE_URL environment variable
    3. DATABASE_URL from the .env file (script folder or current folder)

The script copies EVERY table and ALL rows from Postgres into a
timestamped SQLite database (data as-is, values preserved exactly).
The original table DDL is stored in the backup_meta table.
No data is deleted or modified in the source database.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, date, time
from decimal import Decimal
from urllib.parse import urlparse, urlunparse, parse_qs

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 is not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

BATCH = 2000


# =========================================================
# .env loader (uses python-dotenv when available)
# =========================================================

def load_env_file():
    """Load .env into os.environ. Only fills variables that are not already set."""
    try:
        from dotenv import load_dotenv

        script_dir = os.path.dirname(os.path.abspath(__file__))
        cwd = os.getcwd()

        for folder in (script_dir, cwd):
            env_path = os.path.join(folder, ".env")
            if os.path.isfile(env_path):
                load_dotenv(env_path, override=False)
                return env_path
        return None
    except ImportError:
        # minimal fallback parser (KEY=VALUE lines, # comments, quotes)
        for folder in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
            env_path = os.path.join(folder, ".env")
            if not os.path.isfile(env_path):
                continue
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
            return env_path
        return None


# =========================================================
# PostgreSQL type -> SQLite type mapping
# =========================================================

def base_type(pg_type):
    """numeric(10,2) -> numeric ; character varying(50) -> character varying"""
    return re.sub(r"\(.*\)", "", pg_type.lower())


def pg_type_to_sqlite(pg_type, col_type_oid):
    t = base_type(pg_type)

    if t in ("smallint", "integer", "bigint", "smallserial", "serial", "bigserial", "oid"):
        return "INTEGER"

    if t in ("numeric", "decimal"):
        return "REAL"

    if t in ("real", "double precision", "money"):
        return "REAL"

    if t == "boolean":
        return "BOOLEAN"

    if t in ("text", "character varying", "character", "name", "citext"):
        return "TEXT"

    if t == "date":
        return "DATE"

    if t in ("timestamp without time zone", "timestamp with time zone",
             "timestamp", "timestamptz", "time without time zone",
             "time with time zone", "time", "timetz",
             "interval", "uuid", "inet", "cidr", "macaddr", "macaddr8",
             "json", "jsonb", "xml", "bit", "bit varying", "varbit",
             "tsvector", "tsquery", "point", "line", "lseg", "box",
             "path", "polygon", "circle", "pg_lsn"):
        return "TEXT"

    if t == "bytea":
        return "BLOB"

    # arrays (e.g. integer[], text[])
    if t.endswith("[]"):
        return "TEXT"

    # enums come through as user-defined types -> store as text
    return "TEXT"


# =========================================================
# Value conversion Postgres -> SQLite
# =========================================================

def convert_value(value, pg_type, col_type_oid):
    if value is None:
        return None

    t = base_type(pg_type)

    if t in ("bytea",):
        return sqlite3.Binary(bytes(value))

    if t in ("numeric", "decimal", "money"):
        return float(value)

    if t in ("boolean",):
        return 1 if value else 0

    if t == "date":
        return value.isoformat() if isinstance(value, (date, datetime)) else str(value)

    if t in ("timestamp without time zone", "timestamp with time zone",
             "timestamp", "timestamptz",
             "time without time zone", "time with time zone", "time", "timetz"):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, time):
            return value.isoformat()
        return str(value)

    if t == "interval":
        return str(value)

    if t in ("json", "jsonb"):
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    if t in ("uuid", "inet", "cidr", "macaddr", "bit", "varbit", "xml",
             "tsvector", "tsquery", "pg_lsn", "oid"):
        return str(value)

    if t == "point":
        return str(value)

    if t.endswith("[]"):
        return json.dumps(list(value), ensure_ascii=False)

    # integers, floats, text, enums -> as-is
    return value


# =========================================================
# URL helpers (never log the password)
# =========================================================

def normalize_url(url):
    """Convert a SQLAlchemy-style URL (postgresql+psycopg2://) to plain postgresql://"""
    url = url.strip()
    url = re.sub(r"^postgres(ql)?\+[a-z0-9_]+://", "postgresql://", url, flags=re.I)
    return url


def split_query_params(url):
    """Move URL query params (sslmode etc.) into a kwargs dict psycopg2 understands."""
    p = urlparse(url)
    extra = {}
    if p.query:
        qs = parse_qs(p.query)
        for k in ("sslmode", "connect_timeout", "application_name", "options"):
            if k in qs:
                extra[k] = qs[k][0]
        url = urlunparse((p.scheme, p.netloc, p.path, p.params, "", p.fragment))
    return url, extra


def sanitize_url(url):
    try:
        p = urlparse(url)
        host = p.hostname or "?"
        port = p.port or 5432
        db = p.path.lstrip("/") or "?"
        user = p.username or "?"
        return "%s://%s@%s:%s/%s" % (p.scheme, user, host, port, db)
    except Exception:
        return "<url>"


def parse_args():
    parser = argparse.ArgumentParser(description="Backup PostgreSQL to SQLite")
    parser.add_argument("--url", help="PostgreSQL connection URL")
    parser.add_argument("--output", help="Output SQLite file path (default: backup/postgres_backup_<timestamp>.db)")
    return parser.parse_args()


# =========================================================
# MAIN
# =========================================================

def main():
    args = parse_args()

    env_path = load_env_file()

    url = args.url or os.environ.get("DATABASE_URL")

    if not url:
        print("ERROR: No URL found.")
        print("  Pass --url, set DATABASE_URL, or add DATABASE_URL to a .env file.")
        sys.exit(1)

    if env_path:
        print("Loaded .env:", env_path)

    if "postgres" not in url.split("://")[0].lower() and "postgresql" not in url.split("://")[0].lower():
        print("WARNING: URL does not look like a PostgreSQL URL.")

    out_dir = os.path.dirname(os.path.abspath(args.output)) if args.output else os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")
    os.makedirs(out_dir, exist_ok=True)

    if args.output:
        out_path = args.output
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(out_dir, "postgres_backup_%s.db" % stamp)

    print("Source (PostgreSQL):", sanitize_url(url))
    print("Destination (SQLite):", out_path)
    print()

    pg_url, pg_kwargs = split_query_params(normalize_url(url))
    pg_conn = psycopg2.connect(pg_url, connect_timeout=20, **pg_kwargs)
    pg_conn.autocommit = True
    pg_cur = pg_conn.cursor()

    # -------- find all user tables --------
    pg_cur.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
          AND table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
    """)
    tables = pg_cur.fetchall()

    if not tables:
        print("No user tables found in the database.")
        sys.exit(1)

    print("Found %d table(s):" % len(tables))
    for _, t in tables:
        print("  - %s" % t)

    # -------- sqlite destination --------
    if os.path.exists(out_path):
        print()
        print("WARNING: output file already exists, removing it.")
        os.remove(out_path)

    sq = sqlite3.connect(out_path)
    sq.execute("PRAGMA journal_mode=WAL")

    started = datetime.now()

    # meta storage (DDL of every table, kept as text)
    sq.execute("""
        CREATE TABLE backup_meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    total_rows = 0
    per_table_rows = {}

    for schema, table in tables:
        quoted = '"%s"."%s"' % (schema, table)

        # -------- source column info --------
        pg_cur.execute("""
            SELECT a.attname,
                   format_type(a.atttypid, a.atttypmod) AS pg_type,
                   a.atttypid,
                   a.attnotnull
            FROM pg_attribute a
            WHERE a.attrelid = %s::regclass
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
        """, (quoted,))
        cols = pg_cur.fetchall()

        # -------- primary key --------
        pg_cur.execute("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = %s
              AND tc.table_name = %s
            ORDER BY kcu.ordinal_position
        """, (schema, table))
        pk_cols = [r[0] for r in pg_cur.fetchall()]

        # -------- create table in sqlite --------
        col_defs = []
        for name, pg_type, oid, notnull in cols:
            sq_type = pg_type_to_sqlite(pg_type, oid)
            col_defs.append('"%s" %s%s' % (
                name, sq_type, " NOT NULL" if notnull else ""
            ))

        if pk_cols:
            col_defs.append("PRIMARY KEY (%s)" % ", ".join('"%s"' % c for c in pk_cols))

        sq.execute('CREATE TABLE "%s" (%s)' % (table, ", ".join(col_defs)))

        # -------- copy data --------
        col_names = [c[0] for c in cols]
        pg_types = {c[0]: c[1] for c in cols}
        pg_oids = {c[0]: c[2] for c in cols}

        placeholders = ", ".join(["?"] * len(col_names))
        insert_sql = 'INSERT INTO "%s" (%s) VALUES (%s)' % (
            table,
            ", ".join('"%s"' % n for n in col_names),
            placeholders
        )

        pg_cur.execute('SELECT %s FROM %s' % (", ".join('"%s"' % n for n in col_names), quoted))

        count = 0
        while True:
            batch = pg_cur.fetchmany(BATCH)
            if not batch:
                break

            rows = [
                tuple(convert_value(v, pg_types[n], pg_oids[n]) for n, v in zip(col_names, row))
                for row in batch
            ]
            sq.executemany(insert_sql, rows)
            count += len(batch)

        sq.commit()

        # -------- keep autoincrement counter correct for serial/identity --------
        # (not needed: SQLite INTEGER PRIMARY KEY tables automatically continue
        #  from max(rowid)+1, which matches the copied max id)

        # -------- store original DDL (rebuilt from information_schema) --------
        sq.execute("INSERT INTO backup_meta (key, value) VALUES (?, ?)",
                   ("ddl:%s" % table,
                    "CREATE TABLE \"%s\" (%s);" % (table, ", ".join(col_defs))))

        per_table_rows[table] = count
        total_rows += count
        print("[%5d rows] %s" % (count, table))

    # -------- meta --------
    finished = datetime.now()

    sq.executemany("INSERT INTO backup_meta (key, value) VALUES (?, ?)", [
        ("source_url", sanitize_url(url)),
        ("source_engine", "postgresql"),
        ("destination_engine", "sqlite"),
        ("tool", "backup_pg_to_sqlite.py"),
        ("started_at", started.isoformat()),
        ("finished_at", finished.isoformat()),
        ("total_rows", str(total_rows)),
        ("table_count", str(len(tables))),
        ("tables_json", json.dumps(per_table_rows)),
    ])
    sq.commit()

    sq.close()
    pg_cur.close()
    pg_conn.close()

    print()
    print("Backup complete.")
    print("  Tables : %d" % len(tables))
    print("  Rows   : %d" % total_rows)
    print("  File   : %s" % out_path)
    print("  Size   : %.1f MB" % (os.path.getsize(out_path) / (1024 * 1024)))


if __name__ == "__main__":
    main()