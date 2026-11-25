import io

from conftest import ASSESSMENT, Api, make_docx, make_pdf, register
from app import create_app


# ---------- auth ----------
def test_register_and_me(api):
    r = register(api)
    assert r.status_code == 201
    assert "password" not in r.get_data(as_text=True).lower().replace("password_hash", "")
    me = api.get("/api/auth/me")
    assert me.status_code == 200 and me.json["user"]["email"] == "chandra@example.com"


def test_register_validation(api):
    assert register(api, email="bad").status_code == 400
    assert register(api, pw="short").status_code == 400
    assert register(api, pw="onlyletters").status_code == 400
    assert register(api).status_code == 201
    assert register(api).status_code == 409  # duplicate email


def test_password_is_hashed(app, api):
    register(api)
    from app.extensions import get_db
    with app.app_context():
        u = get_db().users.find_one({"email": "chandra@example.com"})
    assert u["password_hash"] != "Passw0rdOK" and u["password_hash"].startswith("scrypt")


def test_login_success_and_invalid_credentials(client, api):
    register(api)
    api.post("/api/auth/logout")
    assert api.get("/api/auth/me").status_code == 401
    bad = api.post("/api/auth/login", json={"email": "chandra@example.com", "password": "WrongPass1"})
    assert bad.status_code == 401
    unknown = api.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Passw0rdOK"})
    assert unknown.status_code == 401 and unknown.json["error"] == bad.json["error"]
    ok = api.post("/api/auth/login", json={"email": "chandra@example.com", "password": "Passw0rdOK"})
    assert ok.status_code == 200 and api.get("/api/auth/me").status_code == 200


def test_nosql_injection_rejected(api):
    register(api)
    api.post("/api/auth/logout")
    r = api.post("/api/auth/login", json={"email": {"$ne": ""}, "password": {"$ne": ""}})
    assert r.status_code == 401


def test_protected_routes_require_auth(client):
    for url in ("/api/dashboard", "/api/assessment", "/api/careers/recommendations", "/api/resume/history",
                "/api/roadmap", "/api/skills/gap-analysis", "/api/users/profile"):
        assert client.get(url).status_code == 401, url


def test_csrf_required_for_writes(client, api):
    register(api)
    r = client.post("/api/assessment", json=ASSESSMENT)  # no CSRF header
    assert r.status_code == 403


def test_forgot_and_reset_password(api):
    register(api)
    api.post("/api/auth/logout")
    unknown = api.post("/api/auth/forgot-password", json={"email": "ghost@example.com"})
    known = api.post("/api/auth/forgot-password", json={"email": "chandra@example.com"})
    assert unknown.status_code == known.status_code == 200
    assert unknown.json["message"] == known.json["message"]
    token = known.json["dev_token"]
    assert api.post("/api/auth/reset-password", json={"token": "nope", "password": "NewPassw0rd"}).status_code == 400
    assert api.post("/api/auth/reset-password", json={"token": token, "password": "NewPassw0rd"}).status_code == 200
    assert api.post("/api/auth/reset-password", json={"token": token, "password": "Another1234"}).status_code == 400  # single use
    assert api.post("/api/auth/login", json={"email": "chandra@example.com", "password": "NewPassw0rd"}).status_code == 200


# ---------- profile / assessment / careers ----------
def test_profile_get_and_update(api):
    register(api)
    assert api.get("/api/users/profile").json["profile"]["full_name"] == "Chandra Kanta"
    r = api.put("/api/users/profile", json={"headline": "Full-stack dev", "location": "Cuttack"})
    assert r.json["profile"]["headline"] == "Full-stack dev"


def test_assessment_and_recommendations(api):
    register(api)
    assert api.get("/api/careers/recommendations").json["needs_assessment"] is True
    assert api.post("/api/assessment", json={"skills": []}).status_code == 400
    r = api.post("/api/assessment", json=ASSESSMENT)
    assert r.status_code == 201
    recs = r.json["recommendations"]
    assert recs[0]["career"] == "Backend Developer"
    top = recs[0]
    assert top["breakdown"].keys() == {"skills", "interests", "preferences", "education"}
    assert top["missing_skills"] and top["skills_possessed"] and top["recommended_projects"]
    assert "Match =" in r.json["method"]
    # deterministic: same input, same output
    again = api.get("/api/assessment/results").json["recommendations"]
    assert [x["match"] for x in again] == [x["match"] for x in recs]
    assert api.get("/api/careers/recommendations").json["recommendations"][0]["match"] == top["match"]
    assert api.get("/api/assessment").json["assessment"]["degree"] == "BSc"


