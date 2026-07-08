from models.db import get_db

UNUSED_SLOT_KEYS = [
    "menu_category_gold",
    "menu_category_silver",
    "menu_category_diamond",
    "menu_category_special",
    "menu_gift_all",
]

db = get_db()

placeholders = ",".join(["?"] * len(UNUSED_SLOT_KEYS))

rows = db.execute(f"""
    SELECT id, slot_key, slot_name, filename
    FROM home_media
    WHERE slot_key IN ({placeholders})
""", UNUSED_SLOT_KEYS).fetchall()

print("삭제 대상 슬롯:")
for row in rows:
    print(dict(row))

db.execute(f"""
    DELETE FROM home_media
    WHERE slot_key IN ({placeholders})
""", UNUSED_SLOT_KEYS)

db.commit()

print(f"{len(rows)}개 슬롯 삭제 완료")