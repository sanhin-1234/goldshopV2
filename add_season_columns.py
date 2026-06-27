import sqlite3
from models.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

columns = [
    ("is_season", "INTEGER DEFAULT 0"),
    ("season_banner_image", "TEXT"),
    ("season_between_media", "TEXT"),
    ("season_between_media_type", "TEXT")
]

for column_name, column_type in columns:
    try:
        cur.execute(f"ALTER TABLE products ADD COLUMN {column_name} {column_type}")
        print(f"added column: {column_name}")
    except sqlite3.OperationalError as e:
        print(f"skip {column_name}: {e}")

conn.commit()
conn.close()

print("season columns update complete")