# ---------- resume ----------
def upload(api, data, name, career=None):
    form = {"resume": (io.BytesIO(data), name)}
    if career:
        form["career_id"] = career
    return api.post("/api/resume/upload", data=form, content_type="multipart/form-data")


def test_resume_upload_validation(api):
    register(api)
    assert api.post("/api/resume/upload", data={}, content_type="multipart/form-data").status_code == 400
    assert upload(api, b"hello world", "resume.txt").status_code == 400
    assert upload(api, b"not really a pdf" * 20, "resume.pdf").status_code == 400  # extension lies
    assert upload(api, b"%PDF" + b"x" * (5 * 1024 * 1024 + 10), "big.pdf").status_code in (400, 413)


def test_resume_analysis_pdf_and_docx(api):
    register(api)
    for data, name in ((make_pdf(), "alex.pdf"), (make_docx(), "alex.docx")):
        r = upload(api, data, name)
        assert r.status_code == 201, r.json
        a = r.json["resume"]["analysis"]
        assert 0 <= a["overall_score"] <= 100 and "not an official ATS score" in a["disclaimer"]
        assert set(a["category_scores"]) == {"skills", "keywords", "experience", "projects", "education", "structure", "readability"}
        assert a["extracted"]["email"] == "alex.rivera@example.com"
        assert "python" in a["extracted"]["skills"] and a["extracted"]["quantified_bullets"] >= 2
        assert {"education", "experience", "skills", "projects"} <= set(a["extracted"]["sections_found"])
    hist = api.get("/api/resume/history").json["resumes"]
    assert len(hist) == 2
    rid = hist[0]["id"]
    assert api.get(f"/api/resume/{rid}").status_code == 200
    r = api.post("/api/resume/analyze", json={"resume_id": rid, "career_id": "devops-engineer"})
    assert r.json["resume"]["analysis"]["target_career_id"] == "devops-engineer"
    assert "docker" in r.json["resume"]["analysis"]["missing_keywords"]


def test_weak_resume_scores_lower(api):
    register(api)
    weak = ["Bob", "I like computers and I am a hard worker who wants a job at a good company with nice people around me."] * 3
    s_weak = upload(api, make_docx(weak), "weak.docx").json["resume"]["analysis"]["overall_score"]
    s_good = upload(api, make_docx(), "good.docx").json["resume"]["analysis"]["overall_score"]
    assert s_good > s_weak + 20


# ---------- skills / roadmap / dashboard ----------
def test_gap_analysis_and_progress(api):
    register(api)
    assert api.get("/api/skills/gap-analysis").status_code == 404
    api.post("/api/assessment", json=ASSESSMENT)
    g = api.get("/api/skills/gap-analysis?career_id=backend-developer").json
    py = next(s for s in g["skills"] if s["skill"] == "python")
    assert py["current"] == 2 and py["required"] == 3 and py["priority"] == "high"
    assert any(s["skill"] == "docker" and s["current"] == 0 for s in g["skills"])
    assert api.put("/api/skills/progress", json={"skill": "python", "level": "advanced"}).status_code == 200
    g2 = api.get("/api/skills/gap-analysis?career_id=backend-developer").json
    assert next(s for s in g2["skills"] if s["skill"] == "python")["current"] == 3
    assert g2["completion_pct"] > g["completion_pct"]
    assert api.put("/api/skills/progress", json={"skill": "python", "level": "godlike"}).status_code == 400


def test_roadmap_generation_and_progress(api):
    register(api)
    assert api.post("/api/roadmap/generate", json={}).status_code == 404  # needs assessment
    api.post("/api/assessment", json=ASSESSMENT)
    r = api.post("/api/roadmap/generate", json={"career_id": "backend-developer"})
    assert r.status_code == 201
    rm = r.json["roadmap"]
    assert [s["key"] for s in rm["stages"]] == ["beginner", "intermediate", "advanced", "job_ready"]
    assert rm["progress"]["pct"] == 0 and rm["total_weeks"] > 0
    tid = rm["stages"][0]["tasks"][0]["id"]
    p = api.put("/api/roadmap/progress", json={"task_id": tid, "done": True})
    assert p.status_code == 200 and p.json["progress"]["done"] == 1
    assert api.get("/api/roadmap").json["roadmap"]["progress"]["done"] == 1  # persisted
    assert api.put("/api/roadmap/progress", json={"task_id": "nope", "done": True}).status_code == 404
    assert api.post("/api/roadmap/generate", json={"career_id": "astronaut"}).status_code == 404


