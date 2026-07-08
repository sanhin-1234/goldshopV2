from flask import Blueprint, render_template, request, redirect, send_from_directory, current_app, session, abort, url_for, flash
from models.db import get_db, DB_PATH
import os
import sqlite3
import secrets
import hmac
import uuid
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, getcontext

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def get_csrf_token():
    token = session.get("_admin_csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["_admin_csrf_token"] = token

    return token


@admin_bp.context_processor
def inject_admin_csrf_token():
    return {
        "csrf_token": get_csrf_token
    }


@admin_bp.before_request
def protect_admin_csrf():

    if request.method != "POST":
        return

    session_token = session.get("_admin_csrf_token")

    form_token = (
        request.form.get("_csrf_token")
        or request.form.get("csrf_token")
    )

    if not session_token or not form_token:
        abort(400)

    if not hmac.compare_digest(session_token, form_token):
        abort(400)

@admin_bp.before_request
def protect_admin_pages():

    allowed_pages = [
        "admin.admin_login"
    ]

    if request.endpoint in allowed_pages:
        return

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():

    if session.get("admin_logged_in"):
        return redirect("/admin")

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()

        admin = db.execute("""
            SELECT *
            FROM admins
            WHERE username = ?
        """, (username,)).fetchone()

        db.close()

        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session.permanent = True

            session["admin_logged_in"] = True
            session["admin_username"] = admin["username"]

            return redirect("/admin")

        error = "관리자 정보가 일치하지 않습니다."

    return render_template("admin/login.html", error=error)


@admin_bp.route("/logout")
def admin_logout():

    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)

    return redirect("/admin/login")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "uploads")
UPLOAD_FOLDER = os.path.abspath(UPLOAD_FOLDER)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}

ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
ALLOWED_NEW_MEDIA_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS


def allowed_image_file(filename):
    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_IMAGE_EXTENSIONS


def save_product_image(image):
    if not image or image.filename == "":
        return None

    if not allowed_image_file(image.filename):
        raise ValueError("이미지 파일만 업로드할 수 있습니다. jpg, jpeg, png, webp, gif 파일만 허용됩니다.")

    safe_name = secure_filename(image.filename)
    extension = safe_name.rsplit(".", 1)[1].lower()

    new_filename = f"{uuid.uuid4().hex}.{extension}"

    image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], new_filename)

    image.save(image_path)

    return new_filename

def save_new_between_media(file):
    if not file or file.filename == "":
        return None, ""

    if "." not in file.filename:
        raise ValueError("NEW 중간 광고 파일 형식을 확인해 주세요.")

    safe_name = secure_filename(file.filename)
    extension = safe_name.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_NEW_MEDIA_EXTENSIONS:
        raise ValueError("NEW 중간 광고는 jpg, jpeg, png, webp, gif, mp4, webm, mov 파일만 업로드할 수 있습니다.")

    new_filename = f"{uuid.uuid4().hex}.{extension}"
    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], new_filename)

    file.save(file_path)

    if extension in ALLOWED_VIDEO_EXTENSIONS:
        return new_filename, "video"

    return new_filename, "image"

def save_season_between_media(file):
    if not file or file.filename == "":
        return None, ""

    if "." not in file.filename:
        raise ValueError("SEASON 중간 광고 파일 형식을 확인해 주세요.")

    safe_name = secure_filename(file.filename)
    extension = safe_name.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_NEW_MEDIA_EXTENSIONS:
        raise ValueError("SEASON 중간 광고는 jpg, jpeg, png, webp, gif, mp4, webm, mov 파일만 업로드할 수 있습니다.")

    new_filename = f"{uuid.uuid4().hex}.{extension}"
    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], new_filename)

    file.save(file_path)

    if extension in ALLOWED_VIDEO_EXTENSIONS:
        return new_filename, "video"

    return new_filename, "image"

# =========================================================
# GOLD RATE ADMIN
# =========================================================

def clean_money_value(value):
    value = value or ""
    digits = "".join(filter(str.isdigit, value))

    if not digits:
        return 0

    return int(digits)


