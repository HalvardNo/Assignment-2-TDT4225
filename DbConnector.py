import mysql.connector as mysql
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(ENV_PATH)


class DbConnector:
    """
    Connects to the MySQL server on the Ubuntu virtual machine.
    Connector needs HOST, DATABASE, USER and PASSWORD to connect,
    while PORT is optional and should be 3306.

    Example:
    HOST = "tdt4225-00.idi.ntnu.no" // Your server IP address/domain name
    DATABASE = "testdb" // Database name, if you just want to connect to MySQL server, leave it empty
    USER = "testuser" // This is the user you created and added privileges for
    PASSWORD = "test123" // The password you set for said user
    """

    def __init__(self,
                 HOST="tdt4225-70.idi.ntnu.no",
                 DATABASE="Assignment2_grp70",
                 USER="aflarsen",
                 PASSWORD=None):
        password = PASSWORD or os.getenv("USER_PASSWORD")
        if not password:
            raise ValueError(
                f"USER_PASSWORD is not set. Add USER_PASSWORD=<your database password> to {ENV_PATH}."
            )

        # Connect to the database
        try:
            self.db_connection = mysql.connect(
                host=HOST,
                database=DATABASE,
                user=USER,
                password=password,
                port=3306,
                connection_timeout=10,
            )
        except mysql.Error as error:
            raise ConnectionError(f"Failed to connect to the database: {error}") from error

        # Get the db cursor
        self.cursor = self.db_connection.cursor()

        print("Connected to:", self.db_connection.get_server_info())
        # get database information
        self.cursor.execute("select database();")
        database_name = self.cursor.fetchone()
        print("You are connected to the database:", database_name)
        print("-----------------------------------------------\n")

    def close_connection(self):
        if not self.db_connection.is_connected():
            return

        server_info = self.db_connection.get_server_info()
        self.cursor.close()
        self.db_connection.close()
        print("\n-----------------------------------------------")
        print("Connection to %s is closed" % server_info)


if __name__ == "__main__":
    try:
        connection = DbConnector()
    except (ValueError, ConnectionError) as error:
        print(f"ERROR: {error}")
        sys.exit(1)
    else:
        connection.close_connection()
