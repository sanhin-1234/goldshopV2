import sqlite3
from models.db import DB_PATH

DB_NAME = DB_PATH

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

columns = cur.execute("PRAGMA table_info(products)").fetchall()
column_names = [column[1] for column in columns]

if "new_between_media" not in column_names:
    cur.execute("ALTER TABLE products ADD COLUMN new_between_media TEXT DEFAULT ''")
    print("products.new_between_media 컬럼 추가 완료")
else:
    print("products.new_between_media 컬럼 이미 있음")

if "new_between_media_type" not in column_names:
    cur.execute("ALTER TABLE products ADD COLUMN new_between_media_type TEXT DEFAULT ''")
    print("products.new_between_media_type 컬럼 추가 완료")
else:
    print("products.new_between_media_type 컬럼 이미 있음")

conn.commit()
conn.close()

print("NEW 중간 광고/영상 컬럼 점검 완료")