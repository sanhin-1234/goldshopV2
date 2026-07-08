from flask import Blueprint, render_template, request, redirect, url_for, session
from models.db import get_db
import json
import math

 # 소비자 페이지
 
product_bp = Blueprint("product", __name__)

def get_product_rating(db, product_id):
    rating_row = db.execute("""
        SELECT 
            COUNT(id) AS review_count,
            COALESCE(AVG(rating), 0) AS avg_rating
        FROM product_reviews
        WHERE product_id = ?
    """, (product_id,)).fetchone()

    return {
        "review_count": rating_row["review_count"] if rating_row else 0,
        "avg_rating": float(rating_row["avg_rating"] or 0)
    }


def attach_rating_to_products(db, products):
    rated_products = []

    for product in products:
        item = dict(product)

        rating = get_product_rating(db, item["id"])

        item["review_count"] = rating["review_count"]
        item["avg_rating"] = rating["avg_rating"]

        rated_products.append(item)

    return rated_products

def get_page_hero_media(db, slot_key):
    hero = db.execute("""
        SELECT *
        FROM home_media
        WHERE slot_key = ?
          AND is_active = 1
        LIMIT 1
    """, (slot_key,)).fetchone()

    return hero

def safe_float(value, default=0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def row_get(row, key, default=None):
    if row is None:
        return default

    if key in row.keys():
        value = row[key]
        if value is not None:
            return value

    return default


def row_get_any(row, keys, default=None):
    for key in keys:
        if row is not None and key in row.keys() and row[key] is not None:
            return row[key]
    return default


def normalize_rate(value, default=0):
    """
    10 입력 → 0.10
    0.1 입력 → 0.10
    """
    rate = safe_float(value, default)

    if rate > 1:
        return rate / 100

    return rate


def round_at_thousands_digit(value):
    """
    천의 자리에서 반올림
    예: 1,106,600 -> 1,110,000
    """
    value = safe_float(value, 0)
    return int(math.floor((value + 5000) / 10000) * 10000)


def calculate_material_price(material_row, gold_rate):
    material = str(row_get(material_row, "material", "14K")).upper()

    gold_weight = safe_float(row_get(material_row, "gold_weight", 0))

    labor_fee = safe_float(row_get(material_row, "labor_fee", 0))
    stone_price = safe_float(row_get(material_row, "stone_price", 0))
    extra_fee = safe_float(row_get(material_row, "extra_fee", 0))

    multiplier = safe_float(row_get(material_row, "multiplier", 1), 1)
    if multiplier <= 0:
        multiplier = 1

    vat_rate = normalize_rate(row_get(material_row, "vat_rate", 10), 0.1)
    discount_rate = normalize_rate(row_get(material_row, "discount_rate", 0), 0)

    # 해리 컬럼명이 프로젝트에서 다를 수 있어서 여러 이름을 같이 대응
    haeri = safe_float(
        row_get_any(
            material_row,
            ["haeri", "haeri_rate", "loss_rate", "wastage_rate"],
            1
        ),
        1
    )

    if haeri <= 0:
        haeri = 1

    # 14K 기준 입력
    if material == "18K":
        material_weight = gold_weight * 1.15
        pure_weight = material_weight * 0.75
    else:
        material_weight = gold_weight
        pure_weight = material_weight * 0.585

    gold_price = (safe_float(gold_rate, 0) / 3.75) * pure_weight * haeri

    product_cost = gold_price + labor_fee + stone_price + extra_fee

    base_price_before_round = product_cost * multiplier * (1 + vat_rate)
    base_sale_price = round_at_thousands_digit(base_price_before_round)

    discounted_price = int(round(base_sale_price * (1 - discount_rate)))

    margin_price = discounted_price - product_cost

    return {
        "material": material,
        "gold_weight": gold_weight,
        "material_weight": material_weight,
        "pure_weight": pure_weight,
        "gold_price": int(round(gold_price)),
        "product_cost": int(round(product_cost)),
        "base_sale_price": base_sale_price,
        "discounted_price": discounted_price,
        "margin_price": int(round(margin_price)),
        "labor_fee": int(round(labor_fee)),
        "stone_price": int(round(stone_price)),
        "extra_fee": int(round(extra_fee)),
        "multiplier": multiplier,
        "vat_rate": vat_rate,
        "discount_rate": discount_rate,
        "haeri": haeri
    }


def get_latest_gold_rate(db):
    rate_row = db.execute("""
        SELECT *
        FROM gold_market_rates
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    if rate_row is None:
        return 0

    return safe_float(row_get(rate_row, "base_rate", 0), 0)


def get_product_material_price_data(db, product_id):
    rows = db.execute("""
        SELECT *
        FROM product_material_prices
        WHERE product_id = ?
        ORDER BY sort_order ASC, id ASC
    """, (product_id,)).fetchall()

    material_price_data = {}

    for row in rows:
        material = str(row["material"] or "").upper()

        if not material:
            continue

        # 관리자에서 저장한 계산 결과를 그대로 사용
        discount_price = 0
        base_sale_price = 0
        product_cost = 0
        gold_price = 0

        if "discount_price" in row.keys():
            discount_price = safe_int(row["discount_price"], 0)

        if "base_sale_price" in row.keys():
            base_sale_price = safe_int(row["base_sale_price"], 0)

        if "base_price" in row.keys() and base_sale_price <= 0:
            base_sale_price = safe_int(row["base_price"], 0)

        if "calculated_cost" in row.keys():
            product_cost = safe_int(row["calculated_cost"], 0)

        if "gold_price" in row.keys():
            gold_price = safe_int(row["gold_price"], 0)

        # 혹시 discount_price가 비어 있으면 base_sale_price로 대체
        if discount_price <= 0:
            discount_price = base_sale_price

        material_price_data[material] = {
            "material": material,
            "gold_weight": row["gold_weight"] if "gold_weight" in row.keys() else 0,
            "pure_weight": row["pure_weight"] if "pure_weight" in row.keys() else 0,
            "gold_price": gold_price,
            "product_cost": product_cost,
            "base_sale_price": base_sale_price,
            "discounted_price": discount_price,
            "margin_price": discount_price - product_cost,
            "labor_fee": safe_int(row["labor_fee"], 0) if "labor_fee" in row.keys() else 0,
            "stone_price": safe_int(row["stone_price"], 0) if "stone_price" in row.keys() else 0,
            "extra_fee": safe_int(row["extra_fee"], 0) if "extra_fee" in row.keys() else 0,
            "multiplier": row["margin_multiplier"] if "margin_multiplier" in row.keys() else 1,
            "discount_rate": row["discount_rate"] if "discount_rate" in row.keys() else 0,
            "haeri": row["loss_rate"] if "loss_rate" in row.keys() else 0
        }

    return material_price_data


def get_product_option_groups(db, product_id):
    sections = db.execute("""
        SELECT *
        FROM product_price_sections
        WHERE product_id = ?
        ORDER BY sort_order ASC, id ASC
    """, (product_id,)).fetchall()

    option_groups = []

    for section in sections:
        rows = db.execute("""
            SELECT *
            FROM product_price_rows
            WHERE section_id = ?
            ORDER BY sort_order ASC, id ASC
        """, (section["id"],)).fetchall()

        option_rows = []

        for row in rows:
            values = db.execute("""
                SELECT *
                FROM product_price_values
                WHERE row_id = ?
                ORDER BY sort_order ASC, id ASC
            """, (row["id"],)).fetchall()

            prices = {
                "14K": 0,
                "18K": 0
            }

            for value in values:
                material = str(row_get(value, "material", "") or "").upper()

                if "price_14k" in value.keys():
                    prices["14K"] = safe_int(value["price_14k"], prices["14K"])

                if "price_18k" in value.keys():
                    prices["18K"] = safe_int(value["price_18k"], prices["18K"])

                if material in ["14K", "18K"] and "price" in value.keys():
                    prices[material] = safe_int(value["price"], prices[material])

            option_rows.append({
                "id": row["id"],
                "label": row_get(row, "label", ""),
                "min_value": row_get(row, "min_value", ""),
                "max_value": row_get(row, "max_value", ""),
                "prices": prices
            })

        option_groups.append({
            "id": section["id"],
            "title": row_get(section, "title", "옵션"),
            "option_code": row_get(section, "option_code", ""),
            "rows": option_rows
        })

    return option_groups

def ensure_home_media_table(cur):
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

        ("page_hero_new", "페이지 히어로 이미지 - NEW", "image", 63),
        ("page_hero_season", "페이지 히어로 이미지 - SEASON", "image", 64),
        ("page_hero_best", "페이지 히어로 이미지 - BEST", "image", 65),
    ]

    for slot_key, slot_name, media_type, sort_order in slots:
        cur.execute("""
            INSERT OR IGNORE INTO home_media
            (slot_key, slot_name, media_type, sort_order)
            VALUES (?, ?, ?, ?)
        """, (slot_key, slot_name, media_type, sort_order))

@product_bp.route("/")
def home():

    search = request.args.get("search", "")
    collection = request.args.get("collection", "")
    sort = request.args.get("sort", "latest")

    conn = get_db()
    cur = conn.cursor()

    ensure_home_media_table(cur)
    conn.commit()

    # =========================
    # 상품 데이터
    # =========================
    query = "SELECT * FROM products"
    params = []

    conditions = []

    if search:
        conditions.append("name LIKE ?")
        params.append('%' + search + '%')

    if collection:
        conditions.append("collection = ?")
        params.append(collection)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    if sort == "latest":
        query += " ORDER BY id DESC"

    elif sort == "oldest":
        query += " ORDER BY id ASC"

    elif sort == "price_low":
        query += " ORDER BY price ASC"

    elif sort == "price_high":
        query += " ORDER BY price DESC"

    elif sort == "name":
        query += " ORDER BY name ASC"

    cur.execute(query, params)
    products = cur.fetchall()

    # =========================
    # 홈 이미지 데이터
    # =========================
    cur.execute("""
        SELECT *
        FROM home_media
        WHERE is_active = 1
        ORDER BY sort_order ASC, id ASC
    """)

    home_media_rows = cur.fetchall()

    home_media = {
        row["slot_key"]: row
        for row in home_media_rows
    }

    hero_media = [
        home_media.get("home_hero_1"),
        home_media.get("home_hero_2"),
        home_media.get("home_hero_3"),
        home_media.get("home_hero_4"),
        home_media.get("home_hero_5"),
    ]

    story_media = {
        "main": home_media.get("home_story_main"),
        "sub_1": home_media.get("home_story_sub_1"),
        "sub_2": home_media.get("home_story_sub_2"),
        "sub_3": home_media.get("home_story_sub_3"),
    }

    conn.close()

    return render_template(
        "shop/home.html",
        products=products,
        search=search,
        sort=sort,
        collection=collection,
        hero_media=hero_media,
        home_media=home_media,
        story_media=story_media
    )

@product_bp.route("/shop")
def shop():
    db = get_db()

    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "latest").strip()
    category = request.args.get("category", "").strip().upper()
    price_range = request.args.get("price_range", "").strip()
    tag = request.args.get("tag", "").strip().upper()
    material = request.args.get("material", "").strip().upper()

    valid_categories = {
        "RING": "Ring",
        "NECKLACE": "Necklace",
        "EARRINGS": "Earrings",
        "BRACELET": "Bracelet",
        "ANKLET": "Anklet"
    }

    valid_tags = {
        "NEW": "New",
        "SEASON": "Season Item",
        "BEST": "Best"
    }

    valid_materials = {
        "DIAMOND": "Diamond",
        "GOLDBAR": "Gold Bar",
        "24K": "24K",
        "18K": "18K",
        "14K": "14K",
        "SILVER": "Silver"
    }

    # NEW 전용 기획전 페이지
    if tag == "NEW":
        products = db.execute(
            """
            SELECT *
            FROM products
            WHERE tag = ?
            ORDER BY id DESC
            """,
            ("NEW",)
        ).fetchall()

        products = attach_rating_to_products(db, products)

        wished_product_ids = []

        if session.get("username"):
            wished_rows = db.execute(
                """
                SELECT product_id
                FROM wishlists
                WHERE username = ?
                """,
                (session.get("username"),)
            ).fetchall()

            wished_product_ids = [row["product_id"] for row in wished_rows]

        hero_media = get_page_hero_media(db, "page_hero_new")

        return render_template(
            "shop/new.html",
            products=products,
            wished_product_ids=wished_product_ids,
            hero_media=hero_media
        )

    query = "SELECT * FROM products WHERE 1=1"
    params = []

    # 검색
    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")

    # 카테고리 필터
    if category in valid_categories:
        query += " AND collection = ?"
        params.append(category)

    # 가격대 필터
    if price_range == "0_50":
        query += " AND price >= ? AND price < ?"
        params.extend([0, 500000])

    elif price_range == "50_100":
        query += " AND price >= ? AND price < ?"
        params.extend([500000, 1000000])

    elif price_range == "100_150":
        query += " AND price >= ? AND price < ?"
        params.extend([1000000, 1500000])

    elif price_range == "150_200":
        query += " AND price >= ? AND price < ?"
        params.extend([1500000, 2000000])

    elif price_range == "200_up":
        query += " AND price >= ?"
        params.append(2000000)

    # 정렬
    if sort == "price_low":
        query += " ORDER BY price ASC"
    elif sort == "price_high":
        query += " ORDER BY price DESC"
    elif sort == "name":
        query += " ORDER BY name ASC"
    elif sort == "oldest":
        query += " ORDER BY id ASC"
    else:
        query += " ORDER BY id DESC"

    products = db.execute(query, params).fetchall()
    products = attach_rating_to_products(db, products)

    # 로그인한 사용자의 위시리스트 상품 id 목록
    wished_product_ids = []

    if session.get("username"):
        wished_rows = db.execute(
            """
            SELECT product_id
            FROM wishlists
            WHERE username = ?
            """,
            (session.get("username"),)
        ).fetchall()

        wished_product_ids = [row["product_id"] for row in wished_rows]

    product_count = len(products)
    category_label = valid_categories.get(category, "All Jewelry")

    # SHOP / 카테고리별 히어로 슬롯
    hero_slot_map = {
        "RING": "page_hero_shop_ring",
        "NECKLACE": "page_hero_shop_necklace",
        "EARRINGS": "page_hero_shop_earrings",
        "BRACELET": "page_hero_shop_bracelet",
        "ANKLET": "page_hero_shop_anklet",
    }

    hero_slot_key = hero_slot_map.get(category, "page_hero_shop")

    shop_hero_media = db.execute("""
        SELECT *
        FROM home_media
        WHERE slot_key = ?
          AND is_active = 1
        LIMIT 1
    """, (hero_slot_key,)).fetchone()

    # 카테고리 전용 히어로가 없으면 기본 SHOP 히어로로 대체
    if shop_hero_media is None and hero_slot_key != "page_hero_shop":
        shop_hero_media = db.execute("""
            SELECT *
            FROM home_media
            WHERE slot_key = ?
              AND is_active = 1
            LIMIT 1
        """, ("page_hero_shop",)).fetchone()

    return render_template(
        "shop/index.html",
        products=products,
        shop_hero_media=shop_hero_media,
        search=search,
        sort=sort,
        category=category,
        category_label=category_label,
        product_count=product_count,
        price_range=price_range,
        wished_product_ids=wished_product_ids
    )

@product_bp.route("/product/<int:product_id>/review", methods=["POST"])
def add_review(product_id):
    # 로그인 안 했으면 로그인 페이지로 이동
    if "username" not in session:
        return redirect(url_for("auth.login"))

    rating = request.form.get("rating", "5")
    content = request.form.get("content") or request.form.get("review_text") or ""

    content = content.strip()

    if not content:
        return redirect(url_for("product.product_detail", product_id=product_id) + "#reviews")

    try:
        rating = int(rating)
    except ValueError:
        rating = 5

    if rating < 1:
        rating = 1
    if rating > 5:
        rating = 5

    db = get_db()

    db.execute("""
        INSERT INTO product_reviews (
            product_id,
            username,
            rating,
            content
        )
        VALUES (?, ?, ?, ?)
    """, (
        product_id,
        session.get("username"),
        rating,
        content
    ))

    db.commit()

    return redirect(request.referrer or url_for("product.home"))

@product_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    db = get_db()

    product = db.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        return redirect("/shop")

    # 리뷰 목록
    reviews = db.execute("""
        SELECT *
        FROM product_reviews
        WHERE product_id = ?
        ORDER BY id DESC
    """, (product_id,)).fetchall()

    # 실제 리뷰 기준 평균 평점 / 리뷰 개수
    rating_summary = get_product_rating(db, product_id)
    review_count = rating_summary["review_count"]
    avg_rating = rating_summary["avg_rating"]

    # 점수별 리뷰 개수: 5점, 4점, 3점, 2점, 1점
    rating_rows = db.execute("""
        SELECT 
            CAST(rating AS INTEGER) AS score,
            COUNT(*) AS count
        FROM product_reviews
        WHERE product_id = ?
          AND CAST(rating AS INTEGER) BETWEEN 1 AND 5
        GROUP BY CAST(rating AS INTEGER)
    """, (product_id,)).fetchall()

    rating_counts = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0
    }

    for row in rating_rows:
        rating_counts[row["score"]] = row["count"]

    rating_percentages = {}

    for score in range(1, 6):
        if review_count > 0:
            rating_percentages[score] = round((rating_counts[score] / review_count) * 100)
        else:
            rating_percentages[score] = 0

    # 비슷한 상품 추천
    related_products = db.execute("""
        SELECT *
        FROM products
        WHERE id != ?
          AND (
                collection = ?
                OR material = ?
          )
        ORDER BY
            CASE
                WHEN collection = ? THEN 0
                ELSE 1
            END,
            id DESC
        LIMIT 4
    """, (
        product_id,
        product["collection"],
        product["material"],
        product["collection"]
    )).fetchall()

    # 비슷한 상품에도 실제 평점 붙이기
    related_products = attach_rating_to_products(db, related_products)

    # 큰 이미지 + 작은 썸네일 이미지들
    detail_images = []

    for image_col in ["image", "detail_image_1", "detail_image_2", "detail_image_3"]:
        if image_col in product.keys() and product[image_col]:
            detail_images.append(product[image_col])

    # =========================
    # 새 가격 / 옵션 데이터
    # =========================
    material_price_data = get_product_material_price_data(db, product_id)

    default_material = "14K"

    if default_material not in material_price_data:
        if material_price_data:
            default_material = list(material_price_data.keys())[0]
        else:
            default_material = "14K"

    default_price = 0

    if default_material in material_price_data:
        default_price = material_price_data[default_material]["discounted_price"]
    else:
        default_price = safe_int(product["price"], 0) if "price" in product.keys() else 0

    option_groups = get_product_option_groups(db, product_id)

    back_url = request.args.get("back", "/shop")

    # 이상한 외부 주소 방지
    if not back_url.startswith("/") or back_url.startswith("//"):
        back_url = "/shop"

    return render_template(
        "shop/detail.html",
        product=product,
        reviews=reviews,
        review_count=review_count,
        avg_rating=avg_rating,
        related_products=related_products,
        detail_images=detail_images,
        rating_counts=rating_counts,
        rating_percentages=rating_percentages,
        back_url=back_url,
        material_price_data=material_price_data,
        material_price_json=json.dumps(material_price_data, ensure_ascii=False),
        default_material=default_material,
        default_price=default_price,
        option_groups=option_groups,
        option_groups_json=json.dumps(option_groups, ensure_ascii=False),
    )

STORY_CATEGORIES = {
    "gyeol-yeon": {
        "title": "결 ; 연",
        "subtitle": "인연의 시작",
        "keyword": "Connection",
        "description":"우연이라 부르기엔 너무도 정교한, 당신과 나의 결이 만난 찰나를 기록합니다.",
        "message": "당신의 결이, 우리의 연이 됩니다."
    },
    "sum-gyeol": {
        "title": "숨 ; 결",
        "subtitle": "'탄생과 이별'",
        "keyword": "Breath",
        "description": "당신의 하루를 감싸는, 고요한 숨결.",
        "message": "숨;결’은 그 고요한 흔적을 주얼리에 담아, 당신의 기억을 지켜드립니다."
    },
    "sim-gyeol": {
        "title": "심 ; 결",
        "subtitle": "마음의 감정",
        "keyword": "Heart",
        "description": "당신의 마음이 누군가의 심장에 닿는 순간.",
        "message": "마음이 남기는 무늬, 심;결."
    },
    "go-gyeol": {
        "title": "고 ; 결",
        "subtitle": "고귀함과 전통",
        "keyword": "Nobility",
        "description": "겹의 미학, 시대를 초월한 고귀함.",
        "message": "고;결 — 세월이 만드는 품격."
    },
    "gan-gyeol": {
        "title": "간 ; 결",
        "subtitle": "미니멀리즘",
        "keyword": "Minimal",
        "description": "Balance.",
        "message": "본질로의 회귀, 비움이 만든 여유."
    },
    "bit-gyeol": {
        "title": "빛 ; 결",
        "subtitle": "행복, 기쁜, 온기",
        "keyword": "Light",
        "description": "빛의 온기.",
        "message": "당신의 빛이 나는 마음, 그 빛의 결을 기록합니다."
    },
    "gyeol-yak": {
        "title": "결 ; 약",
        "subtitle": "약혹, 약속, 영원",
        "keyword": "Promise",
        "description": "서로를 이어주는 매듭, 평생을 지켜갈 약속.",
        "message": "우리가 만든 작은 선서, 영원까지 이어집니다."
    },
    "hon-gyeol": {
        "title": "혼 ; 결",
        "subtitle": "기억, 추억, 그리움",
        "keyword": "Marriage",
        "description": "흔적의 조각을 이어주는 선(結).",
        "message": "추억은 사라지지 않습니다, 결이 되어 영원히."
    },
    "gyeol-sok": {
        "title": "결 ; 속",
        "subtitle": "가족, 모임, 우정",
        "keyword": "Continuity",
        "description": "펄스 오브 어스(Pulse of Us).",
        "message": "쌓이는 날만큼 깊어지는 결."
    },
    "gyeol-chae": {
        "title": "결 ; 채",
        "subtitle": "축제, 축하, 환영",
        "keyword": "Color",
        "description": "Ribbon Knot(리본 매듭).",
        "message": "축하의 결을 채우다, 결;채."
    }
}


@product_bp.route("/story")
def story():
    return render_template(
        "shop/story.html",
        stories=STORY_CATEGORIES
    )


@product_bp.route("/story/<slug>")
def story_detail(slug):
    story_pages = {
        "yeon": {
            "template": "shop/stories/yeon.html",
            "collection": "GOLD"
        },
        "sum": {
            "template": "shop/stories/sum.html",
            "collection": "SILVER"
        },
        "sim": {
            "template": "shop/stories/sim.html",
            "collection": "DIAMOND"
        },
        "go": {
            "template": "shop/stories/go.html",
            "collection": "GOLD"
        },
        "gan": {
            "template": "shop/stories/gan.html",
            "collection": "SILVER"
        },
        "bit": {
            "template": "shop/stories/bit.html",
            "collection": "DIAMOND"
        },
        "yak": {
            "template": "shop/stories/yak.html",
            "collection": "SPECIAL"
        },
        "hon": {
            "template": "shop/stories/hon.html",
            "collection": "GOLD"
        },
        "sok": {
            "template": "shop/stories/sok.html",
            "collection": "SILVER"
        },
        "chae": {
            "template": "shop/stories/chae.html",
            "collection": "SPECIAL"
        }
    }

    story_page = story_pages.get(slug)

    if story_page is None:
        return "존재하지 않는 스토리입니다.", 404

    db = get_db()
    products = db.execute(
        "SELECT * FROM products WHERE collection = ? ORDER BY id DESC LIMIT 4",
        (story_page["collection"],)
    ).fetchall()

    return render_template(
        story_page["template"],
        products=products
    )

@product_bp.route("/season")
def season():
    db = get_db()

    products = db.execute("""
        SELECT *
        FROM products
        WHERE UPPER(COALESCE(tag, '')) = 'SEASON'
        ORDER BY id DESC
    """).fetchall()

    products = attach_rating_to_products(db, products)

    wished_product_ids = []

    if session.get("username"):
        wished_rows = db.execute("""
            SELECT product_id
            FROM wishlists
            WHERE username = ?
        """, (session.get("username"),)).fetchall()

        wished_product_ids = [row["product_id"] for row in wished_rows]

    hero_media = get_page_hero_media(db, "page_hero_season")

    return render_template(
        "shop/season.html",
        products=products,
        season_products=products,
        product_count=len(products),
        wished_product_ids=wished_product_ids,
        hero_media=hero_media
    )

@product_bp.route("/best")
def best():
    db = get_db()

    products = db.execute("""
        SELECT *
        FROM products
        WHERE UPPER(COALESCE(tag, '')) = 'BEST'
        ORDER BY id DESC
    """).fetchall()

    products = attach_rating_to_products(db, products)

    hero_media = get_page_hero_media(db, "page_hero_best")

    return render_template(
        "shop/best.html",
        products=products,
        hero_media=hero_media
    )

@product_bp.route("/brand-story")
def brand_story():
    return render_template("shop/brand_story.html")

@product_bp.route("/cs")
def customer_service():
    return render_template("shop/customer_service.html")

@product_bp.route("/faq")
def faq():
    db = get_db()

    faqs = db.execute("""
        SELECT *
        FROM faqs
        WHERE is_active = 1
        ORDER BY sort_order ASC, id DESC
    """).fetchall()

    return render_template("shop/faq.html", faqs=faqs)