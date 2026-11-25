from ..data.careers_data import RESOURCES
from .career_engine import get_career, normalize_skills

LEVEL_NAMES = {0: "none", 1: "beginner", 2: "intermediate", 3: "advanced"}


def gap_analysis(assessment, career_id):
    career = get_career(career_id)
    if not career:
        return None
    user = normalize_skills(assessment.get("skills"))
    for k, v in normalize_skills(assessment.get("languages")).items():
        user[k] = max(user.get(k, 0), v)
    rows = []
    for skill, imp in career["skills"].items():
        cur, req = user.get(skill, 0), imp  # core skills need advanced, important intermediate, nice-to-have beginner
        gap = max(0, req - cur)
        priority = "none" if gap == 0 else "high" if imp == 3 else "medium" if imp == 2 else "low"
        res = RESOURCES.get(skill)
        rows.append({"skill": skill, "current": cur, "current_label": LEVEL_NAMES[cur], "required": req,
                     "required_label": LEVEL_NAMES[req], "gap": gap, "priority": priority,
                     "current_pct": round(cur / 3 * 100), "required_pct": round(req / 3 * 100),
                     "resource": {"title": res[0], "url": res[1]} if res else None})
    order = {"high": 0, "medium": 1, "low": 2, "none": 3}
    rows.sort(key=lambda r: (order[r["priority"]], -r["gap"], r["skill"]))
    have = [r for r in rows if r["current"] > 0]
    plan = [f"Study {r['skill']} to {r['required_label']} level" for r in rows if r["gap"] > 0][:6]
    return {"career_id": career["id"], "career": career["title"], "skills": rows,
            "existing_count": len(have), "total_required": len(rows),
            "completion_pct": round(100 * sum(min(r["current"], r["required"]) for r in rows) / max(1, sum(r["required"] for r in rows))),
            "improvement_plan": plan}
