import re
from email_validator import EmailNotValidError, validate_email

MAX_LIST = 60


def clean_email(raw):
    if not isinstance(raw, str):
        return None
    try:
        return validate_email(raw.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return None


def password_problem(pw):
    if not isinstance(pw, str) or len(pw) < 8:
        return "Password must be at least 8 characters."
    if len(pw) > 128:
        return "Password is too long."
    if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
        return "Password must include letters and numbers."
    return None


def clean_str(v, max_len=200):
    """Strings only: rejects dicts/lists so Mongo operator injection ({"$ne": ...}) is impossible."""
    if not isinstance(v, str):
        return ""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", v).strip()[:max_len]


def clean_list(v, max_len=60):
    if isinstance(v, str):
        v = re.split(r"[,\n;]", v)
    if not isinstance(v, list):
        return []
    out, seen = [], set()
    for item in v[:MAX_LIST]:
        s = clean_str(item, max_len)
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out