@admin_bp.route("/gold-rate", methods=["GET", "POST"])
def admin_gold_rate():
    db = get_db()

    today_str = date.today().strftime("%Y-%m-%d")
    error = None

    if request.method == "POST":
        rate_date = request.form.get("rate_date", today_str).strip()
        pure_gold_price_per_don = clean_money_value(
            request.form.get("pure_gold_price_per_don")
        )

        if not rate_date:
            rate_date = today_str

        if pure_gold_price_per_don <= 0:
            error = "순금시세를 숫자로 입력해 주세요."
        else:
            pure_gold_price_per_gram = round(pure_gold_price_per_don / 3.75)

            existing_rate = db.execute("""
                SELECT *
                FROM gold_market_rates
                WHERE rate_date = ?
            """, (rate_date,)).fetchone()

            if existing_rate:
                db.execute("""
                    UPDATE gold_market_rates
                    SET pure_gold_price_per_don = ?,
                        pure_gold_price_per_gram = ?,
                        source = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE rate_date = ?
                """, (
                    pure_gold_price_per_don,
                    pure_gold_price_per_gram,
                    "manual",
                    rate_date
                ))
            else:
                db.execute("""
                    INSERT INTO gold_market_rates (
                        rate_date,
                        pure_gold_price_per_don,
                        pure_gold_price_per_gram,
                        source
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    rate_date,
                    pure_gold_price_per_don,
                    pure_gold_price_per_gram,
                    "manual"
                ))

            db.commit()
            flash("금 시세가 저장되었습니다.")
            return redirect(url_for("admin.admin_gold_rate"))

    latest_rate = db.execute("""
        SELECT *
        FROM gold_market_rates
        ORDER BY rate_date DESC, id DESC
        LIMIT 1
    """).fetchone()

    recent_rates = db.execute("""
        SELECT *
        FROM gold_market_rates
        ORDER BY rate_date DESC, id DESC
        LIMIT 20
    """).fetchall()

    return render_template(
        "admin/gold_rate.html",
        today_str=today_str,
        latest_rate=latest_rate,
        recent_rates=recent_rates,
        error=error
    )

# =========================================================
# JEWELRY PRICE CALCULATION - 14K BASE
# =========================================================

GOLD_PURITY_14K = Decimal("0.585")
GOLD_PURITY_18K = Decimal("0.75")
WEIGHT_RATIO_18K_FROM_14K = Decimal("1.15")
VAT_MULTIPLIER = Decimal("1.10")


def to_decimal(value, default="0"):
    try:
        if value is None:
            return Decimal(default)

        value = str(value).replace(",", "").strip()

        if value == "":
            return Decimal(default)

        return Decimal(value)

    except (InvalidOperation, ValueError):
        return Decimal(default)


def round_won(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def round_1000_won(value):
    return int(
        (Decimal(value) / Decimal("1000"))
        .quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        * Decimal("1000")
    )

def round_10000_won(value):
    return int(
        (Decimal(value) / Decimal("10000"))
        .quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        * Decimal("10000")
    )

def normalize_percent_rate(value):
    """
    할인율 변환.
    10 입력 → 0.10
    0.10 입력 → 0.10
    """
    rate = to_decimal(value, "0")

    if rate > 1:
        rate = rate / Decimal("100")

    return rate

def normalize_haeri_rate(value):
    """
    해리율 변환.
    10 입력   → 0.10
    0.10 입력 → 0.10
    1.10 입력 → 0.10
    """
    rate = to_decimal(value, "0")

    if rate >= 1:
        if rate >= 2:
            rate = rate / Decimal("100")
        else:
            rate = rate - Decimal("1")

    return rate


def get_latest_gold_rate(db):
    return db.execute("""
        SELECT *
        FROM gold_market_rates
        ORDER BY rate_date DESC, id DESC
        LIMIT 1
    """).fetchone()


def calculate_price_from_14k_weight(
    pure_gold_price_per_gram,
    weight_14k,
    labor_fee,
    multiplier,
    discount_rate,
    haeri_rate
):
    """
    14K 금중량 기준 가격 계산.

    관리자 입력값:
    - 14K 금중량
    - 총 공임
    - 배수
    - 할인율

    14K:
    순중량 = 14K 금중량 × 0.585
    금값 = 순중량 × g당 금시세
    제품원가 = 금값 + 총 공임
    기본판매가 = 제품원가 × 배수
    할인판매가 = 기본판매가 × (1 - 할인율)

    18K:
    18K 금중량 = 14K 금중량 × 1.15
    순중량 = 18K 금중량 × 0.75
    금값 = 순중량 × g당 금시세
    제품원가 = 금값 + 총 공임
    기본판매가 = 제품원가 × 배수
    할인판매가 = 기본판매가 × (1 - 할인율)
    """

    gram_price = to_decimal(pure_gold_price_per_gram)
    weight_14k = to_decimal(weight_14k)
    labor_fee = to_decimal(labor_fee)
    multiplier = to_decimal(multiplier, "1.20")
    discount_rate = normalize_percent_rate(discount_rate)
    haeri_rate = normalize_haeri_rate(haeri_rate)
    haeri_multiplier = Decimal("1") + haeri_rate

    # 14K 계산
    pure_weight_14k = weight_14k * GOLD_PURITY_14K
    gold_price_14k_raw = pure_weight_14k * gram_price * haeri_multiplier
    gold_price_14k = Decimal(round_1000_won(gold_price_14k_raw))
    cost_14k = gold_price_14k + labor_fee
    base_sale_price_14k_raw = cost_14k * multiplier * VAT_MULTIPLIER
    base_sale_price_14k = Decimal(round_10000_won(base_sale_price_14k_raw))
    discount_price_14k = base_sale_price_14k * (Decimal("1") - discount_rate)
    margin_amount_14k = discount_price_14k - cost_14k

    # 18K 계산
    weight_18k = weight_14k * WEIGHT_RATIO_18K_FROM_14K
    pure_weight_18k = weight_18k * GOLD_PURITY_18K
    gold_price_18k_raw = pure_weight_18k * gram_price * haeri_multiplier
    gold_price_18k = Decimal(round_1000_won(gold_price_18k_raw))
    cost_18k = gold_price_18k + labor_fee
    base_sale_price_18k_raw = cost_18k * multiplier * VAT_MULTIPLIER
    base_sale_price_18k = Decimal(round_10000_won(base_sale_price_18k_raw))
    discount_price_18k = base_sale_price_18k * (Decimal("1") - discount_rate)
    margin_amount_18k = discount_price_18k - cost_18k

    additional_price_18k = discount_price_18k - discount_price_14k

    return {
        "14K": {
            "material": "14K",
            "gold_weight": str(weight_14k.quantize(Decimal("0.01"))),
            "pure_weight": str(pure_weight_14k.quantize(Decimal("0.01"))),
            "gold_price": round_won(gold_price_14k),
            "labor_fee": round_won(labor_fee),
            "cost": round_won(cost_14k),
            "base_sale_price": round_won(base_sale_price_14k),
            "discount_rate": float(discount_rate),
            "haeri_rate": float(haeri_rate),
            "discount_price": round_won(discount_price_14k),
            "margin_amount": round_won(margin_amount_14k),
            "additional_price": 0,
        },
        "18K": {
            "material": "18K",
            "gold_weight": str(weight_18k.quantize(Decimal("0.01"))),
            "pure_weight": str(pure_weight_18k.quantize(Decimal("0.01"))),
            "gold_price": round_won(gold_price_18k),
            "labor_fee": round_won(labor_fee),
            "cost": round_won(cost_18k),
            "base_sale_price": round_won(base_sale_price_18k),
            "discount_rate": float(discount_rate),
            "haeri_rate": float(haeri_rate),
            "discount_price": round_won(discount_price_18k),
            "margin_amount": round_won(margin_amount_18k),
            "additional_price": round_won(additional_price_18k),
        }
    }


# =========================================================
# PRODUCT MATERIAL PRICE SAVE - 14K BASE
# =========================================================

def parse_admin_number(value):
    value = value or ""
    digits = "".join(filter(str.isdigit, str(value)))

    if not digits:
        return 0

    return int(digits)


def parse_admin_decimal_string(value, default="0"):
    value = str(value or "").replace(",", "").strip()

    if value == "":
        return default

    return value


def get_14k_base_price_result(db, form):
    latest_rate = get_latest_gold_rate(db)

    if not latest_rate:
        return None

    weight_14k = parse_admin_decimal_string(
        form.get("base_14k_weight")
    )

    labor_fee = parse_admin_number(
        form.get("total_labor_fee")
    )

    multiplier = parse_admin_decimal_string(
        form.get("price_multiplier"),
        "1.20"
    )

    discount_rate = parse_admin_decimal_string(
        form.get("discount_rate"),
        "0"
    )

    haeri_rate = parse_admin_decimal_string(
        form.get("haeri_rate"),
        "0"
    )

    if to_decimal(weight_14k) <= 0:
        return None

    if labor_fee <= 0:
        return None

    return calculate_price_from_14k_weight(
        pure_gold_price_per_gram=latest_rate["pure_gold_price_per_gram"],
        weight_14k=weight_14k,
        labor_fee=labor_fee,
        multiplier=multiplier,
        discount_rate=discount_rate,
        haeri_rate=haeri_rate
    )


def get_representative_product_price(db, form):
    """
    상품 카드에 표시될 대표 가격.
    기준은 무조건 14K 할인판매가.
    """

    result = get_14k_base_price_result(db, form)

    if result and result["14K"]["discount_price"] > 0:
        return result["14K"]["discount_price"]

    return 0


def save_product_material_prices(db, product_id, form):
    """
    product_material_prices에 항상 14K / 18K 두 줄 저장.
    기준 입력은 14K 금중량 하나만 사용.
    """

    db.execute("""
        DELETE FROM product_material_prices
        WHERE product_id = ?
    """, (product_id,))

    result = get_14k_base_price_result(db, form)

    if not result:
        return

    weight_14k = parse_admin_decimal_string(
        form.get("base_14k_weight")
    )

    multiplier = parse_admin_decimal_string(
        form.get("price_multiplier"),
        "1.20"
    )

    discount_rate = parse_admin_decimal_string(
        form.get("discount_rate"),
        "0"
    )

    haeri_rate = parse_admin_decimal_string(
        form.get("haeri_rate"),
        "0"
    )

    for sort_order, material_label in enumerate(["14K", "18K"], start=1):
        data = result[material_label]

        db.execute("""
            INSERT INTO product_material_prices (
                product_id,
                material,
                gold_weight,
                base_price,
                sort_order,
                labor_fee,
                stone_price,
                extra_fee,
                loss_rate,
                margin_multiplier,
                calculated_cost,
                is_manual_price,
                pure_weight,
                gold_price,
                discount_rate,
                discount_price,
                base_14k_weight
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            material_label,
            data["gold_weight"],
            data["base_sale_price"],
            sort_order,
            data["labor_fee"],
            0,
            data["additional_price"],
            haeri_rate,
            multiplier,
            data["cost"],
            0,
            data["pure_weight"],
            data["gold_price"],
            discount_rate,
            data["discount_price"],
            weight_14k
        ))

