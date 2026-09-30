"""MySQL schema for cleaned Porto taxi trips and their GPS points."""


def create_tables(cursor, connection):
    """Create the normalized tables used by the assignment queries."""
    statements = (
        """
        CREATE TABLE IF NOT EXISTS Taxi (
            taxi_id INT NOT NULL PRIMARY KEY
        ) ENGINE=InnoDB
        """,
        """
        CREATE TABLE IF NOT EXISTS Trip (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            trip_id VARCHAR(25) NOT NULL,
            source_row_number BIGINT NOT NULL,
            taxi_id INT NOT NULL,
            call_type CHAR(1) NOT NULL,
            origin_call INT NULL,
            origin_stand INT NULL,
            start_time DATETIME NOT NULL,
            missing_data BOOLEAN NOT NULL,
            num_points INT NOT NULL,
            duration_sec INT NOT NULL,
            distance_m DOUBLE NULL,
            is_invalid BOOLEAN NOT NULL,
            UNIQUE INDEX uq_trip_source_row (source_row_number),
            INDEX idx_taxi (taxi_id),
            INDEX idx_start_time (start_time),
            INDEX idx_trip_id (trip_id),
            CONSTRAINT fk_trip_taxi
                FOREIGN KEY (taxi_id) REFERENCES Taxi(taxi_id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB
        """,
        """
        CREATE TABLE IF NOT EXISTS TrajectoryPoint (
            trip_id BIGINT NOT NULL,
            seq INT NOT NULL,
            lon DOUBLE NOT NULL,
            lat DOUBLE NOT NULL,
            PRIMARY KEY (trip_id, seq),
            INDEX idx_trajectory_lon_lat (lon, lat),
            CONSTRAINT fk_point_trip
                FOREIGN KEY (trip_id) REFERENCES Trip(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB
        """,
    )

    for statement in statements:
        cursor.execute(statement)
    connection.commit()


def drop_tables(cursor, connection):
    """Drop the assignment tables in foreign-key dependency order."""
    cursor.execute("DROP TABLE IF EXISTS TrajectoryPoint")
    cursor.execute("DROP TABLE IF EXISTS Trip")
    cursor.execute("DROP TABLE IF EXISTS Taxi")
    connection.commit()
