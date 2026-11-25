/* Smart Career Mentor - shared client helpers. No secrets live here. */
(function () {
  const getCookie = (n) => (document.cookie.split("; ").find((c) => c.startsWith(n + "=")) || "").split("=")[1] || "";

  async function api(method, url, body, opts = {}) {
    const headers = { Accept: "application/json" };
    let payload;
    if (body instanceof FormData) payload = body;
    else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
    const csrf = getCookie("scm_csrf");
    if (csrf) headers["X-CSRF-Token"] = decodeURIComponent(csrf);
    let res;
    try { res = await fetch(url, { method, headers, body: payload, credentials: "same-origin" }); }
    catch (e) { throw Object.assign(new Error("Can't reach the server. Check your connection and try again."), { network: true }); }
    let data = {};
    try { data = await res.json(); } catch (_) {}
    if (res.status === 401 && !opts.noRedirect) { location.href = "login.html"; throw Object.assign(new Error("Please sign in."), { status: 401 }); }
    if (!res.ok) throw Object.assign(new Error(data.error || "Something went wrong."), { status: res.status, data });
    return data;
  }

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const title = (s) => String(s || "").replace(/\b\w/g, (c) => c.toUpperCase());
  const skillLabel = (s) => ({ "ci/cd": "CI/CD", "rest apis": "REST APIs", "sql": "SQL", "aws": "AWS", "html": "HTML", "css": "CSS", "node.js": "Node.js",
    "mongodb": "MongoDB", "c++": "C++", "ui design": "UI Design", "etl": "ETL" }[s] || title(s));

  function toast(msg, kind) {
    let t = document.getElementById("scm-toast");
    if (!t) {
      t = document.createElement("div"); t.id = "scm-toast"; t.setAttribute("role", "status");
      t.className = "fixed left-1/2 -translate-x-1/2 bottom-24 z-[60] max-w-[90vw] px-4 py-2.5 rounded-lg shadow-lg font-label-md text-label-md transition-opacity duration-300 opacity-0 pointer-events-none";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.className = t.className.replace(/bg-\S+|text-\S+/g, "") + (kind === "error" ? " bg-error text-on-error" : " bg-inverse-surface text-inverse-on-surface");
    requestAnimationFrame(() => (t.style.opacity = 1));
    clearTimeout(t._h); t._h = setTimeout(() => (t.style.opacity = 0), 3200);
  }

  const loading = (label = "Loading…") => `<div class="px-space-md py-space-xl flex items-center justify-center gap-2 text-text-muted font-body-md"><svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>${esc(label)}</div>`;
  const errorBox = (msg, retry = true) => `<div class="mx-space-md my-space-md p-space-md rounded-xl bg-error-container text-on-error-container font-body-md flex items-start gap-2"><span class="material-symbols-outlined text-[20px]">error</span><div class="flex-1"><p>${esc(msg)}</p>${retry ? '<button onclick="location.reload()" class="mt-2 underline font-label-md">Try again</button>' : ""}</div></div>`;
  const empty = (icon, head, text, href, cta) => `<div class="mx-space-md my-space-md p-space-lg rounded-xl bg-surface-container-lowest shadow-sm text-center"><span class="material-symbols-outlined text-[36px] text-primary-container">${icon}</span><h3 class="font-headline-sm text-headline-sm text-on-surface mt-2">${esc(head)}</h3><p class="font-body-md text-text-muted mt-1">${esc(text)}</p>${href ? `<a href="${href}" class="inline-flex mt-space-md px-space-md h-10 items-center rounded-lg bg-primary text-on-primary font-label-md hover:bg-primary-container transition-colors">${esc(cta)}</a>` : ""}</div>`;
  const bar = (cur, req, color = "bg-primary-container") => `<div class="w-full bg-surface-container-highest rounded-full h-2 relative overflow-hidden"><div class="${color} h-2 rounded-full absolute left-0 top-0 z-10" style="width:${cur}%"></div><div class="bg-surface-container h-2 rounded-full absolute left-0 top-0" style="width:${req}%"></div></div>`;
  const ring = (pct) => { const r = 28, c = 2 * Math.PI * r; return `<svg class="w-20 h-20 -rotate-90" viewBox="0 0 64 64"><circle cx="32" cy="32" r="${r}" fill="none" stroke="#e4effd" stroke-width="6"></circle><circle cx="32" cy="32" r="${r}" fill="none" stroke="#315c78" stroke-width="6" stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - pct / 100)}"></circle></svg>`; };
  const ago = (iso) => { const m = Math.round((Date.now() - new Date(iso)) / 60000); return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`; };

  async function requireAuth() {
    const { user } = await api("GET", "/api/auth/me");
    document.querySelectorAll("[data-user-name]").forEach((el) => (el.textContent = user.full_name));
    document.querySelectorAll("[data-logout]").forEach((el) => el.addEventListener("click", async (e) => {
      e.preventDefault(); try { await api("POST", "/api/auth/logout", {}, { noRedirect: true }); } catch (_) {} location.href = "login.html";
    }));
    return user;
  }

  // Drawer behaviour (same as the Stitch export).
  document.addEventListener("DOMContentLoaded", () => {
    const d = document.getElementById("app-drawer"), b = document.getElementById("drawer-backdrop");
    const open = () => { d && d.classList.remove("-translate-x-full"); b && b.classList.remove("opacity-0", "pointer-events-none"); };
    const close = () => { d && d.classList.add("-translate-x-full"); b && b.classList.add("opacity-0", "pointer-events-none"); };
    const t = document.getElementById("menu-drawer-toggle"), c = document.getElementById("menu-drawer-close");
    t && t.addEventListener("click", open); c && c.addEventListener("click", close); b && b.addEventListener("click", close);
  });

  window.SCM = { api, esc, title, skillLabel, toast, loading, errorBox, empty, bar, ring, ago, requireAuth };
})();
