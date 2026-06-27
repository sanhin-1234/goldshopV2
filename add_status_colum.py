import sqlite3
from models.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

try:
    cur.execute("""
    ALTER TABLE orders
    ADD COLUMN status TEXT DEFAULT '주문접수'
    """)

    conn.commit()
    print("status 컬럼 추가 완료")

except Exception as e:
    print("에러:", e)

conn.close()