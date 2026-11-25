"""Transparent, rule-based career matching.

Match % = 55% skills + 15% interests + 15% role preference + 15% education.
Every component is returned so the UI (and the user) can see exactly how a score was reached.
"""
import re

from ..data.careers_data import CAREERS, PROFICIENCY_LEVELS, RESOURCES, SKILL_ALIASES

WEIGHTS = {"skills": 0.55, "interests": 0.15, "preferences": 0.15, "education": 0.15}
LEVEL_CREDIT = {1: 0.6, 2: 0.85, 3: 1.0}  # having a skill at all earns most credit; depth earns the rest
METHOD = ("Match = 55% skills (weighted by how core each skill is, scaled by your proficiency) + "
          "15% interest overlap + 15% overlap with your preferred roles/goals + 15% education relevance. "
          "No randomness is involved: the same inputs always give the same result.")

_ALIAS_TO_CANON = {}
for canon, aliases in SKILL_ALIASES.items():
    _ALIAS_TO_CANON[canon] = canon
    for a in aliases:
        _ALIAS_TO_CANON[a] = canon


def canon_skill(name: str):
    n = re.sub(r"\s+", " ", (name or "").strip().lower())
    return _ALIAS_TO_CANON.get(n, n)


def normalize_skills(raw):
    """Accepts ["Python", ...] or [{"name": "Python", "level": "advanced"}, ...] -> {canonical: level_int}."""
    out = {}
    for item in raw or []:
        if isinstance(item, dict):
            name, level = item.get("name", ""), item.get("level", "intermediate")
        else:
            name, level = item, "intermediate"
        c = canon_skill(str(name))
        if not c:
            continue
        lv = PROFICIENCY_LEVELS.get(str(level).lower(), 2) if not isinstance(level, int) else max(1, min(3, level))
        out[c] = max(out.get(c, 0), lv)
    return out


def _text_blob(*parts):
    flat = []
    for p in parts:
        flat.extend(p if isinstance(p, list) else [p])
    return " ".join(str(x).lower() for x in flat if x)


def score_career(career, a):
    user = normalize_skills(a.get("skills"))
    # Programming languages are skills too.
    for lang, lv in normalize_skills(a.get("languages")).items():
        user[lang] = max(user.get(lang, 0), lv)

    total_w = sum(career["skills"].values())
    earned = 0.0
    have, missing = [], []
    for skill, w in career["skills"].items():
        if skill in user:
            earned += w * LEVEL_CREDIT[user[skill]]
            have.append({"skill": skill, "level": user[skill], "importance": w})
        else:
            missing.append({"skill": skill, "importance": w})
    skills_score = earned / total_w

    interest_text = _text_blob(a.get("interests"), a.get("strengths"), a.get("career_goals"))
    hits = [k for k in career["interests"] if k in interest_text]
    interest_score = min(1.0, len(hits) / 2)

    pref_text = _text_blob(a.get("preferred_roles"), a.get("career_goals"))
    role_hits = [r for r in career["roles"] if r in pref_text]
    pref_score = 1.0 if role_hits else 0.0

    edu_text = _text_blob(a.get("degree"), a.get("specialization"))
    edu_hits = [f for f in career["fields"] if f in edu_text]
    edu_score = 1.0 if edu_hits else 0.3

    parts = {"skills": skills_score, "interests": interest_score, "preferences": pref_score, "education": edu_score}
    match = round(100 * sum(WEIGHTS[k] * v for k, v in parts.items()))
    missing.sort(key=lambda m: -m["importance"])

    reasons = []
    if have:
        reasons.append(f"You already have {len(have)} of {len(career['skills'])} skills this role looks for.")
    if hits:
        reasons.append("Your interests overlap with this field (" + ", ".join(hits[:3]) + ").")
    if role_hits:
        reasons.append("It matches the roles you said you want.")
    if edu_hits:
        reasons.append("Your education is directly relevant.")
    if missing:
        reasons.append("Biggest gaps: " + ", ".join(m["skill"] for m in missing[:3]) + ".")

    return {
        "career_id": career["id"], "career": career["title"], "tagline": career["tagline"], "match": match,
        "breakdown": {k: round(100 * v) for k, v in parts.items()}, "weights": WEIGHTS,
        "explanation": " ".join(reasons) or "Limited overlap so far; the roadmap shows how to build toward it.",
        "required_skills": [{"skill": s, "importance": w} for s, w in career["skills"].items()],
        "skills_possessed": have, "missing_skills": missing,
        "recommended_projects": career["projects"], "salary_note": career["avg_salary_inr"],
        "learning_path": [{"skill": m["skill"], "resource": RESOURCES.get(m["skill"])} for m in missing[:5]],
    }


def recommend(assessment, limit=6):
    results = [score_career(c, assessment) for c in CAREERS]
    results.sort(key=lambda r: (-r["match"], r["career"]))
    return {"method": METHOD, "recommendations": results[:limit]}


def get_career(career_id):
    return next((c for c in CAREERS if c["id"] == career_id), None)
