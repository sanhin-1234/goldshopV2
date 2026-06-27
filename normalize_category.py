import sqlite3
from models.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

mapping = {
    "Ring": "RING",
    "ring": "RING",
    "반지": "RING",

    "Necklace": "NECKLACE",
    "necklace": "NECKLACE",
    "목걸이": "NECKLACE",

    "Earrings": "EARRINGS",
    "earrings": "EARRINGS",
    "귀걸이": "EARRINGS",

    "Bracelet": "BRACELET",
    "bracelet": "BRACELET",
    "팔찌": "BRACELET",

    "Anklet": "ANKLET",
    "anklet": "ANKLET",
    "발찌": "ANKLET",
}

for old_value, new_value in mapping.items():
    cur.execute(
        "UPDATE products SET collection = ? WHERE collection = ?",
        (new_value, old_value)
    )

conn.commit()
conn.close()

print("상품 카테고리 정리 완료")