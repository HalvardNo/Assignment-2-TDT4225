"""Answers to Assignment 2 questions using the Porto taxi MySQL database."""

from tabulate import tabulate


# Each query is (title, SQL statement, output column headers). Keep question
# numbers aligned with the assignment so the full set can be run in order.
QUERY_1 = (
    "1. Number of taxis, trips, and GPS points",
    """
    SELECT
        (SELECT COUNT(*) FROM Taxi) AS taxi_count,
        (SELECT COUNT(*) FROM Trip) AS trip_count,
        (SELECT COUNT(*) FROM TrajectoryPoint) AS gps_point_count
    """,
    ("Taxis", "Trips", "GPS points"),
)

QUERY_2 = (
    "2. Average number of trips per taxi",
    """
    SELECT ROUND(AVG(trip_count), 2) AS average_trips_per_taxi
    FROM (
        SELECT taxi_id, COUNT(*) AS trip_count
        FROM Trip
        GROUP BY taxi_id
    ) AS taxi_trip_counts
    """,
    ("Average trips per taxi",),
)

QUERY_3 = (
    "3. Top 20 taxis by number of trips",
    """
    SELECT taxi_id, COUNT(*) AS trip_count
    FROM Trip
    GROUP BY taxi_id
    ORDER BY trip_count DESC, taxi_id
    LIMIT 20
    """,
    ("Taxi ID", "Trips"),
)

QUERY_4A = (
    "4a. Most used call type for each taxi (ties are included)",
    """
    WITH taxi_call_counts AS (
        SELECT taxi_id, call_type, COUNT(*) AS trip_count
        FROM Trip
        GROUP BY taxi_id, call_type
    ),
    taxi_max_counts AS (
        SELECT taxi_id, MAX(trip_count) AS max_trip_count
        FROM taxi_call_counts
        GROUP BY taxi_id
    )
    SELECT counts.taxi_id, counts.call_type, counts.trip_count
    FROM taxi_call_counts AS counts
    JOIN taxi_max_counts AS maxima
      ON maxima.taxi_id = counts.taxi_id
     AND maxima.max_trip_count = counts.trip_count
    ORDER BY counts.taxi_id, counts.call_type
    """,
    ("Taxi ID", "Call type", "Trips"),
)

QUERY_4B = (
    "4b. Average duration, distance, and start-time shares by call type",
    """
    SELECT
        call_type,
        ROUND(AVG(duration_sec), 2) AS average_duration_sec,
        ROUND(AVG(distance_m), 2) AS average_distance_m,
        ROUND(100.0 * SUM(HOUR(start_time) < 6) / COUNT(*), 2)
            AS share_00_06_pct,
        ROUND(100.0 * SUM(HOUR(start_time) >= 6 AND HOUR(start_time) < 12)
            / COUNT(*), 2) AS share_06_12_pct,
        ROUND(100.0 * SUM(HOUR(start_time) >= 12 AND HOUR(start_time) < 18)
            / COUNT(*), 2) AS share_12_18_pct,
        ROUND(100.0 * SUM(HOUR(start_time) >= 18) / COUNT(*), 2)
            AS share_18_24_pct
    FROM Trip
    GROUP BY call_type
    ORDER BY call_type
    """,
    (
        "Call type",
        "Avg duration (s)",
        "Avg distance (m)",
        "00-06 (%)",
        "06-12 (%)",
        "12-18 (%)",
        "18-24 (%)",
    ),
)

QUERY_5 = (
    "5. Taxi total driving hours and distance (ordered by hours)",
    """
    SELECT
        taxi_id,
        ROUND(SUM(duration_sec) / 3600.0, 2) AS total_hours,
        ROUND(SUM(COALESCE(distance_m, 0)), 2) AS total_distance_m
    FROM Trip
    GROUP BY taxi_id
    ORDER BY SUM(duration_sec) DESC, taxi_id
    """,
    ("Taxi ID", "Total hours", "Total distance (m)"),
)

QUERY_6 = (
    "6. Trips passing within 100 m of Porto City Hall",
    """
    SELECT DISTINCT tr.id, tr.trip_id, tr.taxi_id, tr.start_time
    FROM TrajectoryPoint AS point
    JOIN Trip AS tr ON tr.id = point.trip_id
    WHERE point.lat BETWEEN 41.15694 AND 41.15894
      AND point.lon BETWEEN -8.63041 AND -8.62781
      AND ST_Distance_Sphere(
            POINT(point.lon, point.lat),
            POINT(-8.62911, 41.15794)
          ) <= 100
    ORDER BY tr.id
    """,
    ("Trip row ID", "Source trip ID", "Taxi ID", "Start time"),
)

QUERY_6_COUNT = (
    "6 supplementary. Total trips passing within 100 m of Porto City Hall",
    """
    SELECT COUNT(DISTINCT tr.id) AS matching_trip_count
    FROM TrajectoryPoint AS point
    JOIN Trip AS tr
        ON tr.id = point.trip_id
    WHERE point.lat BETWEEN 41.15694 AND 41.15894
      AND point.lon BETWEEN -8.63041 AND -8.62781
      AND ST_Distance_Sphere(
            POINT(point.lon, point.lat),
            POINT(-8.62911, 41.15794)
          ) <= 100
    """,
    ("Matching trips",),
)

