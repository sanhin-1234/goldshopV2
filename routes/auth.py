from flask import Blueprint, render_template, request, redirect, session, abort
from models.db import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import hmac

auth_bp = Blueprint("auth", __name__)

def get_csrf_token():
    token = session.get("_user_csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["_user_csrf_token"] = token

    return token


@auth_bp.context_processor
def inject_user_csrf_token():
    return {
        "csrf_token": get_csrf_token
    }


@auth_bp.before_request
def protect_auth_csrf():

    if request.method != "POST":
        return

    session_token = session.get("_user_csrf_token")
    form_token = request.form.get("_csrf_token")

    if not session_token or not form_token:
        abort(400)

    if not hmac.compare_digest(session_token, form_token):
        abort(400)

# 회원가입
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()

        if not username or not password or not name:
            error = "모든 항목을 입력해주세요."
            return render_template("shop/signup.html", error=error)

        password_hash = generate_password_hash(password)

        conn = get_db()
        cur = conn.cursor()

        existing_user = cur.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        if existing_user:
            conn.close()
            error = "이미 사용 중인 아이디입니다."
            return render_template("shop/signup.html", error=error)

        cur.execute(
            """
            INSERT INTO users(username, password, name)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, name)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("shop/signup.html", error=error)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()

        user = db.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session.permanent = True

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["name"] = user["name"]

            return redirect("/")

        error = "아이디 혹은 패스워드 정보가 일치하지 않습니다."

    return render_template("shop/login.html", error=error)

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/shop")

@auth_bp.route("/mypage")
def mypage():
    if not session.get("user_id"):
        return redirect("/login")

    db = get_db()

    orders = db.execute("""
        SELECT *
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session.get("user_id"),)).fetchall()

    return render_template("shop/mypage.html", orders=orders)

@auth_bp.route("/mypage/order/<int:order_id>")
def my_order_detail(order_id):
    if not session.get("user_id"):
        return redirect("/login")

    db = get_db()

    order = db.execute("""
        SELECT *
        FROM orders
        WHERE id = ? AND user_id = ?
    """, (order_id, session.get("user_id"))).fetchone()

    if not order:
        return redirect("/mypage")

    items = db.execute("""
        SELECT *
        FROM order_items
        WHERE order_id = ?
    """, (order_id,)).fetchall()

    return render_template(
        "shop/my_order_detail.html",
        order=order,
        items=items
    )