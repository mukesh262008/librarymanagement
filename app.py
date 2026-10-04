from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from database import close_db, get_db, init_db
from inference_engine import evaluate_request
from services.auth_service import (
    account_exists,
    authenticate,
    create_account,
    csrf_token,
    current_staff,
    logout,
    safe_redirect_target,
    valid_csrf,
)
from services.catalogue_service import get_book, list_books
from services.circulation_service import (
    create_member,
    create_loan,
    get_dashboard_data,
    get_member_detail,
    list_active_loans,
    list_members,
    process_return,
    renew_loan,
)


def load_secret_key() -> str:
    configured = os.environ.get("LIBRARY_SECRET_KEY")
    if configured:
        return configured
    from database import DATABASE_PATH

    key_path = Path(DATABASE_PATH).parent / "session.key"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        key_path.write_text(secrets.token_hex(32), encoding="ascii")
    return key_path.read_text(encoding="ascii").strip()


app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config["SECRET_KEY"] = load_secret_key()
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.teardown_appcontext(close_db)

with app.app_context():
    init_db()


@app.context_processor
def inject_shell_context():
    return {"csrf_token": csrf_token, "staff_username": current_staff}


@app.before_request
def enforce_staff_sign_in():
    endpoint = request.endpoint
    if endpoint in {"login", "setup", "static"}:
        return None
    if not account_exists():
        return redirect(url_for("setup"))
    if not session.get("staff_username"):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Sign in is required."}), 401
        return redirect(url_for("login", next=request.path))
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not valid_csrf(token):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Refresh the page and try again."}), 400
            return "The form expired. Please go back, refresh and try again.", 400
    return None


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if account_exists():
        return redirect(url_for("login"))
    error = None
    if request.method == "POST":
        if not valid_csrf(request.form.get("csrf_token")):
            error = "Refresh this page and submit the form again."
        else:
            try:
                create_account(request.form.get("username", ""), request.form.get("password", ""))
            except ValueError as exc:
                error = str(exc)
            else:
                authenticate(request.form["username"], request.form["password"])
                return redirect(url_for("overview"))
    return render_template("setup.html", error=error), 400 if error else 200


@app.route("/login", methods=["GET", "POST"])
def login():
    if not account_exists():
        return redirect(url_for("setup"))
    if session.get("staff_username"):
        return redirect(url_for("overview"))
    error = None
    next_page = safe_redirect_target(request.values.get("next"))
    if request.method == "POST":
        if not valid_csrf(request.form.get("csrf_token")):
            error = "Refresh this page and try again."
        elif authenticate(request.form.get("username", ""), request.form.get("password", "")):
            return redirect(next_page)
        else:
            error = "Username or password is incorrect."
    return render_template("login.html", error=error, next_page=next_page), 401 if error else 200


@app.post("/logout")
def logout_route():
    logout()
    return redirect(url_for("login"))


@app.get("/")
def overview():
    return render_template("overview.html", active_page="overview")


@app.get("/members")
def members_page():
    return render_template("members.html", active_page="members")


@app.get("/members/<int:member_id>")
def member_detail_page(member_id: int):
    return render_template("member_detail.html", active_page="members", member_id=member_id)


@app.get("/catalogue")
def catalogue_page():
    return render_template("catalogue.html", active_page="catalogue")


@app.get("/circulation")
def circulation_page():
    return render_template("circulation.html", active_page="circulation")


@app.get("/policies")
def policies_page():
    return render_template("policies.html", active_page="policies")


@app.get("/api/dashboard")
def dashboard_api():
    return jsonify(get_dashboard_data())


@app.get("/api/members")
def members_api():
    return jsonify(list_members(
        search=request.args.get("q", ""),
        status=request.args.get("status", "all"),
    ))


@app.post("/api/members")
def create_member_api():
    payload = request.get_json(silent=True) or {}
    try:
        member = create_member(
            name=payload.get("name", ""),
            email=payload.get("email", ""),
            phone=payload.get("phone", ""),
            member_type=payload.get("member_type", ""),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except sqlite3.IntegrityError:
        return jsonify({"error": "A member with that email address already exists."}), 409
    return jsonify(member), 201


@app.get("/api/members/<int:member_id>")
def member_detail_api(member_id: int):
    member = get_member_detail(member_id)
    if member is None:
        return jsonify({"error": "Member not found."}), 404
    return jsonify(member)


@app.get("/api/books")
def books_api():
    return jsonify(list_books(
        search=request.args.get("q", ""),
        category=request.args.get("category", "all"),
        availability=request.args.get("availability", "all"),
    ))


@app.get("/api/books/<int:book_id>")
def book_detail_api(book_id: int):
    book = get_book(book_id)
    if book is None:
        return jsonify({"error": "Book not found."}), 404
    return jsonify(book)


@app.get("/api/policies")
def policies_api():
    rows = get_db().execute(
        "SELECT policy_key, title, description, value FROM policies "
        "WHERE active = 1 ORDER BY display_order"
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/circulation/active-loans")
def active_loans_api():
    return jsonify(list_active_loans())


@app.post("/api/circulation/check")
def check_circulation_api():
    payload = request.get_json(silent=True) or {}
    action = payload.get("action", "issue")
    member_id = payload.get("member_id")
    book_id = payload.get("book_id")
    loan_id = payload.get("loan_id")
    try:
        result = evaluate_request(action, member_id, book_id, loan_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Select a valid member and book or loan."}), 400
    if result.get("error"):
        return jsonify({"error": result["error"]}), 404
    return jsonify(result)


@app.post("/api/circulation/issue")
def issue_book_api():
    payload = request.get_json(silent=True) or {}
    try:
        result = create_loan(payload.get("member_id"), payload.get("book_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Select a valid member and book."}), 400
    if not result["approved"]:
        return jsonify(result), 409
    return jsonify(result), 201


@app.post("/api/circulation/return")
def return_book_api():
    payload = request.get_json(silent=True) or {}
    try:
        result = process_return(payload.get("loan_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Select a valid loan."}), 400
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result)


@app.post("/api/circulation/renew")
def renew_book_api():
    payload = request.get_json(silent=True) or {}
    try:
        result = renew_loan(payload.get("loan_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Select a valid loan."}), 400
    if result.get("error"):
        return jsonify(result), 404
    if not result["approved"]:
        return jsonify(result), 409
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
