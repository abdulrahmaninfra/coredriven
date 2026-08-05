import sqlite3
import uuid
from passlib.hash import argon2
from src.core.security import hash_password

class CreateNewUser:
    def __init__(self, username: str, password: str, phone_number: str, balance: float):
        self.id = str(uuid.uuid4())
        self.username = username
        self.password = hash_password(password)
        self.phone_number = phone_number
        self.balance = balance


    def create_user(self, conn: sqlite3.Connection):
        cursor = conn.cursor()
        cursor.execute("INSERT INTO customers (id, username, password_hash, balance, phone_number) VALUES (?, ?, ?, ?, ?)",
                       (self.id, self.username, self.password, self.balance, self.phone_number))
        conn.commit()

        cursor.execute("SELECT * FROM customers WHERE username = ? AND password_hash = ?",
                       (self.username, self.password))
        return cursor.fetchone()
