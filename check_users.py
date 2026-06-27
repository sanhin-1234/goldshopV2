import sqlite3
import os
from models.db import DB_PATH

print("현재 실행 위치:", os.getcwd())
print("실제 사용 중인 DB 경로:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("\n=== 현재 DB 안의 테이블 목록 ===")
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()

if not tables:
    print("테이블이 하나도 없습니다.")
else:
    for table in tables:
        print("-", table[0])

print("\n=== users 테이블 컬럼 ===")
cur.execute("PRAGMA table_info(users)")
columns = cur.fetchall()

if not columns:
    print("users 테이블이 없습니다.")
else:
    for col in columns:
        print(col)

conn.close()