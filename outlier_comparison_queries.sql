-- Supplementary comparison queries for results excluding flagged outliers.
-- The primary full-dataset queries are defined in queries.py without an
-- is_outlier predicate. Run those for the "All trips" side of each table.
-- Run the matching query below for the "Outliers excluded" side.

-- Task 1: counts after excluding flagged trips. Taxi count includes taxis
-- with at least one remaining non-outlier trip.
SELECT
    COUNT(DISTINCT taxi_id) AS taxi_count,
    COUNT(*) AS trip_count,
    (
        SELECT COUNT(*)
        FROM TrajectoryPoint AS point
        JOIN Trip AS trip ON trip.id = point.trip_id
        WHERE trip.is_outlier = FALSE
    ) AS gps_point_count
FROM Trip
WHERE is_outlier = FALSE;

-- Task 2: average trips per taxi, considering taxis with at least one
-- non-outlier trip
SELECT ROUND(AVG(trip_count), 2) AS average_trips_per_taxi
FROM (
    SELECT taxi_id, COUNT(*) AS trip_count
    FROM Trip
    WHERE is_outlier = FALSE
    GROUP BY taxi_id
) AS taxi_trip_counts;

-- Task 3: top 20 taxis by non-outlier trip count
SELECT taxi_id, COUNT(*) AS trip_count
FROM Trip
WHERE is_outlier = FALSE
GROUP BY taxi_id
ORDER BY trip_count DESC, taxi_id
LIMIT 20;

-- Task 4a: most used call type per taxi, excluding flagged trips
WITH taxi_call_counts AS (
    SELECT taxi_id, call_type, COUNT(*) AS trip_count
    FROM Trip
    WHERE is_outlier = FALSE
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
ORDER BY counts.taxi_id, counts.call_type;

-- Task 4b: duration, distance, and start-time shares by call type
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
WHERE is_outlier = FALSE
GROUP BY call_type
ORDER BY call_type;

-- Task 5: total driving hours and distance per taxi
SELECT
    taxi_id,
    ROUND(SUM(duration_sec) / 3600.0, 2) AS total_hours,
    ROUND(SUM(COALESCE(distance_m, 0)), 2) AS total_distance_m
FROM Trip
WHERE is_outlier = FALSE
GROUP BY taxi_id
ORDER BY SUM(duration_sec) DESC, taxi_id;

-- Task 6: trips passing within 100 m of Porto City Hall
SELECT DISTINCT tr.id, tr.trip_id, tr.taxi_id, tr.start_time
FROM TrajectoryPoint AS point
JOIN Trip AS tr ON tr.id = point.trip_id
WHERE point.lat BETWEEN 41.15694 AND 41.15894
  AND point.lon BETWEEN -8.63041 AND -8.62781
  AND tr.is_outlier = FALSE
  AND ST_Distance_Sphere(
        POINT(point.lon, point.lat),
        POINT(-8.62911, 41.15794)
      ) <= 100
ORDER BY tr.id;

-- Task 6 supplementary total
SELECT COUNT(DISTINCT tr.id) AS matching_trip_count
FROM TrajectoryPoint AS point
JOIN Trip AS tr ON tr.id = point.trip_id
WHERE point.lat BETWEEN 41.15694 AND 41.15894
  AND point.lon BETWEEN -8.63041 AND -8.62781
  AND tr.is_outlier = FALSE
  AND ST_Distance_Sphere(
        POINT(point.lon, point.lat),
        POINT(-8.62911, 41.15794)
      ) <= 100;

-- Task 7: fewer-than-three-point trips among the non-outliers
SELECT COUNT(*) AS fewer_than_three_points
FROM Trip
WHERE num_points < 3
  AND is_outlier = FALSE;

-- Task 8: trips starting on one calendar day and ending on the next
SELECT
    id,
    trip_id,
    taxi_id,
    start_time,
    TIMESTAMPADD(SECOND, duration_sec, start_time) AS estimated_end_time
FROM Trip
WHERE is_outlier = FALSE
  AND DATE(start_time) < DATE(TIMESTAMPADD(SECOND, duration_sec, start_time))
  AND DATE(TIMESTAMPADD(SECOND, duration_sec, start_time))
      < DATE_ADD(DATE(start_time), INTERVAL 2 DAY)
ORDER BY start_time, id;

-- Task 8 supplementary total with flagged trips excluded
SELECT COUNT(*) AS midnight_crossing_trip_count
FROM Trip
WHERE is_outlier = FALSE
  AND DATE(start_time) < DATE(TIMESTAMPADD(SECOND, duration_sec, start_time))
  AND DATE(TIMESTAMPADD(SECOND, duration_sec, start_time))
      < DATE_ADD(DATE(start_time), INTERVAL 2 DAY);

-- Task 9: circular trips among non-outliers
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
WHERE tr.is_outlier = FALSE
  AND ST_Distance_Sphere(
        POINT(first_point.lon, first_point.lat),
        POINT(last_point.lon, last_point.lat)
      ) <= 50
ORDER BY tr.id;

-- Task 9 supplementary total
SELECT COUNT(DISTINCT tr.id) AS circular_trip_count
FROM Trip AS tr
JOIN TrajectoryPoint AS first_point
  ON first_point.trip_id = tr.id AND first_point.seq = 0
JOIN TrajectoryPoint AS last_point
  ON last_point.trip_id = tr.id AND last_point.seq = tr.num_points - 1
WHERE tr.is_outlier = FALSE
  AND ST_Distance_Sphere(
        POINT(first_point.lon, first_point.lat),
        POINT(last_point.lon, last_point.lat)
      ) <= 50;

-- Task 10: top 20 taxis by average idle time, excluding flagged trips
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
    WHERE is_outlier = FALSE
)
SELECT
    taxi_id,
    ROUND(AVG(idle_seconds) / 3600.0, 2) AS average_idle_hours,
    COUNT(*) AS trip_gaps
FROM trip_gaps
WHERE idle_seconds >= 0
GROUP BY taxi_id
ORDER BY AVG(idle_seconds) DESC, taxi_id
LIMIT 20;
