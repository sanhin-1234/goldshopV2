import sqlite3
from werkzeug.security import generate_password_hash
from models.db import DB_PATH

ADMIN_USERNAME = "sanhinadmin"
ADMIN_PASSWORD = "Qdruixier@2580"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
)
""")

cur.execute("""
SELECT *
FROM admins
WHERE username = ?
""", (ADMIN_USERNAME,))

admin = cur.fetchone()

if admin is None:
    password_hash = generate_password_hash(ADMIN_PASSWORD)

    cur.execute("""
    INSERT INTO admins (username, password_hash)
    VALUES (?, ?)
    """, (ADMIN_USERNAME, password_hash))

    print("관리자 계정이 생성되었습니다.")
else:
    print("이미 관리자 계정이 존재합니다.")

conn.commit()
conn.close()