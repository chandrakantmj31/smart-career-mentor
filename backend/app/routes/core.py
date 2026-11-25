"""Profile, assessment, careers, skills, roadmap, dashboard and resources endpoints."""
from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, g, jsonify, request

from ..data.careers_data import CAREERS, RESOURCES
from ..extensions import get_db
from ..services import career_engine, roadmap_service, skill_service
from ..utils.security import login_required
from ..utils.validators import clean_list, clean_str

bp = Blueprint("core", __name__, url_prefix="/api")
now = lambda: datetime.now(timezone.utc)  # noqa: E731


def _uid():
    return g.user["_id"]


def _assessment():
    return get_db().assessments.find_one({"user_id": _uid()})


def _skills_input(raw):
    out = []
    for item in (raw if isinstance(raw, list) else [])[:60]:
        if isinstance(item, dict):
            name, lvl = clean_str(item.get("name"), 40), clean_str(item.get("level"), 20).lower()
        else:
            name, lvl = clean_str(item, 40), "intermediate"
        if name:
            out.append({"name": name, "level": lvl if lvl in ("beginner", "intermediate", "advanced") else "intermediate"})
    return out


def _iso(d):
    return d.isoformat() if d else None


# ---------- profile ----------
@bp.get("/users/profile")
@login_required
def get_profile():
    u = g.user
    return jsonify(profile={"full_name": u.get("full_name"), "email": u["email"], "created_at": _iso(u.get("created_at")),
                            **{k: u.get("profile", {}).get(k, "") for k in ("headline", "location", "github", "linkedin", "bio")}})


@bp.put("/users/profile")
@login_required
def update_profile():
    d = request.get_json(silent=True) or {}
    upd = {f"profile.{k}": clean_str(d.get(k), 300) for k in ("headline", "location", "github", "linkedin", "bio") if k in d}
    if "full_name" in d:
        name = clean_str(d["full_name"], 100)
        if len(name) < 2:
            return jsonify(error="Name is too short."), 400
        upd["full_name"] = name
    if upd:
        get_db().users.update_one({"_id": _uid()}, {"$set": upd})
    return get_profile()


# ---------- assessment ----------
@bp.post("/assessment")
@login_required
def save_assessment():
    d = request.get_json(silent=True) or {}
    doc = {
        "user_id": _uid(), "name": clean_str(d.get("name"), 100) or g.user.get("full_name", ""),
        "education": clean_str(d.get("education"), 150), "degree": clean_str(d.get("degree"), 100),
        "specialization": clean_str(d.get("specialization"), 100),
        "skills": _skills_input(d.get("skills")), "languages": _skills_input(d.get("languages")),
        "interests": clean_list(d.get("interests")), "strengths": clean_list(d.get("strengths")),
        "weaknesses": clean_list(d.get("weaknesses")), "projects": clean_list(d.get("projects"), 200),
        "experience": clean_str(d.get("experience"), 1000), "preferred_roles": clean_list(d.get("preferred_roles")),
        "career_goals": clean_str(d.get("career_goals"), 500), "updated_at": now(),
    }
    if not doc["skills"] and not doc["languages"]:
        return jsonify(error="Please add at least one skill or programming language."), 400
    db = get_db()
    db.assessments.update_one({"user_id": _uid()}, {"$set": doc, "$setOnInsert": {"created_at": now()}}, upsert=True)
    result = career_engine.recommend(doc)
    db.career_recommendations.update_one(
        {"user_id": _uid()}, {"$set": {"user_id": _uid(), "recommendations": result["recommendations"], "method": result["method"],
                                       "generated_at": now()}}, upsert=True)
    db.assessments.update_one({"user_id": _uid()}, {"$set": {"results": {"top": result["recommendations"][0]["career"],
                                                                         "top_match": result["recommendations"][0]["match"]}}})
    return jsonify(message="Assessment saved.", **result), 201


def _public_assessment(a):
    if not a:
        return None
    return {k: v for k, v in a.items() if k not in ("_id", "user_id")} | {"updated_at": _iso(a.get("updated_at")), "created_at": _iso(a.get("created_at"))}


@bp.get("/assessment")
@login_required
def get_assessment():
    return jsonify(assessment=_public_assessment(_assessment()))


