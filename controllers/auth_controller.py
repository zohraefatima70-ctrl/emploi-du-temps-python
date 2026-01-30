import bcrypt
from database.db import getConnection
from models.user import User

def login(username, password):
    conn = getConnection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, password, role, full_name FROM users WHERE username = ?",
        (username,)
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None  # user غير موجود

    if not bcrypt.checkpw(password.encode("utf-8"), row["password"]):
        return None  # password غلط

    # إنشاء User object
    user = User(
        user_id=row["id"],
        username=row["username"],
        role=row["role"],
        full_name=row["full_name"]
    )

    return user
