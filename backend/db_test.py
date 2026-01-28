import os
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
    )


def main():
    load_env(Path(__file__).with_name(".env"))

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # INSERT (upsert-style)
            cur.execute(
                """
                INSERT INTO SL_sports (name, slug)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET slug = EXCLUDED.slug
                RETURNING id, name, slug
                """,
                ("Baseball", "baseball"),
            )
            inserted = cur.fetchone()
            print("INSERT/UPSERT:", inserted)

            # SELECT
            cur.execute(
                "SELECT id, name, slug FROM SL_sports WHERE name = %s",
                ("Baseball",),
            )
            selected = cur.fetchone()
            print("SELECT:", selected)

            # UPDATE
            cur.execute(
                "UPDATE SL_sports SET slug = %s WHERE name = %s RETURNING id, name, slug",
                ("baseball-mlb", "Baseball"),
            )
            updated = cur.fetchone()
            print("UPDATE:", updated)


if __name__ == "__main__":
    main()