@bp.get("/assessment/results")
@login_required
def assessment_results():
    a = _assessment()
    if not a:
        return jsonify(error="Complete the assessment first."), 404
    return jsonify(results=a.get("results"), **career_engine.recommend(a))


# ---------- careers ----------
@bp.get("/careers/recommendations")
@login_required
def career_recs():
    rec = get_db().career_recommendations.find_one({"user_id": _uid()})
    if not rec:
        return jsonify(recommendations=[], method=career_engine.METHOD, needs_assessment=True)
    return jsonify(recommendations=rec["recommendations"], method=rec["method"], generated_at=_iso(rec.get("generated_at")), needs_assessment=False)


@bp.get("/careers/available")
@login_required
def careers_available():
    return jsonify(careers=[{"id": c["id"], "title": c["title"], "tagline": c["tagline"]} for c in CAREERS])


# ---------- skills ----------
def _target_career(a):
    cid = request.args.get("career_id")
    if cid:
        return cid
    rm = get_db().roadmaps.find_one({"user_id": _uid()})
    if rm:
        return rm["career_id"]
    rec = get_db().career_recommendations.find_one({"user_id": _uid()})
    return rec["recommendations"][0]["career_id"] if rec and rec["recommendations"] else None


@bp.get("/skills/gap-analysis")
@login_required
def gap():
    a = _assessment()
    if not a:
        return jsonify(error="Complete the assessment first.", needs_assessment=True), 404
    res = skill_service.gap_analysis(a, _target_career(a))
    if not res:
        return jsonify(error="Unknown career."), 404
    return jsonify(res)


@bp.put("/skills/progress")
@login_required
def skill_progress():
    d = request.get_json(silent=True) or {}
    name, level = career_engine.canon_skill(clean_str(d.get("skill"), 40)), clean_str(d.get("level"), 20).lower()
    if not name or level not in ("beginner", "intermediate", "advanced"):
        return jsonify(error="Provide a skill and a level (beginner, intermediate, advanced)."), 400
    a = _assessment()
    if not a:
        return jsonify(error="Complete the assessment first."), 404
    skills = [s for s in a.get("skills", []) if career_engine.canon_skill(s["name"]) != name]
    skills.append({"name": name, "level": level})
    get_db().assessments.update_one({"user_id": _uid()}, {"$set": {"skills": skills, "updated_at": now()}})
    a["skills"] = skills
    result = career_engine.recommend(a)
    get_db().career_recommendations.update_one({"user_id": _uid()}, {"$set": {"recommendations": result["recommendations"], "generated_at": now()}})
    return jsonify(message="Skill updated.", skill=name, level=level)


# ---------- roadmap ----------
def _public_roadmap(r):
    return {"career_id": r["career_id"], "career": r["career"], "stages": r["stages"], "total_weeks": r["total_weeks"],
            "progress": roadmap_service.progress(r), "generated_at": _iso(r.get("generated_at"))}


@bp.post("/roadmap/generate")
@login_required
def roadmap_generate():
    a = _assessment()
    if not a:
        return jsonify(error="Complete the assessment first."), 404
    cid = clean_str((request.get_json(silent=True) or {}).get("career_id"), 60) or _target_career(a)
    rm = roadmap_service.generate(a, cid)
    if not rm:
        return jsonify(error="Unknown career."), 404
    get_db().roadmaps.update_one({"user_id": _uid()}, {"$set": {**rm, "user_id": _uid()}}, upsert=True)
    return jsonify(roadmap=_public_roadmap(rm)), 201


@bp.get("/roadmap")
@login_required
def roadmap_get():
    r = get_db().roadmaps.find_one({"user_id": _uid()})
    return jsonify(roadmap=_public_roadmap(r) if r else None)


