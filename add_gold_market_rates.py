import sqlite3
from models.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS gold_market_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rate_date TEXT UNIQUE NOT NULL,
    pure_gold_price_per_don INTEGER NOT NULL DEFAULT 0,
    pure_gold_price_per_gram INTEGER NOT NULL DEFAULT 0,
    source TEXT DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("gold_market_rates 테이블 생성 완료")
