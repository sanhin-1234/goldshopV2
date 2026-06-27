import sqlite3
from models.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
    DELETE FROM home_media
    WHERE slot_key IN (
        'menu_category_new',
        'menu_category_season',
        'menu_category_best'
    )
""")

conn.commit()
conn.close()

print("중복 메뉴 카테고리 슬롯 삭제 완료")