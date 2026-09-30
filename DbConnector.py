"""Load MySQL settings and manage one database connection."""

import os

import mysql.connector


class DbConnector:
    """Open and close a MySQL connection using settings from ``.env``.

    Set ``MYSQL_HOST``, ``MYSQL_DATABASE``, ``MYSQL_USER``, and
    ``USER_PASSWORD``. ``MYSQL_PORT`` defaults to 3306.
    """

    def __init__(self):
        required = ("MYSQL_HOST", "MYSQL_DATABASE", "MYSQL_USER", "USER_PASSWORD")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise ValueError(f"Set these database settings in .env: {', '.join(missing)}.")

        self.host = os.environ["MYSQL_HOST"]
        self.port = int(os.getenv("MYSQL_PORT", "3306"))
        self.database = os.environ["MYSQL_DATABASE"]
        self.user = os.environ["MYSQL_USER"]
        password = os.environ["USER_PASSWORD"]

        self.db_connection = None
        self.cursor = None

        try:
            self.db_connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=password,
                connection_timeout=10,
            )
            self.cursor = self.db_connection.cursor()
        except mysql.connector.Error as error:
            self.close_connection()
            raise ConnectionError(
                f"Could not connect to MySQL at {self.host}:{self.port} "
                f"(database '{self.database}', user '{self.user}'): {error}"
            ) from error

    def close_connection(self):
        """Close the cursor and connection if they were opened."""
        if self.cursor is not None:
            self.cursor.close()
            self.cursor = None
        if self.db_connection is not None:
            self.db_connection.close()
            self.db_connection = None

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        self.close_connection()
