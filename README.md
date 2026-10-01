# TDT4225 Assignment 2

## Configure and run

1. Install the dependencies with `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and set the MySQL connection values and CSV path.
   Keep `.env` private; it contains the database password.
3. Make sure the target database exists and the configured MySQL user can query
   it. The loader also needs permission to create and insert into tables; reset
   additionally needs permission to drop them.
4. Run `python main.py` to execute the read-only query set in `queries.py` against
   the existing database. This is the default and does not need the CSV path.
5. To import into an empty database, run `python main.py --load --limit 1000`
   for a small trial, then `python main.py --load` for the full CSV.

`MYSQL_HOST` should be the VM's address as seen by the computer running Python.
Use `127.0.0.1` when Python runs on the same machine as MySQL. When Python runs
on another computer, use the VM's reachable IP or DNS name and allow that
computer to connect to MySQL on `MYSQL_PORT` (3306 by default). `MYSQL_DATABASE`
must already exist; the loader creates the assignment tables inside it.

`python main.py --load --reset` drops and recreates `Taxi`, `Trip`, and
`TrajectoryPoint`, replacing all data in those tables. `--reset` is rejected
unless `--load` is also present. A load without `--reset` refuses to append a
second import when `Trip` already has rows. The loader streams the CSV and
reports progress every 10,000 source rows. Do not use the reset command for the
database that already contains the uploaded assignment data.

`queries.py` contains the read-only answers for assignment questions 1–10 as
`QUERY_1` through `QUERY_10` (`QUERY_4A` and `QUERY_4B` cover the two parts of
question 4). `run_queries` prints all answers in order. Duration-dependent
queries calculate elapsed time as `max(num_points - 1, 0) * 15` seconds. The
schema has no source end timestamp, so questions 8 and 10 estimate it from the
GPS sampling interval. Trips marked `missing_data` can have less accurate
duration estimates.

The loader stores this corrected duration for future imports. To fix the
`duration_sec` values in an already loaded database without reloading or
dropping trips, run `python main.py --repair-duration` once. This updates only
that column and is safe to rerun.

The query set uses MySQL 8 features (CTEs and `LAG`) and `ST_Distance_Sphere`
for the location and circular-trip calculations.

## Data model and cleaning

- `Trip.id` is the auto-increment primary key. `Trip.trip_id` stores the source
  CSV identifier and is indexed but not unique because source IDs can collide.
- `source_row_number` is an internal unique CSV row ordinal used to associate
  batched trips with their generated IDs and trajectory points.
- Exact duplicate source rows are removed using a SHA-256 fingerprint; distinct
  rows with the same source `TRIP_ID` are retained.
- `DAY_TYPE` is omitted because it is constant in this dataset. Unix timestamps
  are converted to UTC `DATETIME` values in `Trip.start_time`.
- Each polyline coordinate is stored in `TrajectoryPoint`. `Trip` stores the
  point count, duration, and Haversine distance for summary queries. Distance
  is `NULL` for trips with fewer than two points because no segment can be
  measured.
- `Trip.is_invalid` is true when a trip has fewer than three GPS points,
  matching Part 2, Question 7. Trips remain in the database so they can be
  counted and filtered. For the separate eight-point robustness check, query
  using `num_points >= 8`.

For example, count invalid trips with:

```sql
SELECT COUNT(*) FROM Trip WHERE is_invalid = TRUE;
```
