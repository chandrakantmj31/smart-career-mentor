import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, g, jsonify, request
from werkzeug.utils import secure_filename

from ..extensions import get_db, limiter
from ..services import resume_analyzer as ra
from ..utils.security import login_required
from ..utils.validators import clean_str

bp = Blueprint("resume", __name__, url_prefix="/api/resume")
log = logging.getLogger(__name__)
MAX_PER_DAY = 15


def _public(r, full=True):
    out = {"id": str(r["_id"]), "filename": r["filename"], "uploaded_at": r["uploaded_at"].isoformat(),
           "size_bytes": r["size_bytes"], "overall_score": r["analysis"]["overall_score"]}
    if full:
        out["analysis"] = r["analysis"]
    return out


@bp.post("/upload")
@login_required
@limiter.limit("20 per hour")
def upload():
    """Upload AND analyze in one step; the file is processed on this server only."""
    f = request.files.get("resume")
    if not f or not f.filename:
        return jsonify(error="Choose a PDF or DOCX file to upload."), 400
    data = f.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        return jsonify(error="File is too large (max 5 MB)."), 413
    db = get_db()
    since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if db.resumes.count_documents({"user_id": g.user["_id"], "uploaded_at": {"$gte": since}}) >= MAX_PER_DAY:
        return jsonify(error="Daily upload limit reached. Try again tomorrow."), 429
    name = secure_filename(f.filename) or "resume"
    try:
        kind = ra.detect_type(name, data[:4])
        text = ra.extract_text(data, kind)
    except ra.ResumeError as e:
        return jsonify(error=str(e)), 400
    target = clean_str(request.form.get("career_id"), 60) or None
    analysis = ra.analyze(text, target)
    doc = {"user_id": g.user["_id"], "filename": name, "file_type": kind, "size_bytes": len(data),
           # Only extracted text is stored (private, never served publicly). The raw file is not kept.
           "extracted_text": text[:20000], "analysis": analysis, "uploaded_at": datetime.now(timezone.utc)}
    doc["_id"] = db.resumes.insert_one(doc).inserted_id
    return jsonify(resume=_public(doc)), 201


@bp.post("/analyze")
@login_required
@limiter.limit("30 per hour")
def reanalyze():
    """Re-run analysis for a stored resume against a different target career."""
    d = request.get_json(silent=True) or {}
    r = _owned(d.get("resume_id"))
    if r is None:
        return jsonify(error="Resume not found."), 404
    analysis = ra.analyze(r["extracted_text"], clean_str(d.get("career_id"), 60) or None)
    get_db().resumes.update_one({"_id": r["_id"], "user_id": g.user["_id"]}, {"$set": {"analysis": analysis}})
    r["analysis"] = analysis
    return jsonify(resume=_public(r))


def _owned(rid):
    try:
        oid = ObjectId(rid)
    except (InvalidId, TypeError):
        return None
    return get_db().resumes.find_one({"_id": oid, "user_id": g.user["_id"]})  # ownership enforced in the query


@bp.get("/history")
@login_required
def history():
    rows = get_db().resumes.find({"user_id": g.user["_id"]}, sort=[("uploaded_at", -1)], limit=20)
    return jsonify(resumes=[_public(r, full=False) for r in rows])


@bp.get("/<resume_id>")
@login_required
def one(resume_id):
    r = _owned(resume_id)
    return (jsonify(resume=_public(r)) if r else (jsonify(error="Resume not found."), 404))