@bp.put("/roadmap/progress")
@login_required
def roadmap_progress():
    d = request.get_json(silent=True) or {}
    task_id, done = clean_str(d.get("task_id"), 40), d.get("done")
    if not task_id or not isinstance(done, bool):
        return jsonify(error="Provide task_id and done (true/false)."), 400
    r = get_db().roadmaps.find_one({"user_id": _uid()})  # ownership: only ever the caller's roadmap
    if not r:
        return jsonify(error="No roadmap yet."), 404
    found = False
    for s in r["stages"]:
        for t in s["tasks"]:
            if t["id"] == task_id:
                t["done"], t["completed_at"] = done, (now() if done else None)
                found = True
    if not found:
        return jsonify(error="Task not found."), 404
    get_db().roadmaps.update_one({"_id": r["_id"], "user_id": _uid()}, {"$set": {"stages": r["stages"]}})
    return jsonify(progress=roadmap_service.progress(r))


# ---------- resources ----------
@bp.get("/resources")
@login_required
def resources():
    skill = career_engine.canon_skill(clean_str(request.args.get("skill"), 40))
    items = [{"skill": s, "title": t, "url": u} for s, (t, u) in RESOURCES.items() if not skill or s == skill]
    return jsonify(resources=items)


# ---------- dashboard ----------
def _readiness(a, top, rm_pct, resume_score):
    """Career readiness = 50% skill coverage of best-fit career, 30% roadmap progress, 20% resume score."""
    skill_cov = top["breakdown"]["skills"] if top else 0
    return round(0.5 * skill_cov + 0.3 * rm_pct + 0.2 * (resume_score or 0))


@bp.get("/dashboard")
@login_required
def dashboard():
    db, uid = get_db(), _uid()
    a = _assessment()
    rec = db.career_recommendations.find_one({"user_id": uid})
    recs = rec["recommendations"] if rec else []
    top = recs[0] if recs else None
    last_resume = db.resumes.find_one({"user_id": uid}, sort=[("uploaded_at", -1)])
    rm = db.roadmaps.find_one({"user_id": uid})
    prog = roadmap_service.progress(rm) if rm else {"done": 0, "total": 0, "pct": 0}
    gap_res = skill_service.gap_analysis(a, rm["career_id"] if rm else (top["career_id"] if top else None)) if a and (rm or top) else None
    resume_score = last_resume["analysis"]["overall_score"] if last_resume else None

    actions = []
    if not a:
        actions.append({"title": "Complete your career assessment", "detail": "Tell us your skills and goals to unlock recommendations.", "href": "assessment.html"})
    if not last_resume:
        actions.append({"title": "Upload your resume", "detail": "Get an explainable ATS-style score and fixes.", "href": "resume-analyzer.html"})
    if a and not rm:
        actions.append({"title": "Generate your learning roadmap", "detail": "A 4-stage plan toward your best-fit career.", "href": "roadmap.html"})
    if rm:
        nxt = next((t for s in rm["stages"] for t in s["tasks"] if not t["done"]), None)
        if nxt:
            actions.append({"title": nxt["title"], "detail": "Next task on your roadmap.", "href": "roadmap.html"})
    if last_resume and last_resume["analysis"].get("suggestions"):
        actions.append({"title": "Improve your resume", "detail": last_resume["analysis"]["suggestions"][0], "href": "resume-analyzer.html"})

    return jsonify(
        user={"full_name": g.user.get("full_name"), "email": g.user["email"]}, has_assessment=bool(a),
        readiness_score=_readiness(a, top, prog["pct"], resume_score) if a else None,
        resume_score=resume_score,
        skills={"have": gap_res["existing_count"], "required": gap_res["total_required"]} if gap_res else None,
        top_career={"career": top["career"], "match": top["match"]} if top else None,
        recommendations=[{"career": r["career"], "match": r["match"], "career_id": r["career_id"]} for r in recs[:3]],
        recent_resume={"id": str(last_resume["_id"]), "filename": last_resume["filename"], "score": resume_score,
                       "uploaded_at": _iso(last_resume["uploaded_at"]), "suggestions": last_resume["analysis"].get("suggestions", [])[:2]} if last_resume else None,
        skill_gaps=[{"skill": s["skill"], "current_pct": s["current_pct"], "required_pct": s["required_pct"]} for s in (gap_res["skills"] if gap_res else []) if s["gap"] > 0][:4],
        roadmap={"career": rm["career"], **prog} if rm else None,
        next_actions=actions[:4],
        readiness_method="Readiness = 50% skill coverage of your top career + 30% roadmap progress + 20% latest resume score.",
    )
