(function () {
  const { api, toast } = SCM;
  const $ = (id) => document.getElementById(id);
  const validEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  document.querySelectorAll("[data-toggle]").forEach((b) => b.addEventListener("click", () => {
    const i = $(b.dataset.toggle), show = i.type === "password"; i.type = show ? "text" : "password"; b.firstElementChild.textContent = show ? "visibility_off" : "visibility";
  }));
  const setBusy = (busy, label) => { const b = $("submitBtn"); b.disabled = busy; $("submitText").textContent = busy ? "Please wait…" : label; $("submitSpinner").classList.toggle("hidden", !busy); };
  const show = (id, msg) => { const el = $(id); if (!el) return; if (msg) { el.textContent = msg; el.classList.remove("hidden"); } else el.classList.add("hidden"); };
  const bad = (id, on) => { const e = $(id + "Error"); if (e) e.classList.toggle("hidden", !on); return on; };
  ["email", "password", "passwordError", "fullName"].forEach((id) => $(id) && $(id).addEventListener("input", () => { bad(id, false); show("formError"); }));

  // Google sign-in: only enabled when the server has real credentials configured.
  const g = $("googleBtn");
  if (g) {
    api("GET", "/api/auth/google/config", undefined, { noRedirect: true }).then((c) => {
      if (c.enabled) g.addEventListener("click", () => (location.href = "/api/auth/google/start"));
      else { g.disabled = true; g.title = "Google sign-in isn't configured on this server yet."; g.classList.add("opacity-60", "cursor-not-allowed"); }
    }).catch(() => { g.disabled = true; });
  }
  // Already signed in? Go straight to the dashboard (login/register only).
  if ($("loginForm") || $("registerForm")) api("GET", "/api/auth/me", undefined, { noRedirect: true }).then(() => (location.href = "dashboard.html")).catch(() => {});
  const q = new URLSearchParams(location.search);
  if ($("loginForm") && q.get("error")) show("passwordError", null), toast(q.get("error"), "error");

  if ($("loginForm")) $("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = $("email").value.trim(), pw = $("password").value;
    let ok = true;
    if (!validEmail(email)) { $("emailError").classList.remove("hidden"); ok = false; }
    if (!pw) { $("passwordError").classList.remove("hidden"); ok = false; }
    if (!ok) return;
    setBusy(true);
    try { await api("POST", "/api/auth/login", { email, password: pw, remember: $("remember").checked }, { noRedirect: true }); location.href = "dashboard.html"; }
    catch (ex) { toast(ex.message, "error"); setBusy(false, "Sign In"); }
  });

  if ($("registerForm")) $("registerForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = $("fullName").value.trim(), email = $("email").value.trim(), pw = $("password").value;
    const e1 = bad("fullName", name.length < 2), e2 = bad("email", !validEmail(email)), e3 = bad("password", pw.length < 8 || !/[A-Za-z]/.test(pw) || !/\d/.test(pw));
    if (e1 || e2 || e3) return;
    setBusy(true);
    try { await api("POST", "/api/auth/register", { full_name: name, email, password: pw }, { noRedirect: true }); location.href = "assessment.html"; }
    catch (ex) { show("formError", ex.message); setBusy(false, "Create Account"); }
  });

  if ($("forgotForm")) $("forgotForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = $("email").value.trim();
    if (bad("email", !validEmail(email))) return;
    setBusy(true);
    try { const r = await api("POST", "/api/auth/forgot-password", { email }, { noRedirect: true }); show("formOk", r.message); }
    catch (ex) { show("formError", ex.message); }
    setBusy(false, "Send Reset Link");
  });

  if ($("resetForm")) $("resetForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const pw = $("password").value, token = q.get("token");
    if (!token) return show("formError", "This reset link is invalid. Request a new one.");
    if (bad("password", pw.length < 8 || !/[A-Za-z]/.test(pw) || !/\d/.test(pw))) return;
    setBusy(true);
    try { const r = await api("POST", "/api/auth/reset-password", { token, password: pw }, { noRedirect: true }); show("formOk", r.message); setTimeout(() => (location.href = "login.html"), 1500); }
    catch (ex) { show("formError", ex.message); setBusy(false, "Update Password"); }
  });
})();
