import certifi
import ssl
from flask import current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient, ASCENDING

limiter = Limiter(key_func=get_remote_address, default_limits=["300 per hour"])
_client = None


def _make_ssl_context():
    """TLS 1.2 context for MongoDB Atlas compatibility on Python 3.14."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def init_db(app):
    """Create the Mongo client (mongomock in tests) and indexes."""
    global _client
    if app.config.get("TESTING"):
        import mongomock
        _client = mongomock.MongoClient()
    else:
        uri = app.config["MONGODB_URI"]
        if not uri:
            raise RuntimeError("MONGODB_URI is not set. See backend/.env.example")
        _client = MongoClient(
            uri,
            serverSelectionTimeoutMS=15000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000,
            tz_aware=True,
            tls=True,
            tlsCAFile=certifi.where(),
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            ssl_context=_make_ssl_context(),
            retryWrites=True,
            retryReads=True,
        )
    db = _client[app.config["DATABASE_NAME"]]
    db.users.create_index([("email", ASCENDING)], unique=True)
    for name in ("assessments", "career_recommendations", "roadmaps", "job_recommendations"):
        db[name].create_index([("user_id", ASCENDING)])
    db.resumes.create_index([("user_id", ASCENDING), ("uploaded_at", ASCENDING)])
    db.learning_resources.create_index([("related_career", ASCENDING)])
    db.password_resets.create_index([("token_hash", ASCENDING)])
    return db


def get_db():
    return _client[current_app.config["DATABASE_NAME"]]
