import os
import psycopg2

def init_db():
    # Get the database URL from environment variables (Render provides DATABASE_URL)
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise Exception("DATABASE_URL environment variable not set!")

    # Connect to the database
    # sslmode='require' is needed for Render PostgreSQL
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')

    # Enable autocommit so we can execute multiple statements without using cursors
    conn.autocommit = True

    # Read your SQL file
    sql_file_path = os.path.join(os.path.dirname(__file__), "system_db.sql")
    with open(sql_file_path, "r") as f:
        sql = f.read()

    # Execute all SQL commands in one go
    conn.execute(sql)  # psycopg2 supports execute directly on connection with autocommit
    print("Database initialized successfully!")

    # Close the connection
    conn.close()

if __name__ == "__main__":
    init_db()

