"""Rule-based resume analysis. Runs entirely on this server: the file is never sent to a third party.

The score is an *estimate* of ATS-friendliness based on transparent rules. Real ATS products differ.
"""
import io
import re

from ..data.careers_data import ACTION_VERBS, CAREERS, SKILL_ALIASES
from .career_engine import canon_skill

DISCLAIMER = ("This is an estimate based on open, explainable rules, not an official ATS score. "
              "Real applicant tracking systems differ from each other.")
MAGIC = {"pdf": b"%PDF", "docx": b"PK\x03\x04"}
SECTION_HEADS = {
    "education": r"education|academic", "experience": r"experience|employment|internship|work history",
    "skills": r"skills|technologies|technical", "projects": r"projects?", "certifications": r"certifications?|certificates?|courses",
    "summary": r"summary|objective|profile|about",
}
WEIGHTS = {"skills": 0.25, "keywords": 0.20, "experience": 0.20, "projects": 0.15, "education": 0.10, "structure": 0.05, "readability": 0.05}


class ResumeError(ValueError):
    pass


def detect_type(filename: str, head: bytes):
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in MAGIC or not head.startswith(MAGIC[ext]):
        raise ResumeError("Only genuine PDF or DOCX files are accepted.")
    return ext


def extract_text(data: bytes, kind: str) -> str:
    try:
        if kind == "pdf":
            import pdfplumber
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                if len(pdf.pages) > 6:
                    raise ResumeError("Resume has too many pages (max 6).")
                text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        else:
            import docx
            d = docx.Document(io.BytesIO(data))
            lines = [p.text for p in d.paragraphs]
            for t in d.tables:
                for row in t.rows:
                    lines.append(" ".join(c.text for c in row.cells))
            text = "\n".join(lines)
    except ResumeError:
        raise
    except Exception:
        raise ResumeError("Could not read this file. It may be corrupted or password-protected.")
    if len(text.strip()) < 80:
        raise ResumeError("Very little text could be extracted. Scanned/image-only resumes are not supported; export a text-based PDF or DOCX.")
    return text


def split_sections(text):
    sections, current = {"header": []}, "header"
    for line in text.splitlines():
        s = line.strip()
        matched = None
        if 0 < len(s) <= 40:
            for name, pat in SECTION_HEADS.items():
                if re.fullmatch(rf"(?i)\W*({pat})\W*", s):
                    matched = name
                    break
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections[current].append(s)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def find_skills(text):
    low = " " + text.lower() + " "
    found = set()
    for canon, aliases in SKILL_ALIASES.items():
        for term in [canon] + aliases:
            if re.search(r"(?<![a-z0-9+#.])" + re.escape(term) + r"(?![a-z0-9+#])", low):
                found.add(canon)
                break
    return sorted(found)


