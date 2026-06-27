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
        "cart.clear_cart"
    }

    json_endpoints = {
        "cart.add_to_cart",
        "cart.cart_update",
        "cart.cart_remove",
        "cart.clear_cart"
    }

    protected_post_endpoints = {
        "cart.order",
        "cart.add_to_cart",
        "cart.cart_update",
        "cart.cart_remove",
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
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE id=?", (id,))
    product = cur.fetchone()

    conn.close()

    if product is None:
        return jsonify({
            "success": False,
            "message": "상품 없음"
        })

    cart = session.get("cart", [])

    # POST로 옵션이 들어오면 받기
    data = request.get_json(silent=True) or {}

    options = data.get("options", {})

    try:
        quantity = int(data.get("quantity", 1))
    except:
        quantity = 1

    if quantity < 1:
        quantity = 1

    cart_key = make_cart_key(id, options)

    material = options.get("material", "")
    length = options.get("length", "")
    color = options.get("color", "")

    option_text_parts = []

    if material:
        option_text_parts.append(f"함량: {material}")

    if length:
        option_text_parts.append(f"길이: {length}")

    if color:
        option_text_parts.append(f"색상: {color}")

    option_text = " / ".join(option_text_parts)

    # 같은 상품 + 같은 옵션이면 수량 증가
    found = False

    for item in cart:
        if item.get("cart_key") == cart_key:
            item["quantity"] += quantity
            found = True
            break

    if not found:
        cart.append({
            "cart_key": cart_key,
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "image": product["image"],
            "quantity": quantity,
            "options": options,
            "option_text": option_text
        })

    session["cart"] = cart
    session.modified = True

    count = sum(item["quantity"] for item in cart)

    return jsonify({
        "success": True,
        "message": "장바구니 추가 완료",
        "count": count
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

    cart_items = session.get("cart", [])

    if not cart_items :
        return redirect("/cart")

    total = sum(
        item["price"] * item["quantity"]
        for item in cart_items
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
               item["price"],
               item["quantity"],
               item.get("option_text")
            ))

        conn.commit()
        conn.close()

        # 주문 완료 후 장바구니 비우기
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