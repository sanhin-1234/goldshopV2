import sqlite3

conn = sqlite3.connect("shop.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS home_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_key TEXT UNIQUE NOT NULL,
    slot_name TEXT NOT NULL,
    media_type TEXT DEFAULT 'image',
    filename TEXT,
    title TEXT,
    subtitle TEXT,
    link_url TEXT,
    is_active INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

slots = [
    ("home_hero_1", "홈 메인 슬라이드 1", "image", 1),
    ("home_hero_2", "홈 메인 슬라이드 2", "image", 2),
    ("home_hero_3", "홈 메인 슬라이드 3", "image", 3),
    ("home_hero_4", "홈 메인 슬라이드 4", "image", 4),
    ("home_hero_5", "홈 메인 슬라이드 5", "image", 5),

    ("home_yeon_01", "홈 큰 연 이미지 01 - 결 ; 연", "image", 11),
    ("home_yeon_02", "홈 큰 연 이미지 02 - 숨 ; 결", "image", 12),
    ("home_yeon_03", "홈 큰 연 이미지 03 - 고 ; 결", "image", 13),
    ("home_yeon_04", "홈 큰 연 이미지 04 - 간 ; 결", "image", 14),
    ("home_yeon_05", "홈 큰 연 이미지 05 - 빛 ; 결", "image", 15),
    ("home_yeon_06", "홈 큰 연 이미지 06 - 흔 ; 결", "image", 16),
    ("home_yeon_07", "홈 큰 연 이미지 07 - 결 ; 속", "image", 17),
    ("home_yeon_08", "홈 큰 연 이미지 08 - 결 ; 채", "image", 18),

    ("company_story_main", "회사 스토리 메인 이미지", "image", 30),
    ("company_story_box_1", "회사 스토리 하단 이미지 1", "image", 31),
    ("company_story_box_2", "회사 스토리 하단 이미지 2", "image", 32),
    ("company_story_box_3", "회사 스토리 하단 이미지 3", "image", 33),
]

for slot_key, slot_name, media_type, sort_order in slots:
    cur.execute("""
        INSERT OR IGNORE INTO home_media
        (slot_key, slot_name, media_type, sort_order)
        VALUES (?, ?, ?, ?)
    """, (slot_key, slot_name, media_type, sort_order))

conn.commit()
conn.close()

print("home_media 테이블 생성/업데이트 완료")