import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")

print("DB 위치:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS product_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER,
    username TEXT,
    rating INTEGER DEFAULT 5,
    review_text TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()

print("현재 테이블 목록:")
for table in tables:
    print("-", table[0])

conn.close()

print("product_reviews 테이블 생성 완료")