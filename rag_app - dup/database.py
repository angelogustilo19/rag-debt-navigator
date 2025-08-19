import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --- Connection Pool ---
db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="debt_navigator_pool",
    pool_size=5,
    pool_reset_session=True,
    host="127.0.0.1",
    user="root",
    password="Waffles25@",
    database="rag_db",
)

def get_db_connection():
    """Get a connection from the pool."""
    try:
        return db_pool.get_connection()
    except mysql.connector.Error as e:
        print(f"[DB ERROR] Failed to get connection from pool: {e}")
        raise

# --- Database Dependency for FastAPI ---
def get_db():
    """FastAPI dependency to get a DB connection and cursor."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        if conn.is_connected():
            conn.close()


# --- Table Creation ---
TABLE_DEFINITIONS = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
    """,
    "debts": """
        CREATE TABLE IF NOT EXISTS debts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            name VARCHAR(255) NOT NULL,
            amount FLOAT NOT NULL,
            interest_rate FLOAT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """
}

def create_tables():
    """Create all required database tables using a single connection."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for table_name, ddl in TABLE_DEFINITIONS.items():
                    cursor.execute(ddl)
            conn.commit()
        print("[DB] Tables created or verified successfully.")
    except mysql.connector.Error as e:
        print(f"[DB ERROR] Failed to create tables: {e}")

if __name__ == "__main__":
    create_tables()