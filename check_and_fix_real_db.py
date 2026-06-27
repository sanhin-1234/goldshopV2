import os
import sqlite3

from models.db import DB_PATH

print("현재 Flask 앱이 사용하는 DB_PATH:")
print(DB_PATH)
print("절대 경로:")
print(os.path.abspath(DB_PATH))

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(products)")
columns_info = cur.fetchall()
existing_columns = [row[1] for row in columns_info]

print("\n현재 products 컬럼:")
for col in existing_columns:
    print("-", col)

def add_column(column_name, column_sql):
    if column_name not in existing_columns:
        cur.execute(f"ALTER TABLE products ADD COLUMN {column_name} {column_sql}")
        print(f"Added: {column_name}")
        existing_columns.append(column_name)
    else:
        print(f"Already exists: {column_name}")

print("\n컬럼 보정 시작:")

add_column("description", "TEXT")
add_column("collection", "TEXT DEFAULT 'GENERAL'")
add_column("tag", "TEXT DEFAULT ''")
add_column("material", "TEXT DEFAULT ''")

add_column("new_banner_image", "TEXT")
add_column("new_between_media", "TEXT")
add_column("new_between_media_type", "TEXT")

add_column("season_banner_image", "TEXT")
add_column("season_between_media", "TEXT")
add_column("season_between_media_type", "TEXT")

conn.commit()

print("\n보정 후 products 컬럼:")
cur.execute("PRAGMA table_info(products)")
for row in cur.fetchall():
    print("-", row[1])

conn.close()

print("\n실제 Flask DB products 컬럼 보정 완료.")