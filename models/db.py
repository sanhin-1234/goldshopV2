import sqlite3
from pathlib import Path

# 현재 파일 위치:
# C:\코딩\goldshopV2\models\db.py
#
# parent.parent = C:\코딩\goldshopV2
BASE_DIR = Path(__file__).resolve().parent.parent

# 공식 DB는 항상 goldshopV2 폴더 안의 shop.db
DB_PATH = BASE_DIR / "shop.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn