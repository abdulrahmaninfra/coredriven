import sqlite3
from passlib.hash import argon2
from typing import Optional

def _hash_password(password: str) -> str:
    return argon2.hash(password)

def UpdateUser(
    conn: sqlite3.Connection, 
    current_username: str,
    username: Optional[str] = None,
    phone_number: Optional[str] = None,
    password: Optional[str] = None,
    balance: Optional[float] = None,
    is_active: Optional[bool] = None
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
        return

    params.append(current_username)
    
    query = f"UPDATE customers SET {', '.join(conditions)} WHERE username = ?"
    cursor.execute(query, params)
    conn.commit()
    