# TDT4225 Assignment 2

## Configure and run

1. Install the dependencies with `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and set the MySQL connection values and CSV path.
   Keep `.env` private; it contains the database password.
3. Make sure the target database exists and the configured MySQL user can create,
   insert into, query, and (if using `--reset`) drop tables in it.
4. Run a small trial with `python main.py --reset --limit 1000`.
5. Load the complete CSV with `python main.py --reset` after the trial.

`MYSQL_HOST` should be the VM's address as seen by the computer running Python.
Use `127.0.0.1` when Python runs on the same machine as MySQL. When Python runs
on another computer, use the VM's reachable IP or DNS name and allow that
computer to connect to MySQL on `MYSQL_PORT` (3306 by default). `MYSQL_DATABASE`
must already exist; the loader creates the assignment tables inside it.

`--reset` drops and recreates `Taxi`, `Trip`, and `TrajectoryPoint`, so it
replaces any data in those tables. A run without `--reset` refuses to append a
second import when `Trip` already has rows. The loader streams the CSV and
reports progress every 10,000 source rows.

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
  point count, duration, and Haversine distance for summary queries.
- `Trip.is_invalid` is true when a trip has fewer than three GPS points,
  matching Part 2, Question 7. Trips remain in the database so they can be
  counted and filtered. For the separate eight-point robustness check, query
  using `num_points >= 8`.

For example, count invalid trips with:

```sql
SELECT COUNT(*) FROM Trip WHERE is_invalid = TRUE;
```
