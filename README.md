# TDT4225 Assignment 2

## Configure and run

1. Install the dependencies with `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and set the MySQL connection values and CSV
   path. Keep `.env` private; it contains the database password.
3. Make sure the target database exists and the configured MySQL user can query
   it. Loading also requires permission to create and insert into tables.
4. Run `python main.py` to execute the queries configured in
   `ASSIGNMENT_QUERIES` in `queries.py` against the existing database.
5. To import the full CSV into an empty database, run `python main.py --load`.

`MYSQL_HOST` should be the VM's address as seen by the computer running Python.
Use `127.0.0.1` when Python runs on the same machine as MySQL. When Python runs
on another computer, use the VM's reachable IP or DNS name and allow that
computer to connect to MySQL on `MYSQL_PORT` (3306 by default). `MYSQL_DATABASE`
must already exist; the loader creates the assignment tables inside it.

`python main.py --load --reset` drops and recreates `Taxi`, `Trip`, and
`TrajectoryPoint`, replacing their data. `--reset` requires `--load`, and a
load without `--reset` refuses to append a second import when `Trip` already
has rows. Do not use reset on the database that already contains the uploaded
assignment data.

The loader stores duration as `max(num_points - 1, 0) * 15` seconds and sums
Haversine distances between consecutive points. Distance is `NULL` for trips
with fewer than two points. The schema has no source end timestamp, so queries
that need it estimate it from the stored duration. Trips marked
`missing_data` can have less accurate duration estimates.

The query set uses MySQL 8 features (CTEs and `LAG`) and `ST_Distance_Sphere`
for location and circular-trip calculations. Assignment queries exclude rows
where `is_outlier = TRUE`; Question 7 specifically counts trips with fewer than
three GPS points across the full dataset.

## Data model and cleaning

- `Trip.id` is the auto-increment primary key. `Trip.trip_id` stores the source
  CSV identifier and is indexed but not unique because source IDs can collide.
- `source_row_number` is an internal unique source-row ordinal used to link
  batched trips to their generated IDs and trajectory points.
- The loader compares all nine source fields when removing exact duplicate
  rows. Distinct rows with the same `TRIP_ID` are retained.
- `DAY_TYPE` is omitted from the database because it is constant in the
  dataset. `TIMESTAMP` is Unix time in UTC; the loader converts it to a
  timezone-free Porto local `DATETIME` in `Trip.start_time` using
  `Europe/Lisbon`, including daylight-saving changes.
- `POLYLINE` is parsed into rows in `TrajectoryPoint`. `Trip` stores the point
  count, duration, distance, and outlier flag.
- `Trip.is_outlier` is true if a trip has fewer than three points, lasts at
  least two hours, has an average speed above 120 km/h, has at least 20 points
  and a total distance below 200 m, or contains a point more than 300 km from
  Porto City Hall. Outliers remain stored in the database.

Count flagged outliers with:

```sql
SELECT COUNT(*) FROM Trip WHERE is_outlier = TRUE;
```
