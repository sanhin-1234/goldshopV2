import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("DB 위치:", DB_PATH)

try:
    cur.execute("ALTER TABLE orders ADD COLUMN user_id INTEGER")
    print("orders 테이블에 user_id 컬럼 추가 완료")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("orders.user_id 컬럼은 이미 있습니다.")
    else:
        raise

conn.commit()

print("\n현재 orders 테이블 컬럼:")
cur.execute("PRAGMA table_info(orders)")
for col in cur.fetchall():
    print("-", col[1], col[2])

conn.close()

print("\n작업 완료")