import sqlite3
from models.db import DB_PATH

DB_NAME = DB_PATH

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

columns = cur.execute("PRAGMA table_info(products)").fetchall()
column_names = [column[1] for column in columns]

if "tag" not in column_names:
    cur.execute("ALTER TABLE products ADD COLUMN tag TEXT DEFAULT ''")
    print("products.tag 컬럼 추가 완료")
else:
    print("products.tag 컬럼 이미 있음")

if "material" not in column_names:
    cur.execute("ALTER TABLE products ADD COLUMN material TEXT DEFAULT ''")
    print("products.material 컬럼 추가 완료")
else:
    print("products.material 컬럼 이미 있음")

conn.commit()
conn.close()

print("상품 필터 컬럼 점검 완료")