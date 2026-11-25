import uuid
from datetime import datetime, timezone

from ..data.careers_data import RESOURCES
from .career_engine import get_career, normalize_skills

STAGE_META = [
    ("beginner", "Stage 1: Beginner", "Fundamentals, essential concepts and basic exercises."),
    ("intermediate", "Stage 2: Intermediate", "Practical learning, technical skills and small projects."),
    ("advanced", "Stage 3: Advanced", "Real-world projects, advanced concepts and portfolio building."),
    ("job_ready", "Stage 4: Job Ready", "Resume, interview preparation, GitHub portfolio and applications."),
]


def _task(title, kind, weeks, skill=None):
    res = RESOURCES.get(skill) if skill else None
    return {"id": uuid.uuid4().hex[:10], "title": title, "type": kind, "skill": skill, "est_weeks": weeks,
            "resource": {"title": res[0], "url": res[1]} if res else None, "done": False, "completed_at": None}


def generate(assessment, career_id):
    career = get_career(career_id)
    if not career:
        return None
    user = normalize_skills(assessment.get("skills"))
    for k, v in normalize_skills(assessment.get("languages")).items():
        user[k] = max(user.get(k, 0), v)
    missing = sorted([(s, w) for s, w in career["skills"].items() if s not in user], key=lambda x: -x[1])
    shallow = [s for s, w in career["skills"].items() if 0 < user.get(s, 0) < 3 and w >= 2]
    core_missing = [s for s, w in missing if w == 3]
    other_missing = [s for s, w in missing if w < 3]

    s1 = [_task(f"Learn {s} fundamentals", "skill", 2, s) for s in core_missing[:4]]
    s1.append(_task("Complete 10 small practice exercises on your weakest core skill", "exercise", 1))
    s2 = [_task(f"Practice {s} with a hands-on exercise set", "skill", 2, s) for s in (core_missing[4:] + other_missing)[:4]]
    s2.append(_task(f"Mini project: {career['projects'][0]}", "project", 3))
    s3 = [_task(f"Deepen {s} to an advanced level", "skill", 3, s) for s in shallow[:3]]
    s3 += [_task(f"Portfolio project: {career['projects'][1]}", "project", 4),
           _task(f"Portfolio project: {career['projects'][2]}", "project", 4)]
    s4 = [_task("Rewrite your resume and run it through the Resume Analyzer", "milestone", 1),
          _task("Clean up GitHub: READMEs, pinned projects, consistent commits", "milestone", 1),
          _task("Practice interview questions and mock interviews", "milestone", 2),
          _task("Apply to 5 roles per week and track responses", "milestone", 4)]
    stages = []
    for (key, title, desc), tasks in zip(STAGE_META, (s1, s2, s3, s4)):
        stages.append({"key": key, "title": title, "description": desc, "tasks": tasks,
                       "est_weeks": sum(t["est_weeks"] for t in tasks)})
    return {"career_id": career["id"], "career": career["title"], "stages": stages,
            "total_weeks": sum(s["est_weeks"] for s in stages),
            "generated_at": datetime.now(timezone.utc)}


def progress(roadmap):
    tasks = [t for s in roadmap["stages"] for t in s["tasks"]]
    done = sum(1 for t in tasks if t["done"])
    return {"done": done, "total": len(tasks), "pct": round(100 * done / len(tasks)) if tasks else 0}
