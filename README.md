# TDT4225 Assignment 2

This repository contains the assignment's Porto taxi data loader, MySQL queries,
and exploratory analysis notebook. The database used during development is not
included or publicly accessible. To run the program, configure your own MySQL
database and load the assignment CSV into it.

## Requirements

- Python 3.11 or later and the packages listed in `requirements.txt`
- MySQL 8 or later
- The Porto taxi CSV file (`porto.csv`) supplied for the assignment

The CSV is not included in this repository. The loader expects the original
columns: `TRIP_ID`, `CALL_TYPE`, `ORIGIN_CALL`, `ORIGIN_STAND`, `TAXI_ID`,
`TIMESTAMP`, `DAY_TYPE`, `MISSING_DATA`, and `POLYLINE`.

## Set up your database

1. Start your MySQL server and create an empty database. For example, from a
   MySQL client:

   ```sql
   CREATE DATABASE assignment2;
   ```

2. Use a MySQL account that can connect to this database. To import data, that
   account needs permission to create tables, insert rows, and read rows. The
   `--reset` option also needs permission to drop tables.
3. Copy `.env.example` to `.env` and fill in your own connection details and the
   full path to `porto.csv`:

   ```dotenv
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   MYSQL_DATABASE=assignment2
   MYSQL_USER=your_mysql_user
   USER_PASSWORD=your_mysql_password
   PORTO_CSV_PATH=C:/path/to/porto.csv
   ```

   `.env` is local and ignored by Git. Do not put your database password in a
   tracked file.

## Install and run

From the repository directory, install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Import the CSV and create the assignment tables in your database:

```bash
python main.py --load
```

After the import, run the assignment queries:

```bash
python main.py
```

Running `main.py` without `--load` only runs queries; it expects the assignment
tables and data to already exist in the database configured in `.env`. The
initial import reads the full CSV and may take some time. Malformed rows are
skipped and recorded in `rejected_rows.csv`.

To replace the assignment tables and import from scratch, run:

```bash
python main.py --load --reset
```

This drops and recreates `Taxi`, `Trip`, and `TrajectoryPoint` in the database
configured in `.env`. Use it only if you intend to replace those tables.

## Exploratory analysis

The optional EDA notebook is `eda/porto_eda.ipynb`. Open it in Jupyter from the
repository, set `PORTO_CSV_PATH` in `.env` as above, and run its cells. It reads
the CSV in chunks and saves plots to `eda/figures/`; those generated images are
ignored by Git. The spatial map uses Cartopy, which downloads its Natural Earth
basemap files on the first run and therefore needs an internet connection then.

## Project structure

```text
.
|-- main.py                       Command-line entry point
|-- DbConnector.py                Opens the MySQL connection from .env
|-- schema.py                     Creates and drops the assignment tables
|-- loader.py                     Cleans the CSV and inserts trips and GPS points
|-- queries.py                    Defines and runs the assignment queries
|-- outlier_comparison_queries.sql Supplementary queries excluding outliers
|-- requirements.txt              Python dependencies
|-- .env.example                  Template for local database and CSV settings
`-- eda/
    `-- porto_eda.ipynb           Exploratory data analysis notebook
```

With `--load`, `main.py` connects through `DbConnector.py`, creates the tables
using `schema.py`, then calls `loader.py` to import the CSV. Without `--load`,
it connects to the configured database and runs the queries from `queries.py`.
The EDA notebook is a separate workflow that reads the CSV directly.
