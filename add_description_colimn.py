import sqlite3
from models.db import DB_PATH

print("사용 중인 DB:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 현재 DB에 어떤 테이블이 있는지 확인
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cur.fetchall()]

print("현재 테이블 목록:")
print(tables)

# products 테이블 확인
if "products" not in tables:
    conn.close()
    print()
    print("에러: products 테이블이 없습니다.")
    print("지금 보고 있는 DB가 비어 있거나 잘못된 DB입니다.")
    print("DB_PATH가 goldshopV2/shop.db인지 확인하세요.")
    raise SystemExit

# products 컬럼 확인
cur.execute("PRAGMA table_info(products)")
columns = [row[1] for row in cur.fetchall()]

print()
print("현재 products 컬럼:")
print(columns)

# description 컬럼 추가
if "description" not in columns:
    cur.execute("ALTER TABLE products ADD COLUMN description TEXT DEFAULT ''")
    print("description 컬럼 추가 완료")
else:
    print("description 컬럼 이미 있음")

conn.commit()
conn.close()

print("완료")