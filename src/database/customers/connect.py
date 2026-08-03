import sqlite3
from ..core.config import Settings

settings = Settings()

def create_db():
    conn = sqlite3.connect(settings.DATABASE_NAME)
    cursor = conn.cursor()


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gamers
        (
        id PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        phone_number VARCHAR(20) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        balance DECIMAL(10,2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE
        )
        """)

    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(settings.DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
