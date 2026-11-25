import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import create_app  # noqa: E402

RESUME_LINES = [
    "Alex Rivera", "alex.rivera@example.com | +91 98765 43210 | github.com/alexr | linkedin.com/in/alexr",
    "Summary", "Full-stack developer who enjoys building reliable web products and learning quickly.",
    "Skills", "Python, JavaScript, TypeScript, React, Node.js, Flask, SQL, MongoDB, Git, REST APIs, HTML, CSS",
    "Experience", "Web Development Intern - Acme Labs (2025)",
    "- Built 12 reusable React components, reducing page load time by 35%",
    "- Developed a Flask REST API serving 5000 monthly users",
    "- Implemented unit tests with pytest covering 80% of modules",
    "Projects", "Task Manager - Flask, MongoDB, React full-stack app with JWT authentication",
    "Portfolio Website - responsive site using HTML, CSS and JavaScript",
    "Education", "BSc Computer Science, Utkal University, 2026",
    "Certifications", "Meta Front-End Developer Certificate",
]


def make_docx(lines=RESUME_LINES):
    import docx
    d = docx.Document()
    for l in lines:
        d.add_paragraph(l)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def make_pdf(lines=RESUME_LINES):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for l in lines:
        c.drawString(50, y, l)
        y -= 18
    c.save()
    return buf.getvalue()


@pytest.fixture()
def app():
    return create_app(testing=True)


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf_headers(c):
    cookie = c.get_cookie("scm_csrf")
    return {"X-CSRF-Token": cookie.value} if cookie else {}


class Api:
    """Tiny helper that sends the CSRF header automatically, like the frontend does."""
    def __init__(self, c):
        self.c = c

    def post(self, url, **kw):
        return self.c.post(url, headers=csrf_headers(self.c), **kw)

    def put(self, url, **kw):
        return self.c.put(url, headers=csrf_headers(self.c), **kw)

    def get(self, url, **kw):
        return self.c.get(url, **kw)


@pytest.fixture()
def api(client):
    return Api(client)


def register(api, email="chandra@example.com", pw="Passw0rdOK", name="Chandra Kanta"):
    return api.post("/api/auth/register", json={"full_name": name, "email": email, "password": pw})


ASSESSMENT = {
    "degree": "BSc", "specialization": "Computer Science",
    "skills": [{"name": "Python", "level": "intermediate"}, {"name": "SQL", "level": "intermediate"}, {"name": "Git", "level": "advanced"}],
    "languages": ["JavaScript"], "interests": ["backend", "apis"], "preferred_roles": ["Backend Developer"],
    "career_goals": "Become a backend engineer",
}
