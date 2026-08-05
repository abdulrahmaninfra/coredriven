import sqlite3

from src.core.security import hash_password as _hash_password


def UpdateUser(
    conn: sqlite3.Connection,
    current_username: str,
    username: str | None = None,
    phone_number: str | None = None,
    password: str | None = None,
    balance: float | None = None,
    is_active: bool | None = None,
):
    cursor = conn.cursor()
    conditions = []
    params = []

    if username is not None:
        conditions.append("username = ?")
        params.append(username)

    if phone_number is not None:
        conditions.append("phone_number = ?")
        params.append(phone_number)

    if password is not None:
        hashed = _hash_password(password)
        conditions.append("password_hash = ?")
        params.append(hashed)

    if balance is not None:
        conditions.append("balance = ?")
        params.append(balance)

    if is_active is not None:
        conditions.append("is_active = ?")
        params.append(is_active)

    if not conditions:
        print("No fields to update")
        return False

    params.append(current_username)

    set_clause = ", ".join(conditions)
    query = f"UPDATE customers SET {set_clause} WHERE username = ?"
    cursor.execute(query, params)
    conn.commit()
    return True
