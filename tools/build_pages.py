"""Builds frontend/*.html from the untouched Stitch export (stitch_source/).

Keeps each page's <head> (Tailwind config, fonts, design tokens) plus the header, drawer and bottom nav
exactly as designed. Only the content inside <main> is swapped for live, data-driven sections.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "stitch_source"
OUT = ROOT / "frontend"
raw = lambda name: (SRC / name / "code.html").read_text(encoding="utf-8")

dash = raw("dashboard_overview")
HEAD = dash[dash.find("<head>"):dash.find("</head>") + 7]
HEAD = HEAD.replace("</head>", '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 24 24\'%3E%3Crect width=\'24\' height=\'24\' rx=\'5\' fill=\'%23315c78\'/%3E%3Cpath d=\'M5 17l5-5 3 3 6-7\' stroke=\'white\' stroke-width=\'2\' fill=\'none\' stroke-linecap=\'round\'/%3E%3C/svg%3E"></head>')
body = dash[dash.find("<body"):]
HEADER = re.search(r"<header.*?</header>", body, re.S).group(0)
BACKDROP = re.search(r'<div class="fixed inset-0 z-50[^>]*id="drawer-backdrop"></div>', body, re.S).group(0)
ASIDE = re.search(r"<aside.*?</aside>", body, re.S).group(0)
BOTTOM = re.search(r"<nav class=\"fixed bottom-0.*?</nav>", body, re.S).group(0)
BODY_OPEN = re.search(r"<body[^>]*>", body).group(0)

# --- drawer: real links only (no dead '#'), real user name, logout ---
ASIDE = ASIDE.replace("Candidate Profile", '<span data-user-name>Your account</span>')
ASIDE = re.sub(r'<a class="([^"]*)" data-path="job-opportunities" href="#">.*?</a>',
               r'<a class="\1" href="skills.html"><span class="material-symbols-outlined text-[22px]">psychology</span><span class="font-label-md text-label-md">Skill Gap Analysis</span></a>', ASIDE, flags=re.S)
ASIDE = re.sub(r'<a class="([^"]*)" data-path="settings-preferences" href="#">.*?</a>',
               r'<a class="\1" href="#" data-logout><span class="material-symbols-outlined text-[22px]">logout</span><span class="font-label-md text-label-md">Log out</span></a>', ASIDE, flags=re.S)
HREFS = {"profile-portfolio": "profile.html", "resume-analyzer": "resume-analyzer.html", "dashboard-overview": "dashboard.html",
         "career-assessment": "assessment.html", "career-recommendations": "career-recommendations.html", "learning-roadmap": "roadmap.html"}
def fix_links(html):
    return re.sub(r'data-path="([^"]+)" href="#"', lambda m: f'data-path="{m.group(1)}" href="{HREFS.get(m.group(1), "#")}"', html)
ASIDE, BOTTOM, HEADER = fix_links(ASIDE), fix_links(BOTTOM), fix_links(HEADER)
HEADER = re.sub(r'<button aria-label="Notifications".*?</button>', "", HEADER, flags=re.S)  # no notifications feature exists

ACTIVE, INACTIVE = "text-primary-container font-semibold", "text-on-surface-variant hover:text-primary transition-colors"

def shell(page_title, subtitle, active_path, script):
    nav = BOTTOM.replace(' aria-current="page"', "")
    nav = nav.replace("min-w-[56px] h-12 transition-colors " + ACTIVE, "min-w-[56px] h-12 " + INACTIVE)
    if active_path:
        nav = re.sub(r'(<a )(class="[^"]*?)( ?text-on-surface-variant hover:text-primary transition-colors)(" data-path="%s")' % active_path,
                     r'\1aria-current="page" \2 ' + ACTIVE + r'\4', nav)
    hdr = HEADER.replace("Dashboard Overview", subtitle)
    head = HEAD.replace("<head>", f"<head><title>{page_title} · Smart Career Mentor</title>", 1)
    return (f'<!DOCTYPE html>\n<html lang="en">{head}{BODY_OPEN}{hdr}{BACKDROP}{ASIDE}'
            f'<main class="flex flex-col relative w-full pt-16 pb-24 bg-surface min-h-screen"><div id="root" class="flex flex-col w-full">'
            f'<div class="px-space-md py-space-xl text-center text-text-muted">Loading…</div></div></main>{nav}'
            f'<script src="assets/app.js"></script><script src="assets/pages/{script}.js"></script></body></html>')

PAGES = [  # file, title, header subtitle, bottom-nav key, script
    ("dashboard", "Dashboard", "Dashboard Overview", "dashboard-overview"),
    ("assessment", "Career Assessment", "Career Assessment", "career-assessment"),
    ("career-recommendations", "Career Recommendations", "Career Recommendations", "career-recommendations"),
    ("resume-analyzer", "Resume Analyzer", "Resume Analyzer", "resume-analyzer"),
    ("roadmap", "Learning Roadmap", "Learning Roadmap", "learning-roadmap"),
    ("skills", "Skill Gap Analysis", "Skill Gap Analysis", None),
    ("profile", "Profile", "Profile & Portfolio", "profile-portfolio"),
]
for f, t, sub, key in PAGES:
    (OUT / f"{f}.html").write_text(shell(t, sub, key, f), encoding="utf-8")
    print("built", f)
