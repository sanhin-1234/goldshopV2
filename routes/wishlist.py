from flask import Blueprint, session, jsonify, render_template, redirect
from models.db import get_db

wishlist_bp = Blueprint("wishlist", __name__)


@wishlist_bp.route("/wishlist")
def wishlist_page():
    if not session.get("username"):
        return redirect("/login")

    username = session.get("username")
    db = get_db()

    products = db.execute(
        """
        SELECT p.*
        FROM wishlists w
        JOIN products p ON w.product_id = p.id
        WHERE w.username = ?
        ORDER BY w.created_at DESC
        """,
        (username,)
    ).fetchall()

    wished_product_ids = [p["id"] for p in products]

    return render_template(
        "shop/wishlist.html",
        products=products,
        wished_product_ids=wished_product_ids
    )


@wishlist_bp.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
def toggle_wishlist(product_id):
    if not session.get("username"):
        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    username = session.get("username")
    db = get_db()

    existing = db.execute(
        """
        SELECT id
        FROM wishlists
        WHERE username = ? AND product_id = ?
        """,
        (username, product_id)
    ).fetchone()

    if existing:
        db.execute(
            """
            DELETE FROM wishlists
            WHERE username = ? AND product_id = ?
            """,
            (username, product_id)
        )
        db.commit()

        return jsonify({
            "success": True,
            "wished": False
        })

    db.execute(
        """
        INSERT INTO wishlists (username, product_id)
        VALUES (?, ?)
        """,
        (username, product_id)
    )
    db.commit()

    return jsonify({
        "success": True,
        "wished": True
    })