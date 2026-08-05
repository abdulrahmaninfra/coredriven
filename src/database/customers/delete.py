import sqlite3


class DeleteUser:
    def __init__(self, username: str | None, phone_number: str | None, conn: sqlite3.Connection):
        self.conn = conn
        self.username = username
        self.phone_number = phone_number


    def delete_by_phone_number(self):
        if self.phone_number is None:
            print("Phone number is required")
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM customers WHERE phone_number = ?", (self.phone_number,))
            self.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            self.conn.rollback()
            return False

    def delete_by_username(self):
        if self.username is None:
            print("Username is required")
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM customers WHERE username = ?", (self.username,))
            self.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            self.conn.rollback()
            return False