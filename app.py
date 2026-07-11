from flask import Flask, send_from_directory, session, jsonify, request, redirect, url_for, render_template
import os
import sqlite3
import secrets
from models.db import get_db
from dotenv import load_dotenv
from routes.wishlist import wishlist_bp
from models.db import DB_PATH
from datetime import timedelta


# 현재 app.py가 있는 폴더 기준 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# .env 파일 불러오기
load_dotenv(os.path.join(BASE_DIR, ".env"))

from routes.product import product_bp
from routes.cart import cart_bp
from routes.admin import admin_bp
from routes.auth import auth_bp

app = Flask(__name__)

@app.context_processor
def inject_home_media():
    home_media = {}

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM home_media
            WHERE is_active = 1
        """)

        rows = cur.fetchall()

        home_media = {
            row["slot_key"]: row
            for row in rows
        }

        conn.close()

    except Exception as e:
        print("home_media context error:", e)

    return {
        "home_media": home_media
    }

# secret key

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-later")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

if os.getenv("FLASK_ENV") == "production":
    app.config["SESSION_COOKIE_SECURE"] = True
else:
    app.config["SESSION_COOKIE_SECURE"] = False

def get_cart_csrf_token():
    token = session.get("_order_csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["_order_csrf_token"] = token

    return token


@app.context_processor
def inject_global_cart_csrf_token():
    return {
        "csrf_token": get_cart_csrf_token
    }


# uploads 설정

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 *1024

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.context_processor
def inject_cart_count():
    cart = session.get("cart", {})

    cart_count = 0

    # cart가 딕셔너리 형태일 때
    if isinstance(cart, dict):
        for item in cart.values():
            if isinstance(item, dict):
                cart_count += item.get("quantity", 1)
            else:
                cart_count += 1

    # cart가 리스트 형태일 때
    elif isinstance(cart, list):
        for item in cart:
            if isinstance(item, dict):
                cart_count += item.get("quantity", 1)
            else:
                cart_count += 1

    # cart가 이상한 형태면 0으로 처리
    else:
        cart_count = 0

    return {
        "cart_count": cart_count
    }

# blueprint 등록

app.register_blueprint(product_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(wishlist_bp)

# DB 초기화

def init_db():
    print("DB 초기화 실행됨")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        image TEXT
    )
    """)

    # 주문 테이블
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        phone TEXT,
        address TEXT,
        total_price INTEGER,
        status TEXT DEFAULT '주문접수',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_name TEXT,
        price INTEGER,
        quantity INTEGER
    )
    """)

    conn.commit()
    conn.close()

@app.route("/")
def home():
    return "Flask 정상 작동"

@app.context_processor
def inject_user():
    return dict(
        user_name=session.get("user_name"),
        user_id=session.get("user_id")
    )

# 실행
if __name__ == "__main__":
    init_db()

    is_production = os.getenv("FLASK_ENV") == "production"

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=not is_production
    )