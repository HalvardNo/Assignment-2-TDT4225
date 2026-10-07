"""Query the database by default; load or replace data only when requested."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from tabulate import tabulate

from DbConnector import DbConnector
from loader import load_trips
from queries import run_queries
from schema import create_tables, drop_tables

load_dotenv(Path(__file__).resolve().with_name(".env"))


def print_database_summary(cursor):
    cursor.execute("SHOW TABLES")
    print("\nTables in the database:")
    for (table_name,) in cursor.fetchall():
        print(f"- {table_name}")

    cursor.execute(
        """
        SELECT id, trip_id, taxi_id, start_time,
               num_points, duration_sec, distance_m, is_outlier
        FROM Trip
        ORDER BY id DESC
        LIMIT 5
        """
    )
    rows = cursor.fetchall()
    print("\nFive most recently inserted trips:")
    print(
        tabulate(
            rows,
            headers=[
                "id", "source trip id", "taxi", "start time",
                "points", "duration (s)", "distance (m)", "outlier",
            ],
            tablefmt="github",
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description="Query the Porto taxi database, or explicitly load its CSV."
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="import the CSV (without this flag, main only runs read-only queries)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="drop existing assignment tables before loading; requires --load",
    )
    args = parser.parse_args()
    if args.reset and not args.load:
        parser.error("--reset requires --load; it drops the existing assignment data")

    if not args.load:
        with DbConnector() as db:
            run_queries(db.cursor)
        return

    csv_path = os.getenv("PORTO_CSV_PATH")
    if not csv_path or csv_path == "replace-with-your-porto-csv-path":
        raise ValueError(
            "Set PORTO_CSV_PATH in .env to the path of the Porto taxi CSV file."
        )
    csv_file = Path(csv_path).expanduser()
    if not csv_file.is_file():
        raise FileNotFoundError(f"Taxi CSV file does not exist: {csv_file}")

    with DbConnector() as db:
        if args.reset:
            print("Reset requested: dropping the Taxi, Trip and TrajectoryPoint tables.")
            drop_tables(db.cursor, db.db_connection)

        create_tables(db.cursor, db.db_connection)

        if not args.reset:
            db.cursor.execute("SELECT COUNT(*) FROM Trip")
            existing_trips = db.cursor.fetchone()[0]
            if existing_trips:
                raise RuntimeError(
                    f"Trip already contains {existing_trips:,} rows. "
                    "Refusing to append a duplicate import; rerun with --reset "
                    "to replace the assignment tables."
                )

        inserted, outlier_trips, duplicates_removed = load_trips(
            db.cursor,
            db.db_connection,
            csv_file,
        )
        print(f"\nImport complete: {inserted:,} trips loaded.")
        print(f"Trips flagged as outliers: {outlier_trips:,}.")
        print(f"Exact duplicate source rows removed: {duplicates_removed:,}.")
        print_database_summary(db.cursor)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, ConnectionError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
