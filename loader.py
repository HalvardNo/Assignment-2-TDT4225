"""Clean and batch-load Porto taxi trips and their GPS points."""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from haversine import Unit, haversine


# POLYLINE values can exceed csv's default 128 KiB field limit.
csv.field_size_limit(16 * 1024 * 1024)

CSV_COLUMNS = (
    "TRIP_ID",
    "CALL_TYPE",
    "ORIGIN_CALL",
    "ORIGIN_STAND",
    "TAXI_ID",
    "TIMESTAMP",
    "DAY_TYPE",
    "MISSING_DATA",
    "POLYLINE",
)

INVALID_POINT_THRESHOLD = 3

INSERT_TRIP = """
    INSERT INTO Trip (
        source_row_number, trip_id, taxi_id, call_type, origin_call,
        origin_stand, start_time, missing_data, num_points, duration_sec,
        distance_m, is_invalid
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
INSERT_POINT = """
    INSERT INTO TrajectoryPoint (trip_id, seq, lon, lat)
    VALUES (%s, %s, %s, %s)
"""


def _parse_integer(value, column, line_number, nullable=False):
    """Convert one CSV field to an integer and report malformed values clearly."""
    if value is None or value.strip() == "":
        if nullable:
            return None
        raise ValueError(f"CSV line {line_number}: {column} is empty")
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(
            f"CSV line {line_number}: invalid integer in {column}: {value!r}"
        ) from error


def _parse_boolean(value, line_number):
    """Convert the MISSING_DATA field into a Python boolean."""
    normalized = (value or "").strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(
        f"CSV line {line_number}: invalid MISSING_DATA value: {value!r}"
    )


def _parse_polyline(value, line_number):
    """Parse POLYLINE into validated (longitude, latitude) pairs."""
    try:
        coordinates = json.loads(value or "[]")
    except json.JSONDecodeError as error:
        raise ValueError(f"CSV line {line_number}: invalid POLYLINE JSON") from error

    if not isinstance(coordinates, list):
        raise ValueError(f"CSV line {line_number}: POLYLINE must be a list")

    points = []
    for point in coordinates:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(
                f"CSV line {line_number}: POLYLINE point must be [longitude, latitude]"
            )
        try:
            lon, lat = float(point[0]), float(point[1])
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"CSV line {line_number}: POLYLINE has a non-numeric coordinate"
            ) from error
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError(
                f"CSV line {line_number}: coordinate is outside longitude/latitude bounds"
            )
        points.append((lon, lat))
    return points


def _calculate_distance_m(points):
    """Sum Haversine distances between consecutive GPS points."""
    return sum(
        haversine((lat1, lon1), (lat2, lon2), unit=Unit.METERS)
        for (lon1, lat1), (lon2, lat2) in zip(points, points[1:])
    )


def _fingerprint_source_row(row):
    """Create a compact fingerprint for exact duplicate detection."""
    serialized = json.dumps(
        [row.get(column) for column in CSV_COLUMNS],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).digest()


def _transform_row(row, line_number):
    """Clean a CSV record and return its taxi, trip values, and GPS points."""
    source_trip_id = (row.get("TRIP_ID") or "").strip()
    call_type = (row.get("CALL_TYPE") or "").strip()
    if not source_trip_id:
        raise ValueError(f"CSV line {line_number}: TRIP_ID is empty")
    if len(source_trip_id) > 25:
        raise ValueError(f"CSV line {line_number}: TRIP_ID exceeds 25 characters")
    if call_type not in {"A", "B", "C"}:
        raise ValueError(f"CSV line {line_number}: invalid CALL_TYPE: {call_type!r}")

    taxi_id = _parse_integer(row.get("TAXI_ID"), "TAXI_ID", line_number)
    timestamp = _parse_integer(row.get("TIMESTAMP"), "TIMESTAMP", line_number)
    start_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)
    points = _parse_polyline(row.get("POLYLINE"), line_number)
    num_points = len(points)

    trip_values = (
        line_number - 1,  # Internal CSV row ordinal for batched FK mapping.
        source_trip_id,
        taxi_id,
        call_type,
        _parse_integer(row.get("ORIGIN_CALL"), "ORIGIN_CALL", line_number, nullable=True),
        _parse_integer(row.get("ORIGIN_STAND"), "ORIGIN_STAND", line_number, nullable=True),
        start_time,
        _parse_boolean(row.get("MISSING_DATA"), line_number),
        num_points,
        num_points * 15,
        _calculate_distance_m(points),
        num_points < INVALID_POINT_THRESHOLD,
    )
    return taxi_id, trip_values, points


def _validate_csv_header(fieldnames, path):
    """Fail early if the input CSV does not have the expected columns."""
    if fieldnames is None:
        raise ValueError(f"CSV file is empty: {path}")
    missing_columns = set(CSV_COLUMNS).difference(fieldnames)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSV is missing required columns: {missing}")


def _insert_trip_batch(cursor, trip_batch):
    """Insert trips and map their source row numbers to generated database IDs."""
    cursor.executemany(INSERT_TRIP, trip_batch)
    first_row_number = trip_batch[0][0]
    last_row_number = trip_batch[-1][0]
    cursor.execute(
        """
        SELECT id, source_row_number
        FROM Trip
        WHERE source_row_number BETWEEN %s AND %s
        """,
        (first_row_number, last_row_number),
    )
    ids_by_source_row = {
        source_row_number: trip_id
        for trip_id, source_row_number in cursor.fetchall()
    }
    if len(ids_by_source_row) != len(trip_batch):
        raise RuntimeError("Could not map all inserted trips to their generated IDs")
    return ids_by_source_row


def _insert_point_batch(cursor, point_batch, ids_by_source_row, chunk_size):
    """Insert trajectory points in bounded chunks to limit query size."""
    for start in range(0, len(point_batch), chunk_size):
        chunk = point_batch[start : start + chunk_size]
        values = [
            (ids_by_source_row[source_row], seq, lon, lat)
            for source_row, seq, lon, lat in chunk
        ]
        cursor.executemany(INSERT_POINT, values)


def _flush_batch(cursor, connection, taxi_batch, trip_batch, point_batch, point_chunk_size):
    """Insert one batch in parent-before-child order and commit it."""
    if taxi_batch:
        cursor.executemany(
            "INSERT IGNORE INTO Taxi (taxi_id) VALUES (%s)", taxi_batch
        )
    ids_by_source_row = _insert_trip_batch(cursor, trip_batch)
    _insert_point_batch(cursor, point_batch, ids_by_source_row, point_chunk_size)
    connection.commit()


def load_trips(
    cursor,
    connection,
    csv_path,
    batch_size=500,
    row_limit=None,
    progress_every=10_000,
    point_batch_size=10_000,
):
    """Load rows, tag trips with fewer than three points, and remove exact duplicates.

    Returns (inserted trips, invalid trips, exact duplicate rows removed).
    """
    path = Path(csv_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Taxi CSV file does not exist: {path}")
    if batch_size < 1 or progress_every < 1 or point_batch_size < 1:
        raise ValueError("Batch and progress sizes must be positive integers")
    if row_limit is not None and row_limit < 1:
        raise ValueError("row_limit must be a positive integer")

    inserted = 0
    invalid_trips = 0
    duplicates_removed = 0
    rows_read = 0
    next_progress = progress_every
    seen_fingerprints = set()
    known_taxis = set()
    taxi_batch = []
    trip_batch = []
    point_batch = []

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            _validate_csv_header(reader.fieldnames, path)

            for line_number, row in enumerate(reader, start=2):
                if row_limit is not None and rows_read >= row_limit:
                    break
                rows_read += 1

                fingerprint = _fingerprint_source_row(row)
                if fingerprint in seen_fingerprints:
                    duplicates_removed += 1
                    continue
                seen_fingerprints.add(fingerprint)

                taxi_id, trip_values, points = _transform_row(row, line_number)
                if trip_values[-1]:
                    invalid_trips += 1
                if taxi_id not in known_taxis:
                    taxi_batch.append((taxi_id,))
                    known_taxis.add(taxi_id)

                source_row_number = trip_values[0]
                trip_batch.append(trip_values)
                point_batch.extend(
                    (source_row_number, seq, lon, lat)
                    for seq, (lon, lat) in enumerate(points)
                )
                inserted += 1

                if len(trip_batch) >= batch_size:
                    _flush_batch(
                        cursor, connection, taxi_batch, trip_batch,
                        point_batch, point_batch_size,
                    )
                    taxi_batch.clear()
                    trip_batch.clear()
                    point_batch.clear()
                    while rows_read >= next_progress:
                        print(
                            f"Read {rows_read:,}; inserted {inserted:,}; "
                            f"invalid (< 3 points) {invalid_trips:,}; "
                            f"exact duplicates removed {duplicates_removed:,}",
                            flush=True,
                        )
                        next_progress += progress_every

        if trip_batch:
            _flush_batch(
                cursor, connection, taxi_batch, trip_batch,
                point_batch, point_batch_size,
            )
    except Exception:
        connection.rollback()
        raise

    print(
        f"Inserted {inserted:,} trips; tagged {invalid_trips:,} invalid "
        f"(< 3 points); removed {duplicates_removed:,} exact duplicate rows"
    )
    return inserted, invalid_trips, duplicates_removed