def test_dashboard_is_dynamic(api):
    register(api)
    d = api.get("/api/dashboard").json
    assert d["has_assessment"] is False and d["readiness_score"] is None and d["next_actions"]
    api.post("/api/assessment", json=ASSESSMENT)
    upload(api, make_docx(), "r.docx")
    api.post("/api/roadmap/generate", json={})
    d = api.get("/api/dashboard").json
    assert d["has_assessment"] and d["top_career"]["career"] == "Backend Developer"
    assert d["resume_score"] == d["recent_resume"]["score"] and d["roadmap"]["total"] > 0
    assert 0 <= d["readiness_score"] <= 100 and d["skill_gaps"]


# ---------- data isolation ----------
def test_user_data_isolation(app):
    a_client, b_client = app.test_client(), app.test_client()
    a, b = Api(a_client), Api(b_client)
    register(a, email="a@example.com")
    register(b, email="b@example.com", name="Bee Person")
    a.post("/api/assessment", json=ASSESSMENT)
    a.post("/api/roadmap/generate", json={})
    rid = upload(a, make_docx(), "a.docx").json["resume"]["id"]
    tid = a.get("/api/roadmap").json["roadmap"]["stages"][0]["tasks"][0]["id"]
    # B sees nothing of A's data and cannot touch it
    assert b.get("/api/resume/history").json["resumes"] == []
    assert b.get(f"/api/resume/{rid}").status_code == 404
    assert b.post("/api/resume/analyze", json={"resume_id": rid}).status_code == 404
    assert b.get("/api/assessment").json["assessment"] is None
    assert b.get("/api/roadmap").json["roadmap"] is None
    assert b.put("/api/roadmap/progress", json={"task_id": tid, "done": True}).status_code == 404
    assert b.get("/api/dashboard").json["has_assessment"] is False
    assert a.get("/api/roadmap").json["roadmap"]["progress"]["done"] == 0  # A untouched


def test_health_and_unknown_api(client):
    assert client.get("/api/health").json == {"status": "ok"}
    assert client.get("/api/nope").status_code == 404


# ---------- Google OAuth (mocked; no real Google call is made) ----------
def test_google_disabled_without_credentials(client):
    assert client.get("/api/auth/google/config").json == {"enabled": False}
    assert client.get("/api/auth/google/start").status_code == 503


def test_google_flow_with_mocked_google(app, monkeypatch):
    from app.services import google_service as gs
    for k, v in (("GOOGLE_CLIENT_ID", "cid"), ("GOOGLE_CLIENT_SECRET", "sec"), ("GOOGLE_REDIRECT_URI", "http://localhost/cb")):
        app.config[k] = v
    c = app.test_client()
    assert c.get("/api/auth/google/config").json["enabled"] is True
    r = c.get("/api/auth/google/start")
    assert r.status_code == 302 and "accounts.google.com" in r.location and "client_secret" not in r.location
    state = c.get_cookie("scm_oauth_state", path="/api/auth/google").value
    monkeypatch.setattr(gs, "fetch_profile", lambda cfg, code: {"email": "G.User@example.com", "email_verified": True, "name": "G User", "sub": "123"})
    assert "error=" in c.get("/api/auth/google/callback?code=abc&state=WRONG").location  # CSRF/state check
    ok = c.get(f"/api/auth/google/callback?code=abc&state={state}")
    assert ok.status_code == 302 and ok.location.endswith("/assessment.html")
    assert c.get("/api/auth/me").json["user"]["email"] == "g.user@example.com"
    monkeypatch.setattr(gs, "fetch_profile", lambda cfg, code: {"email": "x@example.com", "email_verified": False})
    c2 = app.test_client(); c2.get("/api/auth/google/start"); st = c2.get_cookie("scm_oauth_state", path="/api/auth/google").value
    assert "error=" in c2.get(f"/api/auth/google/callback?code=abc&state={st}").location  # unverified email refused
