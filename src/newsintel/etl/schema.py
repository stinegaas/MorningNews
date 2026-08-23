import sqlite3

def get_connection(db_path):
    # Establishes a connection to the SQLite database.
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign key support in SQLite
    return conn
    # Has to be its own function so that the connection is still open after the schema is created.

def create_schema(conn):
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            published DATETIME,
            fetched_at DATETIME NOT NULL,
            source_id INTEGER NOT NULL,
            date_id INTEGER NOT NULL,
            FOREIGN KEY (source_id) REFERENCES dim_source(source_id),
            FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_date (
            date_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE NOT NULL, -- Must be unique to avoid duplicate dates in schema
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_source (
            source_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL, -- Must be unique to avoid duplicate sources in schema
            url TEXT NOT NULL
        );
    ''')

    conn.commit()
