import sqlite3
from models.db import DB_PATH

print("사용 중인 DB_PATH:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 상품별 소재 기본 가격
cur.execute("""
CREATE TABLE IF NOT EXISTS product_material_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    material TEXT NOT NULL,
    gold_weight TEXT,
    base_price INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id)
)
""")

# 상품별 가격표 섹션
cur.execute("""
CREATE TABLE IF NOT EXISTS product_price_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    option_code TEXT,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id)
)
""")

# 가격표 행
cur.execute("""
CREATE TABLE IF NOT EXISTS product_price_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    min_value INTEGER,
    max_value INTEGER,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (section_id) REFERENCES product_price_sections(id)
)
""")

# 가격표 셀
cur.execute("""
CREATE TABLE IF NOT EXISTS product_price_cells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    row_id INTEGER NOT NULL,
    material TEXT NOT NULL,
    gold_weight TEXT,
    price_delta INTEGER DEFAULT 0,
    sale_price INTEGER DEFAULT 0,
    FOREIGN KEY (row_id) REFERENCES product_price_rows(id)
)
""")

# 매일 금 시세 저장 테이블
cur.execute("""
CREATE TABLE IF NOT EXISTS gold_market_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    rate_date TEXT NOT NULL UNIQUE,

    pure_gold_price_per_don INTEGER NOT NULL,
    pure_gold_price_per_gram INTEGER NOT NULL,

    source TEXT DEFAULT 'manual',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("상품 가격표 관련 테이블 생성 완료")