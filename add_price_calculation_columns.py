import sqlite3
from models.db import DB_PATH

print("사용 중인 DB_PATH:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()


def get_columns(table_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cur.fetchall()]


def add_column_if_missing(table_name, column_name, column_sql):
    columns = get_columns(table_name)

    if column_name in columns:
        print(f"이미 있음: {table_name}.{column_name}")
        return

    cur.execute(f"""
        ALTER TABLE {table_name}
        ADD COLUMN {column_sql}
    """)
    print(f"추가 완료: {table_name}.{column_name}")


# 상품 소재 기본 가격 계산용 컬럼
add_column_if_missing(
    "product_material_prices",
    "labor_fee",
    "labor_fee INTEGER DEFAULT 0"
)

add_column_if_missing(
    "product_material_prices",
    "stone_price",
    "stone_price INTEGER DEFAULT 0"
)

add_column_if_missing(
    "product_material_prices",
    "extra_fee",
    "extra_fee INTEGER DEFAULT 0"
)

add_column_if_missing(
    "product_material_prices",
    "loss_rate",
    "loss_rate REAL DEFAULT 0.10"
)

add_column_if_missing(
    "product_material_prices",
    "margin_multiplier",
    "margin_multiplier REAL DEFAULT 1.20"
)

add_column_if_missing(
    "product_material_prices",
    "calculated_cost",
    "calculated_cost INTEGER DEFAULT 0"
)

add_column_if_missing(
    "product_material_prices",
    "is_manual_price",
    "is_manual_price INTEGER DEFAULT 0"
)


# 가격표 셀 계산용 컬럼
add_column_if_missing(
    "product_price_cells",
    "labor_fee",
    "labor_fee INTEGER DEFAULT 0"
)

add_column_if_missing(
    "product_price_cells",
    "stone_price",
    "stone_price INTEGER DEFAULT 0"
)

add_column_if_missing(
    "product_price_cells",
    "extra_fee",
    "extra_fee INTEGER DEFAULT 0"
)

add_column_if_missing(
    "product_price_cells",
    "loss_rate",
    "loss_rate REAL DEFAULT 0.10"
)

add_column_if_missing(
    "product_price_cells",
    "margin_multiplier",
    "margin_multiplier REAL DEFAULT 1.20"
)

add_column_if_missing(
    "product_price_cells",
    "calculated_cost",
    "calculated_cost INTEGER DEFAULT 0"
)

add_column_if_missing(
    "product_price_cells",
    "is_manual_price",
    "is_manual_price INTEGER DEFAULT 0"
)

# 14K 기준 자동 계산용 추가 컬럼
add_column_if_missing(
    "product_material_prices",
    "pure_weight",
    "pure_weight TEXT"
)

add_column_if_missing(
    "product_material_prices",
    "gold_price",
    "gold_price INTEGER DEFAULT 0"
)

add_column_if_missing(
    "product_material_prices",
    "discount_rate",
    "discount_rate REAL DEFAULT 0"
)

add_column_if_missing(
    "product_material_prices",
    "discount_price",
    "discount_price INTEGER DEFAULT 0"
)

add_column_if_missing(
    "product_material_prices",
    "base_14k_weight",
    "base_14k_weight TEXT"
)

conn.commit()
conn.close()

print("가격 계산용 컬럼 추가 완료")