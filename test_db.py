import mysql.connector

# --- IMPORTANT --- 
# For debugging only. Replace the placeholder with your actual password.
DB_PASSWORD_HARDCODED = "YOUR_PASSWORD_HERE"

try:
    print("Attempting to connect to the database with a hardcoded password...")
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password=DB_PASSWORD_HARDCODED,
        database="rag_db",
    )
    print("Database connection successful!")
    conn.close()
except mysql.connector.Error as err:
    print(f"Database connection failed: {err}")
