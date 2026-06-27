import sqlite3
from models.db import DB_PATH

db_path = DB_PATH

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("PRAGMA table_info(products)")
columns = [row[1] for row in cur.fetchall()]

print("products 컬럼 목록:")
print(columns)
print()
print("collection 있음?", "collection" in columns)
print("tag 있음?", "tag" in columns)

conn.close()