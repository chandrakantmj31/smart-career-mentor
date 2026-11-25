import hashlib
import secrets
from datetime import datetime, timezone
from functools import wraps

import jwt
from bson import ObjectId
from flask import current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import get_db


def hash_password(pw: str) -> str:
    return generate_password_hash(pw, method="scrypt")


def verify_password(pw_hash: str, pw: str) -> bool:
    return check_password_hash(pw_hash, pw)


def make_token(user_id: str, remember: bool = False) -> str:
    cfg = current_app.config
    exp = datetime.now(timezone.utc) + (cfg["JWT_REMEMBER_EXPIRES"] if remember else cfg["JWT_EXPIRES"])
    return jwt.encode({"sub": user_id, "exp": exp}, cfg["JWT_SECRET_KEY"], algorithm="HS256")


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def set_auth_cookies(resp, user_id: str, remember: bool = False):
    cfg = current_app.config
    max_age = int((cfg["JWT_REMEMBER_EXPIRES"] if remember else cfg["JWT_EXPIRES"]).total_seconds())
    resp.set_cookie(cfg["COOKIE_NAME"], make_token(user_id, remember), max_age=max_age,
                    httponly=True, secure=cfg["COOKIE_SECURE"], samesite="Lax", path="/")
    # Readable by JS on purpose: double-submit CSRF token.
    resp.set_cookie(cfg["CSRF_COOKIE_NAME"], secrets.token_urlsafe(24), max_age=max_age,
                    httponly=False, secure=cfg["COOKIE_SECURE"], samesite="Lax", path="/")
    return resp


def clear_auth_cookies(resp):
    cfg = current_app.config
    resp.delete_cookie(cfg["COOKIE_NAME"], path="/")
    resp.delete_cookie(cfg["CSRF_COOKIE_NAME"], path="/")
    return resp


def _csrf_ok() -> bool:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    cookie = request.cookies.get(current_app.config["CSRF_COOKIE_NAME"])
    header = request.headers.get("X-CSRF-Token")
    return bool(cookie) and bool(header) and secrets.compare_digest(cookie, header)


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        token = request.cookies.get(current_app.config["COOKIE_NAME"])
        if not token:
            return jsonify(error="Authentication required"), 401
        try:
            data = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
            user = get_db().users.find_one({"_id": ObjectId(data["sub"])})
        except Exception:
            return jsonify(error="Session expired. Please sign in again."), 401
        if not user:
            return jsonify(error="Account not found"), 401
        if not _csrf_ok():
            return jsonify(error="CSRF validation failed"), 403
        g.user = user
        return fn(*a, **kw)
    return wrapper
