import sqlite3


class GetUser:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM customers;")
        return cursor.fetchall()


    def get_user_by_username(self, username: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE username = ?", (username,))
        return cursor.fetchone()


    def get_user_by_phone_number(self, phone_number: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE phone_number = ?", (phone_number,))
        return cursor.fetchone()


    def get_user(self, username: str | None = None, phone_number: str | None = None):
        conditions = []
        params = []

        if username is not None:
            conditions.append("username LIKE ?")
            params.append(f"%{username}%")

        if phone_number is not None:
            conditions.append("phone_number LIKE ?")
            params.append(f"%{phone_number}%")

        query = "SELECT * FROM customers"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cursor = self.conn.cursor()
        cursor.execute(query,params)
        return cursor.fetchall()