# =========================================================
# FAQ ADMIN
# =========================================================

FAQ_CATEGORIES = {
    "ORDER": "주문 / 결제",
    "DELIVERY": "배송",
    "EXCHANGE": "교환 / 반품",
    "PRODUCT": "상품 / 관리",
    "MEMBER": "회원"
}


@admin_bp.route("/faq")
def admin_faqs():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    db = get_db()

    faqs = db.execute("""
        SELECT *
        FROM faqs
        ORDER BY sort_order ASC, id DESC
    """).fetchall()

    return render_template(
        "admin/faqs.html",
        faqs=faqs,
        categories=FAQ_CATEGORIES
    )


@admin_bp.route("/faq/add", methods=["POST"])
def admin_add_faq():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    category = request.form.get("category", "").strip()
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()
    sort_order = request.form.get("sort_order", "0").strip()
    is_active = 1 if request.form.get("is_active") == "1" else 0

    if not sort_order.isdigit():
        sort_order = 0
    else:
        sort_order = int(sort_order)

    if not category or not question or not answer:
        return redirect(url_for("admin.admin_faqs"))

    db = get_db()

    db.execute("""
        INSERT INTO faqs (category, question, answer, sort_order, is_active)
        VALUES (?, ?, ?, ?, ?)
    """, (category, question, answer, sort_order, is_active))

    db.commit()

    return redirect(url_for("admin.admin_faqs"))


