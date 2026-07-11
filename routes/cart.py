from flask import Blueprint, session, jsonify, render_template, request, redirect, abort
from models.db import get_db, DB_PATH
import sqlite3
from datetime import datetime, timedelta
import json
import hashlib
import secrets
import hmac

# 장바구니 관련

cart_bp = Blueprint("cart", __name__)

def get_order_csrf_token():
    token = session.get("_order_csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["_order_csrf_token"] = token

    return token


@cart_bp.context_processor
def inject_order_csrf_token():
    return {
        "csrf_token": get_order_csrf_token
    }


@cart_bp.before_request
def protect_cart_security():

    login_required_endpoints = {
        "cart.cart",
        "cart.order",
        "cart.order_complete",
        "cart.add_to_cart",
        "cart.cart_update",
        "cart.cart_remove",
        "cart.buy_now",
        "cart.clear_cart"
    }

    json_endpoints = {
        "cart.add_to_cart",
        "cart.cart_update",
        "cart.cart_remove",
        "cart.buy_now",
        "cart.clear_cart"
    }

    protected_post_endpoints = {
        "cart.order",
        "cart.add_to_cart",
        "cart.cart_update",
        "cart.cart_remove",
        "cart.buy_now",
        "cart.clear_cart"
    }

    if request.endpoint in login_required_endpoints and not session.get("user_id"):
        if request.endpoint in json_endpoints:
            return jsonify({
                "success": False,
                "message": "로그인이 필요합니다.",
                "require_login": True,
                "redirect_url": "/login"
            }), 401

        return redirect("/login")

    if request.endpoint not in protected_post_endpoints:
        return

    if request.method != "POST":
        return

    session_token = session.get("_order_csrf_token")

    form_token = (
        request.form.get("_csrf_token")
        or request.form.get("csrf_token")
    )

    header_token = (
        request.headers.get("X-CSRF-Token")
        or request.headers.get("X-CSRFToken")
    )

    request_token = form_token or header_token

    if not session_token or not request_token:
        abort(400)

    if not hmac.compare_digest(session_token, request_token):
        abort(400)

def make_cart_key(product_id, options):
    options_text = json.dumps(
        options or {},
        sort_keys=True,
        ensure_ascii=False
    )

    raw_key = f"{product_id}-{options_text}"

    return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except:
        return default


def safe_float(value, default=0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except:
        return default


def row_get(row, key, default=None):
    if row is None:
        return default

    if key in row.keys() and row[key] is not None:
        return row[key]

    return default


def row_get_any(row, keys, default=None):
    for key in keys:
        if row is not None and key in row.keys() and row[key] is not None:
            return row[key]

    return default


def normalize_rate(value, default=0):
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
    return int(((value + 5000) // 10000) * 10000)


def get_latest_gold_rate(cur):
    rate_row = cur.execute("""
        SELECT *
        FROM gold_market_rates
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    if rate_row is None:
        return 0

    return safe_float(row_get(rate_row, "base_rate", 0), 0)


def calculate_material_price(material_row, gold_rate, selected_material=None):
    material = str(selected_material or row_get(material_row, "material", "14K")).upper()

    gold_weight = safe_float(row_get(material_row, "gold_weight", 0))

    labor_fee = safe_float(row_get(material_row, "labor_fee", 0))
    stone_price = safe_float(row_get(material_row, "stone_price", 0))
    extra_fee = safe_float(row_get(material_row, "extra_fee", 0))

    multiplier = safe_float(row_get(material_row, "multiplier", 1), 1)

    if multiplier <= 0:
        multiplier = 1

    vat_rate = normalize_rate(row_get(material_row, "vat_rate", 10), 0.1)
    discount_rate = normalize_rate(row_get(material_row, "discount_rate", 0), 0)

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

    # 14K 기준 입력값에서 18K 파생
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

    return discounted_price


def get_product_base_price(cur, product_id, material, fallback_price=0):
    material = str(material or "14K").upper()

    gold_rate = get_latest_gold_rate(cur)

    material_row = cur.execute("""
        SELECT *
        FROM product_material_prices
        WHERE product_id = ?
          AND UPPER(material) = ?
        ORDER BY sort_order ASC, id ASC
        LIMIT 1
    """, (product_id, material)).fetchone()

    # 18K 전용 row가 없으면 14K row에서 18K 가격 파생
    if material_row is None and material == "18K":
        material_row = cur.execute("""
            SELECT *
            FROM product_material_prices
            WHERE product_id = ?
              AND UPPER(material) = '14K'
            ORDER BY sort_order ASC, id ASC
            LIMIT 1
        """, (product_id,)).fetchone()

    if material_row is None:
        return safe_int(fallback_price, 0)

    return calculate_material_price(
        material_row,
        gold_rate,
        selected_material=material
    )


def get_option_extra_price(cur, selected_details, material):
    if not isinstance(selected_details, dict):
        return 0

    material = str(material or "14K").upper()

    total = 0

    for option in selected_details.values():
        if not isinstance(option, dict):
            continue

        row_id = safe_int(option.get("rowId") or option.get("row_id"), 0)

        if not row_id:
            continue

        value_rows = cur.execute("""
            SELECT *
            FROM product_price_values
            WHERE row_id = ?
            ORDER BY sort_order ASC, id ASC
        """, (row_id,)).fetchall()

        option_price = 0

        for value_row in value_rows:
            keys = value_row.keys()

            if material == "14K" and "price_14k" in keys:
                option_price = safe_int(value_row["price_14k"], option_price)

            if material == "18K" and "price_18k" in keys:
                option_price = safe_int(value_row["price_18k"], option_price)

            if "material" in keys and "price" in keys:
                value_material = str(value_row["material"] or "").upper()

                if value_material == material:
                    option_price = safe_int(value_row["price"], option_price)

        total += option_price

    return total

def get_simple_option_extra_price(selected_simple_options):
    if not isinstance(selected_simple_options, dict):
        return 0

    total = 0

    for option in selected_simple_options.values():
        if not isinstance(option, dict):
            continue

        total += safe_int(
            option.get("addPrice") or option.get("add_price"),
            0
        )

    return total

def make_option_text(material, selected_price_options, selected_simple_options=None, legacy_options=None):
    parts = []

    if material:
        parts.append(f"소재: {material}")

    # 호수 / 길이 같은 가격 옵션
    if isinstance(selected_price_options, dict):
        for option in selected_price_options.values():
            if not isinstance(option, dict):
                continue

            section_title = (
                option.get("sectionTitle")
                or option.get("section_title")
                or option.get("title")
                or option.get("sectionTitle")
                or "옵션"
            )

            label = option.get("label", "")

            if label:
                parts.append(f"{section_title}: {label}")

    # 선물포장 / 각인 / 메시지카드 같은 단순 옵션
    if isinstance(selected_simple_options, dict):
        for option in selected_simple_options.values():
            if not isinstance(option, dict):
                continue

            group_title = (
                option.get("groupTitle")
                or option.get("group_title")
                or option.get("title")
                or "옵션"
            )

            label = (
                option.get("label")
                or option.get("value")
                or ""
            )

            if label:
                parts.append(f"{group_title}: {label}")

    # 예전 장바구니 옵션 구조도 혹시 들어오면 대응
    if legacy_options and isinstance(legacy_options, dict):
        length = legacy_options.get("length", "")
        color = legacy_options.get("color", "")

        if length:
            parts.append(f"길이: {length}")

        if color:
            parts.append(f"색상: {color}")

    return " / ".join(parts)

# 장바구니 추가
@cart_bp.route("/add-to-cart/<int:id>", methods=["POST"])
def add_to_cart(id):

    if not session.get("user_id"):
        return jsonify({
            "success": False,
            "message": "로그인 후 장바구니에 담을 수 있습니다.",
            "require_login": True,
            "redirect_url": "/login"
        }), 401

    data = request.get_json(silent=True) or {}

    try:
        quantity = int(data.get("quantity", 1))
    except:
        quantity = 1

    if quantity < 1:
        quantity = 1

    options = data.get("options", {})

    if not isinstance(options, dict):
        options = {}

    material = (
        data.get("material")
        or options.get("material")
        or "14K"
    )

    material = str(material).upper()

    selected_price_options = (
        options.get("price_options")
        or options.get("details")
        or {}
    )

    if not isinstance(selected_price_options, dict):
        selected_price_options = {}

    selected_simple_options = options.get("simple_options", {})

    if not isinstance(selected_simple_options, dict):
        selected_simple_options = {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE id=?", (id,))
    product = cur.fetchone()

    if product is None:
        conn.close()

        return jsonify({
            "success": False,
            "message": "상품 없음"
        })

    frontend_unit_price = safe_int(data.get("unit_price"), 0)

    price_option_extra_price = 0

    if isinstance(selected_price_options, dict):
        for option in selected_price_options.values():
            if not isinstance(option, dict):
                continue

            if material == "18K":
                price_option_extra_price += safe_int(
                    option.get("price18k")
                    or option.get("price_18k"),
                    0
                )
            else:
                price_option_extra_price += safe_int(
                    option.get("price14k")
                    or option.get("price_14k"),
                    0
                )

    simple_option_extra_price = get_simple_option_extra_price(
        selected_simple_options
    )

    option_extra_price = price_option_extra_price + simple_option_extra_price

    if frontend_unit_price > 0:
        unit_price = frontend_unit_price
        base_price = max(unit_price - option_extra_price, 0)
    else:
        base_price = get_product_base_price(
            cur,
            id,
            material,
            product["price"]
        )

        db_price_option_extra_price = get_option_extra_price(
            cur,
            selected_price_options,
            material
        )

        option_extra_price = db_price_option_extra_price + simple_option_extra_price
        unit_price = base_price + option_extra_price

    conn.close()

    normalized_options = {
        "material": material,
        "price_options": selected_price_options,
        "simple_options": selected_simple_options
    }

    option_text = make_option_text(
        material,
        selected_price_options,
        selected_simple_options,
        legacy_options=options
    )

    cart = session.get("cart", [])

    if not isinstance(cart, list):
        cart = []

    cart_key = make_cart_key(id, normalized_options)

    found = False

    for item in cart:
        if item.get("cart_key") == cart_key:
            item["quantity"] = safe_int(item.get("quantity", 1), 1) + quantity

            # 금시세나 옵션가가 바뀌었을 수 있으니 현재 계산가로 갱신
            item["price"] = unit_price
            item["base_price"] = base_price
            item["option_extra_price"] = option_extra_price
            item["material"] = material
            item["options"] = normalized_options
            item["option_text"] = option_text

            found = True
            break

    if not found:
        cart.append({
            "cart_key": cart_key,
            "id": product["id"],
            "name": product["name"],
            "price": unit_price,
            "base_price": base_price,
            "option_extra_price": option_extra_price,
            "image": product["image"],
            "quantity": quantity,
            "material": material,
            "options": normalized_options,
            "option_text": option_text
        })

    session["cart"] = cart
    session.modified = True

    count = sum(
        safe_int(item.get("quantity", 1), 1)
        for item in cart
        if isinstance(item, dict)
    )

    return jsonify({
        "success": True,
        "message": "장바구니 추가 완료",
        "count": count
    })

def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except:
        return default


def make_buy_now_option_text(material, options):
    parts = []

    if material:
        parts.append(f"소재: {material}")

    if not isinstance(options, dict):
        options = {}

    if options.get("default_option"):
        parts.append("기본 옵션: 상품 설명 기준")
        return " / ".join(parts)

    price_options = (
        options.get("price_options")
        or options.get("details")
        or {}
    )

    simple_options = options.get("simple_options", {})

    if isinstance(price_options, dict):
        for option in price_options.values():
            if not isinstance(option, dict):
                continue

            section_title = (
                option.get("sectionTitle")
                or option.get("section_title")
                or option.get("title")
                or "옵션"
            )

            label = option.get("label", "")

            if label:
                parts.append(f"{section_title}: {label}")

    if isinstance(simple_options, dict):
        for option in simple_options.values():
            if not isinstance(option, dict):
                continue

            group_title = (
                option.get("groupTitle")
                or option.get("group_title")
                or option.get("title")
                or "옵션"
            )

            label = (
                option.get("label")
                or option.get("value")
                or ""
            )

            if label:
                parts.append(f"{group_title}: {label}")

    if len(parts) <= 1:
        parts.append("기본 옵션: 상품 설명 기준")

    return " / ".join(parts)


@cart_bp.route("/buy-now/<int:id>", methods=["POST"])
def buy_now(id):

    if not session.get("user_id"):
        return jsonify({
            "success": False,
            "message": "로그인 후 구매할 수 있습니다.",
            "require_login": True,
            "redirect_url": "/login"
        }), 401

    data = request.get_json(silent=True) or {}

    try:
        quantity = int(data.get("quantity", 1))
    except:
        quantity = 1

    if quantity < 1:
        quantity = 1

    options = data.get("options", {})

    if not isinstance(options, dict):
        options = {}

    material = (
        data.get("material")
        or options.get("material")
        or "14K"
    )

    material = str(material).upper()

    default_option = bool(
        data.get("default_option")
        or options.get("default_option")
    )

    selected_price_options = (
        options.get("price_options")
        or options.get("details")
        or {}
    )

    if not isinstance(selected_price_options, dict):
        selected_price_options = {}

    selected_simple_options = options.get("simple_options", {})

    if not isinstance(selected_simple_options, dict):
        selected_simple_options = {}

    normalized_options = {
        "material": material,
        "price_options": selected_price_options,
        "simple_options": selected_simple_options,
        "default_option": default_option
    }

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE id = ?", (id,))
    product = cur.fetchone()

    conn.close()

    if product is None:
        return jsonify({
            "success": False,
            "message": "상품 없음"
        }), 404

    # 기본 바로구매는 대표 가격 기준.
    # 옵션 드로어에서 구매할 때는 프론트에서 계산된 unit_price를 우선 사용.
    unit_price = safe_int(
        data.get("unit_price"),
        safe_int(product["price"], 0)
    )

    if unit_price <= 0:
        unit_price = safe_int(product["price"], 0)

    option_text = make_buy_now_option_text(
        material,
        normalized_options
    )

    buy_now_item = {
        "cart_key": make_cart_key(id, normalized_options),
        "id": product["id"],
        "name": product["name"],
        "price": unit_price,
        "image": product["image"],
        "quantity": quantity,
        "material": material,
        "options": normalized_options,
        "option_text": option_text,
        "is_buy_now": True
    }

    session["buy_now_items"] = [buy_now_item]
    session.modified = True

    return jsonify({
        "success": True,
        "message": "바로 구매로 이동합니다.",
        "redirect_url": "/order?mode=buy_now"
    })

# 장바구니 페이지
@cart_bp.route("/cart")
def cart():

    cart_items = session.get("cart", [])

    if not isinstance(cart_items, list):
        cart_items = []

    fixed_cart_items = []

    for item in cart_items:
        if not isinstance(item, dict):
            continue

        item.setdefault("id", 0)
        item.setdefault("name", "상품명 없음")
        item.setdefault("price", 0)
        item.setdefault("image", "")
        item.setdefault("quantity", 1)
        item.setdefault("options", {})
        item.setdefault("option_text", "")

        if not item.get("cart_key"):
            item["cart_key"] = make_cart_key(
                item.get("id", 0),
                item.get("options", {})
            )

        try:
            item["price"] = int(item["price"])
        except:
            item["price"] = 0

        try:
            item["quantity"] = int(item["quantity"])
        except:
            item["quantity"] = 1

        if item["quantity"] < 1:
            item["quantity"] = 1

        fixed_cart_items.append(item)

    session["cart"] = fixed_cart_items
    session.modified = True

    total = sum(
        item["price"] * item["quantity"]
        for item in fixed_cart_items
    )

    back_url = request.args.get("back", "/shop")

    if not back_url.startswith("/") or back_url.startswith("//"):
        back_url = "/shop"

    return render_template(
        "shop/cart.html",
        cart_items=fixed_cart_items,
        total=total,
        back_url=back_url
    )


# 카운트
@cart_bp.route("/cart-count")
def cart_count():

    cart = session.get("cart", [])

    if not isinstance(cart, list):
        cart = []

    count = 0

    for item in cart:
        if isinstance(item, dict):
            try:
                count += int(item.get("quantity", 1))
            except:
                count += 1

    return jsonify({"count": count})

@cart_bp.route("/cart/update", methods=["POST"])
def cart_update():

    data = request.get_json() or {}

    cart_key = data.get("cart_key")
    action = data.get("action")

    cart = session.get("cart", [])

    for item in cart:
        if item.get("cart_key") == cart_key:

            if action == "plus":
                item["quantity"] += 1

            elif action == "minus":
                if item["quantity"] > 1:
                    item["quantity"] -= 1

            break

    session["cart"] = cart
    session.modified = True

    count = sum(item["quantity"] for item in cart)

    return jsonify({
        "success": True,
        "count": count
    })

@cart_bp.route("/cart/remove", methods=["POST"])
def cart_remove():

    data = request.get_json() or {}

    cart_key = data.get("cart_key")

    cart = session.get("cart", [])

    cart = [
        item for item in cart
        if item.get("cart_key") != cart_key
    ]

    session["cart"] = cart
    session.modified = True

    count = sum(item["quantity"] for item in cart)

    return jsonify({
        "success": True,
        "count": count
    })

@cart_bp.route("/cart/clear", methods=["POST"])
def clear_cart():

    session["cart"] = []
    session.modified = True

    return jsonify({
        "success": True,
        "count": 0
    })

@cart_bp.route("/order", methods=["GET", "POST"])
def order():

    if not session.get("user_id"):
        return redirect("/login")

    checkout_mode = (
        request.args.get("mode")
        or request.form.get("checkout_mode")
        or ""
    )

    if checkout_mode == "buy_now":
        cart_items = session.get("buy_now_items", [])
    else:
        cart_items = session.get("cart", [])

    if not cart_items:
        if checkout_mode == "buy_now":
            return redirect("/shop")
        return redirect("/cart")

    total = sum(
        safe_int(item.get("price", 0), 0) * safe_int(item.get("quantity", 1), 1)
        for item in cart_items
        if isinstance(item, dict)
    )

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not name or not phone or not address:
            return redirect("/order")

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        user_id = session.get("user_id")

        korea_time = datetime.utcnow() + timedelta(hours=9)
        created_at = korea_time.strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
            INSERT INTO orders (customer_name, phone, address, total_price, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, phone, address, total, user_id, created_at))

        order_id = cur.lastrowid

        for item in cart_items:

            cur.execute("""
            INSERT INTO order_items
            (
                order_id,
                product_name,
                price,
                quantity,
                option_text
            )
            VALUES (?, ?, ?, ?, ?)
            """, (
               order_id,
               item["name"],
               safe_int(item.get("price", 0), 0),
               safe_int(item.get("quantity", 1), 1),
               item.get("option_text", "")
            ))

        conn.commit()
        conn.close()

        # 주문 완료 후 장바구니 비우기
        if checkout_mode == "buy_now":
            session.pop("buy_now_items", None)
        else:
            session["cart"] = []

        session.modified = True

        return redirect(f"/order-complete?order_id={order_id}")
    
    return render_template(
        "shop/order.html",
        cart_items=cart_items,
        total=total
    )

@cart_bp.route("/order-complete")
def order_complete():

    if not session.get("user_id"):
        return redirect("/login")

    order_id = request.args.get("order_id", type=int)

    if not order_id:
        return redirect("/mypage")

    db = get_db()

    order = db.execute("""
        SELECT id
        FROM orders
        WHERE id = ? AND user_id = ?
    """, (order_id, session.get("user_id"))).fetchone()

    if not order:
        return redirect("/mypage")

    return render_template(
        "shop/order_complete.html",
        order_id=order_id
    )