QUERY_7 = (
    "7. Number of trips with fewer than 3 GPS points (full dataset)",
    """
    SELECT COUNT(*) AS fewer_than_three_points
    FROM Trip
    WHERE num_points < 3
    """,
    ("Trips with fewer than 3 points",),
)

QUERY_8 = (
    "8. Trips starting on one calendar day and ending on the next",
    """
    SELECT
        id,
        trip_id,
        taxi_id,
        start_time,
        TIMESTAMPADD(SECOND, duration_sec, start_time) AS estimated_end_time
    FROM Trip
    WHERE DATE(start_time) < DATE(TIMESTAMPADD(SECOND, duration_sec, start_time))
      AND DATE(TIMESTAMPADD(SECOND, duration_sec, start_time))
          < DATE_ADD(DATE(start_time), INTERVAL 2 DAY)
    ORDER BY start_time, id
    """,
    ("Trip row ID", "Source trip ID", "Taxi ID", "Start time", "Estimated end"),
)

QUERY_8_COUNT = (
    "8 supplementary. Total midnight-crossing trips",
    """
    SELECT COUNT(*) AS midnight_crossing_trip_count
    FROM Trip
    WHERE DATE(start_time) < DATE(TIMESTAMPADD(SECOND, duration_sec, start_time))
      AND DATE(TIMESTAMPADD(SECOND, duration_sec, start_time))
          < DATE_ADD(DATE(start_time), INTERVAL 2 DAY)
    """,
    ("Midnight-crossing trips",),
)

QUERY_9 = (
    "9. Circular trips (start and end points within 50 m)",
    """
    SELECT
        tr.id,
        tr.trip_id,
        tr.taxi_id,
        ROUND(
            ST_Distance_Sphere(
                POINT(first_point.lon, first_point.lat),
                POINT(last_point.lon, last_point.lat)
            ),
            2
        ) AS endpoint_distance_m
    FROM Trip AS tr
    JOIN TrajectoryPoint AS first_point
      ON first_point.trip_id = tr.id AND first_point.seq = 0
    JOIN TrajectoryPoint AS last_point
      ON last_point.trip_id = tr.id AND last_point.seq = tr.num_points - 1
    WHERE ST_Distance_Sphere(
            POINT(first_point.lon, first_point.lat),
            POINT(last_point.lon, last_point.lat)
          ) <= 50
    ORDER BY tr.id
    """,
    ("Trip row ID", "Source trip ID", "Taxi ID", "Endpoint distance (m)"),
)

QUERY_9_COUNT = (
    "9 supplementary. Total circular trips (start and end within 50 m)",
    """
    SELECT COUNT(DISTINCT tr.id) AS circular_trip_count
    FROM Trip AS tr
    JOIN TrajectoryPoint AS first_point
        ON first_point.trip_id = tr.id
        AND first_point.seq = 0
    JOIN TrajectoryPoint AS last_point
        ON last_point.trip_id = tr.id
        AND last_point.seq = tr.num_points - 1
    WHERE ST_Distance_Sphere(
        POINT(first_point.lon, first_point.lat),
        POINT(last_point.lon, last_point.lat)
    ) <= 50
    """,
    ("Circular trips",),
)

QUERY_10 = (
    "10. Top 20 taxis by average idle time between trips",
    """
    WITH trip_gaps AS (
        SELECT
            taxi_id,
            start_time,
            TIMESTAMPDIFF(
                SECOND,
                LAG(TIMESTAMPADD(SECOND, duration_sec, start_time))
                    OVER (PARTITION BY taxi_id ORDER BY start_time, id),
                start_time
            ) AS idle_seconds
        FROM Trip
    )
    SELECT
        taxi_id,
        ROUND(AVG(idle_seconds) / 3600.0, 2) AS average_idle_hours,
        COUNT(*) AS trip_gaps
    FROM trip_gaps
    WHERE idle_seconds >= 0
    GROUP BY taxi_id
    ORDER BY AVG(idle_seconds) DESC, taxi_id
    LIMIT 20
    """,
    ("Taxi ID", "Average idle hours", "Gaps averaged"),
)

ASSIGNMENT_QUERIES = (
    QUERY_1,
    QUERY_2,
    QUERY_3,
    QUERY_4A,
    QUERY_4B,
    QUERY_5,
    QUERY_6,
    QUERY_6_COUNT,
    QUERY_7,
    QUERY_8,
    QUERY_8_COUNT,
    QUERY_9,
    QUERY_9_COUNT,
    QUERY_10,
)


def run_queries(cursor):
    """Run all assignment queries in order and print each result as a table."""
    for title, statement, headers in ASSIGNMENT_QUERIES:
        cursor.execute(statement)
        rows = cursor.fetchall()
        print(f"\n{title}")
        print(tabulate(rows, headers=headers, tablefmt="github"))
