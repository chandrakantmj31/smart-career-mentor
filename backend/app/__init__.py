import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from .config import Config, TestConfig
from .extensions import init_db, limiter

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def create_app(testing=False):
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    app = Flask(__name__, static_folder=None)
    app.config.from_object(TestConfig if testing else Config)
    if not testing and os.getenv("FLASK_ENV") == "production":
        for var in ("FLASK_SECRET_KEY", "JWT_SECRET_KEY", "MONGODB_URI"):
            if not os.getenv(var):
                raise RuntimeError(f"Missing required environment variable: {var}")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    init_db(app)
    limiter.init_app(app)
    # Frontend is served by this same app, so CORS is only needed for an explicitly configured separate origin.
    CORS(app, resources={r"/api/*": {"origins": [app.config["FRONTEND_URL"]]}}, supports_credentials=True)

    from .routes import auth, core, resume
    for bp in (auth.bp, core.bp, resume.bp):
        app.register_blueprint(bp)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.after_request
    def headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if app.config.get("COOKIE_SECURE"):
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if resp.mimetype == "application/json":
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(HTTPException)
    def http_err(e):
        return jsonify(error=e.description if e.code != 413 else "File is too large (max 5 MB)."), e.code

    @app.errorhandler(Exception)
    def any_err(e):
        app.logger.exception("Unhandled error")  # details go to logs only, never to the client
        return jsonify(error="Something went wrong on our side. Please try again."), 500

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "login.html")

    @app.get("/<path:path>")
    def static_files(path):
        if path.startswith("api/"):
            return jsonify(error="Not found"), 404
        return send_from_directory(FRONTEND_DIR, path)

    return app
