"""Builds login / register / forgot-password / reset-password pages from the Stitch login page.
The brand panel, typography, spacing and form styling are kept exactly as designed."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "stitch_source/smart_career_mentor_login/code.html").read_text(encoding="utf-8")
OUT = ROOT / "frontend"

INPUT = 'w-full bg-surface-container-lowest text-on-surface font-body-md text-body-md {pl} pr-{pr} py-2.5 rounded-lg border border-border-subtle placeholder:text-text-muted focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary-container/15 transition-colors'
ERR = '<p class="hidden font-body-sm text-body-sm text-error mt-1.5 flex items-center gap-1" id="{id}"><span class="material-symbols-outlined text-[16px]">error</span><span>{msg}</span></p>'

def field(id, label, icon, typ, ph, auto, msg, toggle=False):
    pr = "11" if toggle else "4"
    eye = ('<button aria-label="Toggle password visibility" class="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-on-surface p-1 rounded transition-colors" data-toggle="%s" type="button"><span class="material-symbols-outlined text-[20px]">visibility</span></button>' % id) if toggle else ""
    return (f'<div><label class="block font-label-md text-label-md text-on-surface mb-1.5" for="{id}">{label}</label><div class="relative">'
            f'<span class="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted text-[20px] pointer-events-none">{icon}</span>'
            f'<input autocomplete="{auto}" class="{INPUT.format(pl="pl-10", pr=pr)}" id="{id}" name="{id}" placeholder="{ph}" required type="{typ}"/>{eye}</div>'
            + ERR.format(id=id + "Error", msg=msg) + "</div>")

BTN = ('<button class="w-full h-11 bg-primary-container hover:bg-primary active:scale-[0.99] text-on-primary font-label-md text-label-md rounded-lg transition-all flex items-center justify-center gap-2 shadow-sm cursor-pointer" id="submitBtn" type="submit"><span id="submitText">{t}</span>'
       '<svg class="hidden animate-spin h-4 w-4 text-on-primary" fill="none" id="submitSpinner" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor"></path></svg></button>')
FORMERR = '<p class="hidden font-body-sm text-body-sm text-error flex items-center gap-1" id="formError" role="alert"></p><p class="hidden font-body-sm text-body-sm text-status-success flex items-center gap-1" id="formOk" role="status"></p>'
HEAD = lambda h, p: f'<div class="mb-8"><h2 class="font-headline-lg text-headline-lg text-on-surface mb-2">{h}</h2><p class="font-body-md text-body-md text-text-muted">{p}</p></div>'
LINK = 'font-label-md text-label-md text-primary-container hover:text-primary transition-colors'
FOOT = lambda t, a, h: f'<p class="text-center font-body-sm text-body-sm text-text-muted mt-8">{t} <a class="{LINK}" href="{h}">{a}</a></p>'

# Keep the original Google button markup, just make it real.
google = re.search(r'<!-- Google Auth Button -->\s*(<button.*?</button>)', src, re.S).group(1)
google = google.replace('<button class="', '<button id="googleBtn" class="', 1)
divider = re.search(r'<!-- Divider -->.*?</div>\s*</div>\s*(?=<!-- Google)', src, re.S).group(0)
social = divider + google

orig_login_form = re.search(r'<div class="mb-8">.*?</form>', src, re.S).group(0)
orig_login_form = orig_login_form.replace('<a class="font-label-md text-label-md text-primary-container hover:text-primary transition-colors" href="#">Forgot password?</a>',
                                          f'<a class="{LINK}" href="forgot-password.html">Forgot password?</a>')

PAGES = {
    "login": (orig_login_form + social + FOOT("Don't have an account?", "Create an account", "register.html"), "Sign In"),
    "register": (HEAD("Create your account", "Start building your future in a few minutes.")
                 + '<form class="space-y-5" id="registerForm" novalidate>'
                 + field("fullName", "Full name", "person", "text", "Enter your full name", "name", "Please enter your full name.")
                 + field("email", "Email address", "mail", "email", "Enter your email address", "email", "Please enter a valid email address.")
                 + field("password", "Password", "lock", "password", "At least 8 characters, letters and numbers", "new-password", "Use 8+ characters with letters and numbers.", True)
                 + FORMERR + BTN.format(t="Create Account") + "</form>" + social + FOOT("Already have an account?", "Sign in", "login.html"), "Create Account"),
    "forgot-password": (HEAD("Reset your password", "Enter your email and we'll send you a reset link.")
                        + '<form class="space-y-5" id="forgotForm" novalidate>' + field("email", "Email address", "mail", "email", "Enter your email address", "email", "Please enter a valid email address.")
                        + FORMERR + BTN.format(t="Send Reset Link") + "</form>" + FOOT("Remembered it?", "Back to sign in", "login.html"), "Forgot Password"),
    "reset-password": (HEAD("Choose a new password", "Pick something strong that you don't use elsewhere.")
                       + '<form class="space-y-5" id="resetForm" novalidate>' + field("password", "New password", "lock", "password", "At least 8 characters, letters and numbers", "new-password", "Use 8+ characters with letters and numbers.", True)
                       + FORMERR + BTN.format(t="Update Password") + "</form>" + FOOT("", "Back to sign in", "login.html"), "Reset Password"),
}

start = src.index('<div class="w-full max-w-[410px]">')
end = src.index("</section>", start)
tail_open = src.index("<script>", end)
for name, (inner, title) in PAGES.items():
    html = src[:start] + '<div class="w-full max-w-[410px]">' + inner + "</div>\n" + src[end:tail_open]
    html = html.replace("<head>", f"<head><title>{title} · Smart Career Mentor</title>", 1)
    html += '<script src="assets/app.js"></script><script src="assets/auth.js"></script></main></body></html>'
    (OUT / f"{name}.html").write_text(html, encoding="utf-8")
    print("built", name)
