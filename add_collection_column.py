import sqlite3
from models.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

try:
    cur.execute("""
        ALTER TABLE products
        ADD COLUMN collection TEXT DEFAULT 'GENERAL'
    """)

    print("collection 컬럼 추가 완료")

except Exception as e:
    print("이미 존재하거나 오류:", e)

conn.commit()
conn.close()