import sqlite3

DB_PATH = "shop.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(products)")
existing_columns = [row[1] for row in cur.fetchall()]

def add_column(column_name, column_sql):
    if column_name not in existing_columns:
        cur.execute(f"ALTER TABLE products ADD COLUMN {column_name} {column_sql}")
        print(f"Added: {column_name}")
    else:
        print(f"Already exists: {column_name}")

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
conn.close()

print("products table columns fixed.")