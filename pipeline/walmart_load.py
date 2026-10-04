"""Full reload of the walmart schema from the CSVs in walmart_dataset/data/.

Usage: python -m pipeline.walmart_load
"""

import csv

from psycopg import sql

from pipeline.db import ROOT, connect

DATA_DIR = ROOT / "walmart_dataset" / "data"
TABLES = ["customers", "stores", "products", "employees", "orders", "order_items"]


def main() -> None:
    with connect() as conn, conn.transaction():
        # Truncate and reload together so readers never see a half-loaded dataset.
        conn.execute(
            sql.SQL("TRUNCATE {}").format(sql.SQL(", ").join(sql.Identifier("walmart", t) for t in TABLES))
        )
        for table in TABLES:
            path = DATA_DIR / f"{table}.csv"
            with path.open(newline="") as f:
                columns = next(csv.reader(f))  # map by header name, not position
            copy_stmt = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)").format(
                sql.Identifier("walmart", table), sql.SQL(", ").join(map(sql.Identifier, columns))
            )
            with conn.cursor() as cur, cur.copy(copy_stmt) as copy, path.open("rb") as f:
                while chunk := f.read(1 << 20):
                    copy.write(chunk)
            count = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("walmart", table))).fetchone()[0]
            print(f"{table}: {count} rows")


if __name__ == "__main__":
    main()
