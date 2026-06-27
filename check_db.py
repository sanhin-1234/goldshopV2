import sqlite3
from models.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(users)")

for row in cur.fetchall():
    print(row)

conn.close()