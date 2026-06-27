import sqlite3
from werkzeug.security import generate_password_hash
from models.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

users = cur.execute("""
SELECT id, username, password
FROM users
""").fetchall()

changed_count = 0

for user in users:
    password = user["password"]

    if not password:
        continue

    already_hashed = (
        password.startswith("scrypt:")
        or password.startswith("pbkdf2:")
        or password.startswith("argon2:")
    )

    if already_hashed:
        continue

    password_hash = generate_password_hash(password)

    cur.execute("""
    UPDATE users
    SET password = ?
    WHERE id = ?
    """, (password_hash, user["id"]))

    changed_count += 1

conn.commit()
conn.close()

print(f"{changed_count}명의 회원 비밀번호를 해시로 변환했습니다.")