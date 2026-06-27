import sqlite3
from models.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE order_items ADD COLUMN option_text TEXT")
    print("order_items 테이블에 option_text 컬럼 추가 완료")
except sqlite3.OperationalError as e:
    print("이미 컬럼이 있거나 오류 발생:", e)

conn.commit()
conn.close()