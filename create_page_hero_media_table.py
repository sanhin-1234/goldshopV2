import sqlite3

DB_PATH = "shop.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS page_hero_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page TEXT NOT NULL UNIQUE,
    hero_image TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

for page in ["new", "season", "best"]:
    cur.execute("""
        INSERT OR IGNORE INTO page_hero_media (page, hero_image)
        VALUES (?, NULL)
    """, (page,))

conn.commit()
conn.close()

print("page_hero_media 테이블 생성 완료")