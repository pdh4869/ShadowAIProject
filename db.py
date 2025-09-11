import mysql.connector

DB_NAME = "resume_portal"
DB_USER = "root"
DB_PASSWORD = "mysql"
DB_HOST = "localhost"

def init_db():
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET 'utf8mb4'")
    conn.database = DB_NAME

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS uploads (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        filename VARCHAR(255),
        filedata LONGBLOB,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    cursor.close()
    conn.close()
