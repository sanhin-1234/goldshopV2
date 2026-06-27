import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

columns = [
    "detail_image_1",
    "detail_image_2",
    "detail_image_3"
]

for col in columns:
    try:
        cur.execute(f"ALTER TABLE products ADD COLUMN {col} TEXT")
        print(f"{col} 컬럼 추가 완료")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"{col} 컬럼은 이미 있습니다.")
        else:
            raise

conn.commit()
conn.close()

print("상품 상세 이미지 컬럼 작업 완료")