def analyze(text, target_career=None):
    sections = split_sections(text)
    skills_found = find_skills(text)
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    phone = re.search(r"(\+?\d[\d\s().-]{8,}\d)", text)
    links = re.findall(r"(?:https?://)?(?:www\.)?(?:linkedin\.com|github\.com)/[\w\-./]+", text, re.I)

    bullets = [l.strip(" •-–*\t") for l in text.splitlines() if re.match(r"^\s*[•\-–*▪●]", l)]
    if not bullets:  # fall back to sentence-like lines
        bullets = [l.strip() for l in text.splitlines() if len(l.split()) >= 6]
    quantified = [b for b in bullets if re.search(r"\d+\s*%|\$\s*\d|₹\s*\d|\b\d{2,}\b|\b\d+x\b", b)]
    verb_bullets = [b for b in bullets if b.split() and b.split()[0].lower().strip(",.:;") in ACTION_VERBS]

    career = next((c for c in CAREERS if c["id"] == target_career), None)
    if career is None:  # best-fit: career whose skills overlap most with the resume
        career = max(CAREERS, key=lambda c: sum(w for s, w in c["skills"].items() if s in skills_found))
    wanted = career["skills"]
    present_kw = [s for s in wanted if s in skills_found]
    missing_kw = [s for s in sorted(wanted, key=lambda s: -wanted[s]) if s not in skills_found]
    kw_cov = sum(w for s, w in wanted.items() if s in skills_found) / sum(wanted.values())

    words = len(text.split())
    exp_text = sections.get("experience", "")
    proj_text = sections.get("projects", "")
    n_proj = len([l for l in proj_text.splitlines() if l.strip()]) if proj_text else 0

    scores = {}
    scores["skills"] = min(100, round(len(skills_found) / 10 * 100))
    scores["keywords"] = round(kw_cov * 100)
    exp_pts = 30 if exp_text else 0
    exp_pts += min(40, round(len(quantified) / max(1, min(len(bullets), 8)) * 40)) if bullets else 0
    exp_pts += min(30, round(len(verb_bullets) / max(1, min(len(bullets), 8)) * 30)) if bullets else 0
    scores["experience"] = min(100, exp_pts) if exp_text or bullets else 0
    scores["projects"] = 0 if not proj_text else min(100, 40 + 15 * min(n_proj, 4))
    scores["education"] = 100 if sections.get("education") else 20
    struct = sum(1 for k in ("education", "experience", "skills", "projects") if k in sections)
    scores["structure"] = round(struct / 4 * 70 + (15 if email else 0) + (15 if phone else 0))
    scores["readability"] = 100 if 250 <= words <= 900 else 70 if 150 <= words <= 1200 else 40
    overall = round(sum(WEIGHTS[k] * v for k, v in scores.items()))

    weak, tips = [], []
    if "experience" not in sections:
        weak.append("Experience"); tips.append("Add an Experience or Internships section, even for academic or freelance work.")
    elif len(quantified) < max(2, len(bullets) // 4):
        weak.append("Experience"); tips.append("Add measurable results to your bullets (e.g. 'reduced load time by 30%', 'served 500 users').")
    if "projects" not in sections:
        weak.append("Projects"); tips.append("Add a Projects section with 2-4 projects: what you built, the tech used, and the outcome.")
    if "skills" not in sections:
        weak.append("Skills"); tips.append("Add a dedicated Skills section so scanners can find your keywords quickly.")
    if "education" not in sections:
        weak.append("Education"); tips.append("Add an Education section with degree, institution and year.")
    if not email:
        tips.append("Include a professional email address in the header.")
    if not links:
        tips.append("Add your GitHub and/or LinkedIn URL.")
    if words < 150:
        weak.append("Length"); tips.append("Your resume is very short; expand on impact and responsibilities.")
    elif words > 1200:
        weak.append("Length"); tips.append("Your resume is long; aim for 1 page (freshers) or 2 pages maximum.")
    if verb_bullets and len(verb_bullets) < len(bullets) // 2:
        tips.append("Start more bullets with strong action verbs (built, designed, optimized, deployed).")
    if missing_kw:
        tips.append(f"For {career['title']} roles, consider adding (only if true): " + ", ".join(missing_kw[:6]) + ".")

    return {
        "disclaimer": DISCLAIMER, "target_career": career["title"], "target_career_id": career["id"],
        "overall_score": overall, "category_scores": scores, "weights": WEIGHTS,
        "extracted": {
            "email": email.group(0) if email else None, "phone_found": bool(phone), "links": links[:4],
            "skills": skills_found, "sections_found": [k for k in sections if k != "header" and sections[k]],
            "education": sections.get("education", "")[:500], "experience": exp_text[:1200],
            "projects": proj_text[:1200], "certifications": sections.get("certifications", "")[:500],
            "word_count": words, "bullet_count": len(bullets), "quantified_bullets": len(quantified),
        },
        "keywords_present": present_kw, "missing_keywords": missing_kw, "weak_sections": weak,
        "suggestions": tips, "recommended_skills": missing_kw[:6],
        "improvement_examples": [{"original": b, "tip": "Add a number: how many users/files/ms/% improved? What was the result?"}
                                 for b in bullets if b not in quantified][:3],
    }
