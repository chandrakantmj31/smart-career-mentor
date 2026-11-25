import sys, re
sys.path.insert(0, "backend/tests"); sys.path.insert(0, "backend")
from conftest import make_pdf
from playwright.sync_api import sync_playwright, expect

BASE = "http://localhost:5055"
open("/tmp/resume.pdf", "wb").write(make_pdf())
errors, steps = [], []
def ok(msg): steps.append(msg); print("PASS", msg)

with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={"width": 390, "height": 844}); page = ctx.new_page()
    page.route(re.compile(r"https?://(?!localhost).*"), lambda r: r.abort())  # sandbox has no internet; app code is local
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "ERR_FAILED" not in m.text and "Failed to load resource" not in m.text else None)

    page.goto(f"{BASE}/register.html", wait_until="domcontentloaded")
    page.fill("#fullName", "Chandrakant Test"); page.fill("#email", "e2e@example.com"); page.fill("#password", "Passw0rdOK")
    page.click("#submitBtn"); page.wait_for_url("**/assessment.html"); ok("register -> redirected to assessment")

    page.wait_for_selector("#form")
    page.fill("#degree", "BSc (Hons)"); page.fill("#specialization", "Computer Science")
    page.fill("#skills", "Python:advanced, SQL, Git, React, Flask"); page.fill("#languages", "JavaScript:advanced")
    page.fill("#interests", "web, backend, apis"); page.fill("#preferred_roles", "Full Stack Developer, Backend Developer")
    page.click("#submit"); page.wait_for_url("**/career-recommendations.html"); ok("assessment saved")

    page.wait_for_selector("article"); n = page.locator("article").count()
    top = page.locator("article").first.inner_text()
    assert n >= 6 and "%" in top and "How this match is calculated" in top, top[:200]; ok(f"{n} recommendations rendered with calculation breakdown")

    page.goto(f"{BASE}/resume-analyzer.html", wait_until="domcontentloaded"); page.wait_for_selector("#file")
    page.set_input_files("#file", "/tmp/resume.pdf"); page.click("#analyze")
    page.wait_for_selector("text=ATS-style compatibility estimate"); txt = page.inner_text("#results")
    assert "not an official ATS score" in txt and "Keyword coverage" in txt; ok("resume uploaded + analyzed + disclaimer shown")

    page.goto(f"{BASE}/skills.html", wait_until="domcontentloaded"); page.wait_for_selector("text=Your improvement plan"); ok("skill gap page renders")
    sel = page.locator("select[data-skill]").first; before = page.inner_text("#root")[:0]
    sel.select_option("advanced"); page.wait_for_selector("text=Progress saved"); ok("skill level update persisted")

    page.goto(f"{BASE}/roadmap.html", wait_until="domcontentloaded"); page.wait_for_selector("#go"); page.click("#go")
    page.wait_for_selector("input[data-task]"); page.locator("input[data-task]").first.check()
    page.wait_for_function("document.getElementById('pcount').textContent.startsWith('1 of')"); ok("roadmap generated + task completion saved")
    page.reload(wait_until="domcontentloaded"); page.wait_for_selector("input[data-task]")
    assert page.locator("input[data-task]").first.is_checked(); ok("progress persists after refresh")

    page.goto(f"{BASE}/dashboard.html", wait_until="domcontentloaded"); page.wait_for_selector("text=Recommended Actions"); d = page.inner_text("#root")
    assert "Chandrakant" in d and "Alex" not in d and "Staff AI" not in d and "Latest Resume Analysis" in d and "tasks done" in d; ok("dashboard shows real data, no placeholders")
    page.screenshot(path="/tmp/dash.png", full_page=True)

    page.goto(f"{BASE}/profile.html", wait_until="domcontentloaded"); page.wait_for_selector("#headline"); page.fill("#headline", "Full-stack dev"); page.click("text=Save profile"); page.wait_for_selector("text=Profile saved"); ok("profile saved")

    page.evaluate("document.querySelector('[data-logout]').click()"); page.wait_for_url("**/login.html"); ok("logout")
    page.goto(f"{BASE}/dashboard.html", wait_until="domcontentloaded"); page.wait_for_url("**/login.html"); ok("protected page redirects to login when signed out")
    page.fill("#email", "e2e@example.com"); page.fill("#password", "WrongPass9"); page.click("#submitBtn"); page.wait_for_selector("text=Invalid email or password"); ok("wrong password shows error")
    page.fill("#password", "Passw0rdOK"); page.check("#remember"); page.click("#submitBtn"); page.wait_for_url("**/dashboard.html"); ok("login works")
    page.reload(wait_until="domcontentloaded"); page.wait_for_selector("text=Recommended Actions"); ok("stays authenticated after refresh")
    b.close()
print("\nJS errors:", errors or "none"); print(len(steps), "steps passed")
