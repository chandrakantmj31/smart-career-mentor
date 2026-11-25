import logging
import secrets
from datetime import datetime, timedelta, timezone

from urllib.parse import urlencode

from flask import Blueprint, current_app, g, jsonify, redirect, request

from ..extensions import get_db, limiter
from ..services import google_service
from ..utils.security import (clear_auth_cookies, hash_password, login_required, set_auth_cookies, sha256,
                              verify_password)
from ..utils.validators import clean_email, clean_str, password_problem

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
log = logging.getLogger(__name__)


def public_user(u):
    return {"id": str(u["_id"]), "full_name": u.get("full_name", ""), "email": u["email"],
            "created_at": u.get("created_at").isoformat() if u.get("created_at") else None,
            "profile": u.get("profile", {})}


@bp.post("/register")
@limiter.limit("10 per hour")
def register():
    d = request.get_json(silent=True) or {}
    name, email = clean_str(d.get("full_name"), 100), clean_email(d.get("email"))
    if len(name) < 2:
        return jsonify(error="Please enter your full name."), 400
    if not email:
        return jsonify(error="Please enter a valid email address."), 400
    problem = password_problem(d.get("password"))
    if problem:
        return jsonify(error=problem), 400
    db = get_db()
    if db.users.find_one({"email": email}):
        return jsonify(error="An account with this email already exists."), 409
    doc = {"full_name": name, "email": email, "password_hash": hash_password(d["password"]),
           "created_at": datetime.now(timezone.utc), "profile": {}}
    uid = db.users.insert_one(doc).inserted_id
    doc["_id"] = uid
    resp = jsonify(user=public_user(doc))
    resp.status_code = 201
    return set_auth_cookies(resp, str(uid))


@bp.post("/login")
@limiter.limit("10 per minute")
def login():
    d = request.get_json(silent=True) or {}
    email = clean_email(d.get("email"))
    pw = d.get("password")
    user = get_db().users.find_one({"email": email}) if email and isinstance(pw, str) else None
    # Same message for unknown email and wrong password, so accounts can't be enumerated.
    if not user or not user.get("password_hash") or not verify_password(user["password_hash"], pw):
        return jsonify(error="Invalid email or password."), 401
    return set_auth_cookies(jsonify(user=public_user(user)), str(user["_id"]), bool(d.get("remember")))


@bp.post("/logout")
def logout():
    return clear_auth_cookies(jsonify(ok=True))


@bp.get("/me")
@login_required
def me():
    return jsonify(user=public_user(g.user))


@bp.post("/forgot-password")
@limiter.limit("5 per hour")
def forgot_password():
    email = clean_email((request.get_json(silent=True) or {}).get("email"))
    generic = {"message": "If that email is registered, a reset link has been sent."}
    user = get_db().users.find_one({"email": email}) if email else None
    if user:
        token = secrets.token_urlsafe(32)
        get_db().password_resets.insert_one({
            "user_id": user["_id"], "token_hash": sha256(token), "used": False,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)})
        link = f"{current_app.config['FRONTEND_URL']}/reset-password.html?token={token}"
        # No email provider is configured yet. In development the link is logged; in production it is not.
        if not current_app.config.get("COOKIE_SECURE"):
            log.warning("DEV ONLY password reset link for %s: %s", email, link)
            if current_app.config.get("TESTING"):
                generic["dev_token"] = token
    return jsonify(generic)


@bp.post("/reset-password")
@limiter.limit("10 per hour")
def reset_password():
    d = request.get_json(silent=True) or {}
    token, pw = d.get("token"), d.get("password")
    problem = password_problem(pw)
    if problem:
        return jsonify(error=problem), 400
    if not isinstance(token, str):
        return jsonify(error="Invalid or expired reset link."), 400
    db = get_db()
    rec = db.password_resets.find_one({"token_hash": sha256(token), "used": False})
    exp = rec["expires_at"] if rec else None
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if not rec or exp < datetime.now(timezone.utc):
        return jsonify(error="Invalid or expired reset link."), 400
    db.users.update_one({"_id": rec["user_id"]}, {"$set": {"password_hash": hash_password(pw)}})
    db.password_resets.update_one({"_id": rec["_id"]}, {"$set": {"used": True}})
    return jsonify(message="Password updated. You can sign in now.")


@bp.get("/google/config")
def google_config():
    return jsonify(enabled=google_service.is_configured(current_app.config))


@bp.get("/google/start")
def google_start():
    if not google_service.is_configured(current_app.config):
        return jsonify(error="Google sign-in is not configured on this server."), 503
    state = google_service.new_state()
    resp = redirect(google_service.authorize_url(current_app.config, state))
    resp.set_cookie("scm_oauth_state", state, max_age=600, httponly=True, samesite="Lax",
                    secure=current_app.config["COOKIE_SECURE"], path="/api/auth/google")
    return resp


@bp.get("/google/callback")
def google_callback():
    cfg = current_app.config
    back = lambda msg: redirect("/login.html?" + urlencode({"error": msg}))  # noqa: E731
    if not google_service.is_configured(cfg):
        return back("Google sign-in is not configured.")
    state, cookie = request.args.get("state", ""), request.cookies.get("scm_oauth_state", "")
    if request.args.get("error") or not request.args.get("code") or not cookie or not secrets.compare_digest(state, cookie):
        return back("Google sign-in was cancelled or could not be verified.")
    try:
        info = google_service.fetch_profile(cfg, request.args["code"])
    except Exception:
        log.exception("Google token exchange failed")
        return back("Could not complete Google sign-in. Please try again.")
    email = clean_email(info.get("email"))
    if not email or not info.get("email_verified"):
        return back("Your Google account's email is not verified.")
    db, new = get_db(), False
    user = db.users.find_one({"email": email})
    if not user:
        user = {"full_name": clean_str(info.get("name"), 100) or email.split("@")[0], "email": email, "google_id": info.get("sub"),
                "created_at": datetime.now(timezone.utc), "profile": {}}
        user["_id"] = db.users.insert_one(user).inserted_id
        new = True
    resp = redirect("/assessment.html" if new else "/dashboard.html")
    resp.delete_cookie("scm_oauth_state", path="/api/auth/google")
    return set_auth_cookies(resp, str(user["_id"]))
