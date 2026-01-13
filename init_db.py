import os
import psycopg2

def init_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise Exception("DATABASE_URL environment variable not set!")

    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    conn.autocommit = True  # no need for manual commit

    sql_file_path = os.path.join(os.path.dirname(__file__), "system_db.sql")
    if not os.path.exists(sql_file_path):
        raise FileNotFoundError(f"SQL file not found at {sql_file_path}")

    with open(sql_file_path, "r") as f:
        sql = f.read()

    # Minimal cursor usage
    with conn.cursor() as cur:
        # Split statements by semicolon in case of multiple CREATE/INSERT
        statements = sql.split(';')
        for stmt in statements:
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)

    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()