@admin_bp.route("/faq/update/<int:faq_id>", methods=["POST"])
def admin_update_faq(faq_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    category = request.form.get("category", "").strip()
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()
    sort_order = request.form.get("sort_order", "0").strip()
    is_active = 1 if request.form.get("is_active") == "1" else 0

    if not sort_order.isdigit():
        sort_order = 0
    else:
        sort_order = int(sort_order)

    db = get_db()

    db.execute("""
        UPDATE faqs
        SET category = ?,
            question = ?,
            answer = ?,
            sort_order = ?,
            is_active = ?
        WHERE id = ?
    """, (category, question, answer, sort_order, is_active, faq_id))

    db.commit()

    return redirect(url_for("admin.admin_faqs"))


@admin_bp.route("/faq/delete/<int:faq_id>", methods=["POST"])
def admin_delete_faq(faq_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    db = get_db()

    db.execute("""
        DELETE FROM faqs
        WHERE id = ?
    """, (faq_id,))

    db.commit()

    return redirect(url_for("admin.admin_faqs"))

# 관리자 페이지
@admin_bp.route("/")
def admin_home():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    conn.close()

    return render_template("admin/admin.html", products=products)

# 상품 추가
@admin_bp.route("/add", methods=["GET", "POST"])
def add_product():
    db = get_db()

    latest_rate = get_latest_gold_rate(db)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        collection = request.form.get("collection", "").strip().upper()
        sub_category = request.form.get("sub_category", "").strip().upper()
        tag = request.form.get("tag", "").strip().upper()
        material = request.form.get("material", "").strip().upper()

        image = request.files.get("image")
        new_banner_image = request.files.get("new_banner_image")
        new_between_media = request.files.get("new_between_media")

        season_banner_image = request.files.get("season_banner_image")
        season_between_media = request.files.get("season_between_media")

        if not name:
            return render_template(
                "admin/add_product.html",
                error="상품명을 입력해 주세요.",
                latest_rate=latest_rate
            )

        if not collection:
            return render_template(
                "admin/add_product.html",
                error="컬렉션을 선택해 주세요.",
                latest_rate=latest_rate
            )

        representative_price = get_representative_product_price(db, request.form)

        if representative_price <= 0:
            return render_template(
                "admin/add_product.html",
                error="14K 금중량, 총 공임, 해리율, 배수, 할인율을 입력해 주세요.",
                latest_rate=latest_rate
            )

        filename = None
        new_banner_filename = None
        new_between_filename = None
        new_between_media_type = ""

        season_banner_filename = None
        season_between_filename = None
        season_between_media_type = ""

        try:
            filename = save_product_image(image)

            new_banner_filename = save_product_image(new_banner_image)
            new_between_filename, new_between_media_type = save_new_between_media(new_between_media)

            season_banner_filename = save_product_image(season_banner_image)
            season_between_filename, season_between_media_type = save_season_between_media(season_between_media)

        except ValueError as e:
            return render_template(
                "admin/add_product.html",
                error=str(e),
                latest_rate=latest_rate
            )

        cursor = db.execute(
            """
            INSERT INTO products (
                name,
                price,
                image,
                description,
                collection,
                sub_category,
                tag,
                material,
                new_banner_image,
                new_between_media,
                new_between_media_type,
                season_banner_image,
                season_between_media,
                season_between_media_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                representative_price,
                filename,
                description,
                collection,
                sub_category,
                tag,
                material,
                new_banner_filename,
                new_between_filename,
                new_between_media_type,
                season_banner_filename,
                season_between_filename,
                season_between_media_type
            )
        )

        product_id = cursor.lastrowid

        save_product_material_prices(db, product_id, request.form)

        db.commit()

        return redirect("/admin")

    return render_template(
        "admin/add_product.html",
        latest_rate=latest_rate
    )

# 이미지 서빙 (중요)
@admin_bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# 상품 삭제
@admin_bp.route("/delete-product/<int:id>", methods=["POST"])
def delete_product(id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

@admin_bp.route("/orders")
def admin_orders():

    page = request.args.get("page", 1, type=int)
    per_page = 20

    status_filter = request.args.get("status", "all").strip()
    keyword = request.args.get("q", "").strip()

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    month_start_str = today.replace(day=1).strftime("%Y-%m-%d")

    allowed_statuses = [
        "all",
        "배송준비중",
        "배송중",
        "배송완료"
    ]

    if status_filter not in allowed_statuses:
        status_filter = "all"

    def is_valid_date(value):
        if not value:
            return False

        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    if not is_valid_date(start_date):
        start_date = ""

    if not is_valid_date(end_date):
        end_date = ""

    if page < 1:
        page = 1

    offset = (page - 1) * per_page

    where_parts = []
    params = []

    # 배송상태 필터
    if status_filter == "배송준비중":
        where_parts.append("""
            (
                status = ?
                OR status IS NULL
                OR status = ''
            )
        """)
        params.append("배송준비중")

    elif status_filter != "all":
        where_parts.append("status = ?")
        params.append(status_filter)

    # 고객명 / 전화번호 / 주문번호 검색
    if keyword:
        where_parts.append("""
            (
                customer_name LIKE ?
                OR phone LIKE ?
                OR CAST(id AS TEXT) LIKE ?
            )
        """)
        search_keyword = f"%{keyword}%"
        params.extend([
            search_keyword,
            search_keyword,
            search_keyword
        ])

    # 시작일 검색
    if start_date:
        where_parts.append("DATE(created_at) >= DATE(?)")
        params.append(start_date)

    # 종료일 검색
    if end_date:
        where_parts.append("DATE(created_at) <= DATE(?)")
        params.append(end_date)

    where_clause = ""

    if where_parts:
        where_clause = "WHERE " + " AND ".join(where_parts)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    def get_total_value(cursor):
        row = cursor.fetchone()

        if row is None:
            return 0

        return row["total"] or 0

    # 필터 + 검색 + 기간 적용된 전체 주문 개수
    cur.execute(f"""
        SELECT COUNT(*) AS total
        FROM orders
        {where_clause}
    """, params)

    total_orders = get_total_value(cur)

    # 관리자 상단 요약 카드용 데이터
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM orders
    """)
    summary_total_orders = get_total_value(cur)

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status = ?
           OR status IS NULL
           OR status = ''
    """, ("배송준비중",))
    summary_ready_orders = get_total_value(cur)

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status = ?
    """, ("배송중",))
    summary_shipping_orders = get_total_value(cur)

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status = ?
    """, ("배송완료",))
    summary_done_orders = get_total_value(cur)

    cur.execute("""
        SELECT COALESCE(SUM(total_price), 0) AS total
        FROM orders
        WHERE DATE(created_at) >= DATE(?)
          AND DATE(created_at) <= DATE(?)
    """, (month_start_str, today_str))
    summary_month_sales = get_total_value(cur)

    total_pages = (total_orders + per_page - 1) // per_page

    if total_pages < 1:
        total_pages = 1

    if page > total_pages:
        page = total_pages
        offset = (page - 1) * per_page

    # 현재 페이지 주문만 가져오기
    cur.execute(f"""
        SELECT *
        FROM orders
        {where_clause}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    orders = cur.fetchall()

    conn.close()

    return render_template(
        "admin/orders.html",
        orders=orders,
        page=page,
        per_page=per_page,
        total_orders=total_orders,
        total_pages=total_pages,
        current_status=status_filter,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        today_str=today_str,
        month_start_str=month_start_str,
        summary_total_orders=summary_total_orders,
        summary_ready_orders=summary_ready_orders,
        summary_shipping_orders=summary_shipping_orders,
        summary_done_orders=summary_done_orders,
        summary_month_sales=summary_month_sales,
        status_options=[
            "배송준비중",
            "배송중",
            "배송완료"
        ]
    )

@admin_bp.route("/order/<int:order_id>")
def order_detail(order_id):

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    # 주문 정보
    cur.execute("""
    SELECT *
    FROM orders
    WHERE id=?
    """, (order_id,))

    order = cur.fetchone()

    if order is None:
        conn.close()
        return redirect("/admin/orders")

    # 주문 상품
    cur.execute("""
    SELECT *
    FROM order_items
    WHERE order_id=?
    """, (order_id,))

    items = cur.fetchall()

    conn.close()

    return render_template(
        "admin/order_detail.html",
        order=order,
        items=items
    )

@admin_bp.route("/order/<int:order_id>/status", methods=["POST"])
def update_order_status(order_id):

    status = request.form.get("status")

    allowed_statuses = [
        "배송준비중",
        "배송중",
        "배송완료"
    ]

    if status not in allowed_statuses:
        return redirect(f"/admin/order/{order_id}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    UPDATE orders
    SET status=?
    WHERE id=?
    """, (status, order_id))

    conn.commit()
    conn.close()

    return redirect(f"/admin/order/{order_id}")

@admin_bp.route("/edit/<int:product_id>")
def edit_product(product_id):
    db = get_db()

    latest_rate = get_latest_gold_rate(db)

    product = db.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        return redirect("/admin")

    material_prices = db.execute("""
        SELECT *
        FROM product_material_prices
        WHERE product_id = ?
        ORDER BY sort_order ASC, id ASC
    """, (product_id,)).fetchall()

    material_price_map = {}

    for item in material_prices:
        material_price_map[item["material"]] = item

    price_base = material_price_map.get("14K")

    return render_template(
        "admin/edit_product.html",
        product=product,
        latest_rate=latest_rate,
        material_price_map=material_price_map,
        price_base=price_base
    )


@admin_bp.route("/edit-product/<int:product_id>")
def old_edit_product_url(product_id):
    return redirect(f"/admin/edit/{product_id}")


@admin_bp.route("/update-product/<int:product_id>", methods=["POST"])
def update_product(product_id):
    db = get_db()

    latest_rate = get_latest_gold_rate(db)

    product = db.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        return redirect("/admin")

    material_prices = db.execute("""
        SELECT *
        FROM product_material_prices
        WHERE product_id = ?
        ORDER BY sort_order ASC, id ASC
    """, (product_id,)).fetchall()

    material_price_map = {}

    for item in material_prices:
        material_price_map[item["material"]] = item

    price_base = material_price_map.get("14K")

    def render_edit_with_error(message):
        return render_template(
            "admin/edit_product.html",
            product=product,
            latest_rate=latest_rate,
            material_price_map=material_price_map,
            price_base=price_base,
            error=message
        )

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    collection = request.form.get("collection", "").strip().upper()
    sub_category = request.form.get("sub_category", "").strip().upper()
    tag = request.form.get("tag", "").strip().upper()
    material = request.form.get("material", "").strip().upper()

    image = request.files.get("image")
    new_banner_image = request.files.get("new_banner_image")
    new_between_media = request.files.get("new_between_media")

    season_banner_image = request.files.get("season_banner_image")
    season_between_media = request.files.get("season_between_media")

    if not name:
        return render_edit_with_error("상품명을 입력해 주세요.")

    if not collection:
        return render_edit_with_error("컬렉션을 선택해 주세요.")

    representative_price = get_representative_product_price(db, request.form)

    if representative_price <= 0:
        return render_edit_with_error(
            "14K 금중량, 총 공임, 해리율, 배수, 할인율을 입력해 주세요."
        )

    try:
        filename = save_product_image(image)

        new_banner_filename = save_product_image(new_banner_image)
        new_between_filename, new_between_media_type = save_new_between_media(new_between_media)

        season_banner_filename = save_product_image(season_banner_image)
        season_between_filename, season_between_media_type = save_season_between_media(season_between_media)

    except ValueError as e:
        return render_edit_with_error(str(e))

    update_fields = [
        "name = ?",
        "price = ?",
        "description = ?",
        "collection = ?",
        "sub_category = ?",
        "tag = ?",
        "material = ?"
    ]

    params = [
        name,
        representative_price,
        description,
        collection,
        sub_category,
        tag,
        material
    ]

    if filename:
        update_fields.append("image = ?")
        params.append(filename)

    if new_banner_filename:
        update_fields.append("new_banner_image = ?")
        params.append(new_banner_filename)

    if new_between_filename:
        update_fields.append("new_between_media = ?")
        update_fields.append("new_between_media_type = ?")
        params.append(new_between_filename)
        params.append(new_between_media_type)

    if season_banner_filename:
        update_fields.append("season_banner_image = ?")
        params.append(season_banner_filename)

    if season_between_filename:
        update_fields.append("season_between_media = ?")
        update_fields.append("season_between_media_type = ?")
        params.append(season_between_filename)
        params.append(season_between_media_type)

    params.append(product_id)

    query = f"""
        UPDATE products
        SET {", ".join(update_fields)}
        WHERE id = ?
    """

    db.execute(query, params)

    save_product_material_prices(db, product_id, request.form)

    db.commit()

    return redirect("/admin")

HOME_MEDIA_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "mp4", "webm", "mov"}

def allowed_home_media(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in HOME_MEDIA_ALLOWED_EXTENSIONS


def save_home_media_file(file):
    if not file or file.filename == "":
        return None

    if not allowed_home_media(file.filename):
        return None

    ext = file.filename.rsplit(".", 1)[1].lower()
    new_filename = f"{uuid.uuid4().hex}.{ext}"

    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, new_filename)
    file.save(file_path)

    return new_filename

def ensure_home_media_slots(db):
    db.execute("""
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

        # 홈 / 메뉴 공통 카테고리 이미지
        ("home_category_all", "카테고리 이미지 - ALL", "image", 40),
        ("home_category_ring", "카테고리 이미지 - RING", "image", 41),
        ("home_category_necklace", "카테고리 이미지 - NECKLACE", "image", 42),
        ("home_category_earrings", "카테고리 이미지 - EARRINGS", "image", 43),
        ("home_category_bracelet", "카테고리 이미지 - BRACELET", "image", 44),
        ("home_category_anklet", "카테고리 이미지 - ANKLET", "image", 45),

        # 메뉴 FEATURED 이미지
        ("menu_featured_new", "메뉴 FEATURED 이미지 - NEW", "image", 60),
        ("menu_featured_season", "메뉴 FEATURED 이미지 - SEASON", "image", 61),
        ("menu_featured_best", "메뉴 FEATURED 이미지 - BEST", "image", 62),

        # NEW / SEASON / BEST 페이지 히어로 이미지
        ("page_hero_new", "페이지 히어로 이미지 - NEW", "image", 63),
        ("page_hero_season", "페이지 히어로 이미지 - SEASON", "image", 64),
        ("page_hero_best", "페이지 히어로 이미지 - BEST", "image", 65),
        ("page_hero_shop", "페이지 히어로 이미지 - SHOP", "image", 66),
        ("page_hero_shop_ring", "페이지 히어로 이미지 - SHOP / RING", "image", 67),
        ("page_hero_shop_necklace", "페이지 히어로 이미지 - SHOP / NECKLACE", "image", 68),
        ("page_hero_shop_earrings", "페이지 히어로 이미지 - SHOP / EARRINGS", "image", 69),
        ("page_hero_shop_bracelet", "페이지 히어로 이미지 - SHOP / BRACELET", "image", 70),
        ("page_hero_shop_anklet", "페이지 히어로 이미지 - SHOP / ANKLET", "image", 71),

        # 메뉴 METAL 이미지
        ("menu_metal_diamond", "메뉴 METAL 이미지 - DIAMOND", "image", 72),
        ("menu_metal_goldbar", "메뉴 METAL 이미지 - GOLD BAR", "image", 73),
        ("menu_metal_24k", "메뉴 METAL 이미지 - 24K", "image", 74),
        ("menu_metal_18k", "메뉴 METAL 이미지 - 18K", "image", 75),
        ("menu_metal_14k", "메뉴 METAL 이미지 - 14K", "image", 76),
        ("menu_metal_silver", "메뉴 METAL 이미지 - SILVER", "image", 77),

        # 메뉴 GIFT 이미지
        ("menu_gift_men", "메뉴 GIFT 이미지 - 남", "image", 81),
        ("menu_gift_women", "메뉴 GIFT 이미지 - 여", "image", 82),
        ("menu_gift_kids_baby", "메뉴 GIFT 이미지 - 키즈/베이비", "image", 83),
        ("menu_gift_parents_teacher", "메뉴 GIFT 이미지 - 부모/스승", "image", 84),
        ("menu_gift_dog", "메뉴 GIFT 이미지 - 반려견", "image", 85),
        ("menu_gift_group", "메뉴 GIFT 이미지 - 모임", "image", 86),
        ("menu_gift_memorial", "메뉴 GIFT 이미지 - 추모", "image", 87),
        ("menu_gift_celebration", "메뉴 GIFT 이미지 - 축하", "image", 88),
    ]

    for slot_key, slot_name, media_type, sort_order in slots:
        db.execute("""
            INSERT OR IGNORE INTO home_media
            (slot_key, slot_name, media_type, sort_order)
            VALUES (?, ?, ?, ?)
        """, (slot_key, slot_name, media_type, sort_order))

    db.commit()


@admin_bp.route("/home-media")
def admin_home_media():
    db = get_db()

    ensure_home_media_slots(db)

    media_slots = db.execute("""
        SELECT *
        FROM home_media
        ORDER BY sort_order ASC, id ASC
    """).fetchall()

    return render_template("admin/home_media.html", media_slots=media_slots)


@admin_bp.route("/home-media/update/<int:media_id>", methods=["POST"])
def update_home_media(media_id):
    db = get_db()

    current_media = db.execute("""
        SELECT *
        FROM home_media
        WHERE id = ?
    """, (media_id,)).fetchone()

    if not current_media:
        flash("해당 홈 이미지 칸을 찾을 수 없습니다.")
        return redirect(url_for("admin.admin_home_media"))

    media_type = request.form.get("media_type", "image")
    is_active = 1 if request.form.get("is_active") == "on" else 0

    file = request.files.get("media_file")
    new_filename = save_home_media_file(file)

    if new_filename:
        db.execute("""
            UPDATE home_media
            SET filename = ?,
                media_type = ?,
                is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            new_filename,
            media_type,
            is_active,
            media_id
        ))
    else:
        db.execute("""
            UPDATE home_media
            SET media_type = ?,
                is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            media_type,
            is_active,
            media_id
        ))

    db.commit()

    flash("홈 이미지가 수정되었습니다.")
    return redirect(f"{url_for('admin.admin_home_media')}#media-{media_id}")