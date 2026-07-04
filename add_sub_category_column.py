import sqlite3

conn = sqlite3.connect("shop.db")
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE products ADD COLUMN sub_category TEXT")
    print("sub_category 컬럼 추가 완료")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("sub_category 컬럼은 이미 존재합니다.")
    else:
        raise

conn.commit()
conn.close()