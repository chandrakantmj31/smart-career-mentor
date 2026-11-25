(async function () {
  const { api, esc, loading, errorBox, toast } = SCM;
  const root = document.getElementById("root");
  root.innerHTML = loading("Loading profile…");
  const inp = "w-full bg-surface-container-lowest text-on-surface font-body-md px-3 py-2.5 rounded-lg border border-border-subtle focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary-container/15";
  try {
    await SCM.requireAuth();
    const p = (await api("GET", "/api/users/profile")).profile;
    const f = (id, label, val, ph) => `<label class="block font-label-md text-on-surface" for="${id}">${label}<input id="${id}" class="${inp} mt-1.5" value="${esc(val)}" placeholder="${ph || ""}"></label>`;
    root.innerHTML = `<form id="form" class="px-space-md pt-space-md flex flex-col gap-space-md" novalidate><div><h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface font-semibold tracking-tight">Profile &amp; Portfolio</h1><p class="font-body-md text-text-muted">${esc(p.email)} · member since ${p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}</p></div>
<section class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col gap-space-sm">${f("full_name", "Full name", p.full_name)}${f("headline", "Headline", p.headline, "e.g. Full-stack developer")}${f("location", "Location", p.location)}${f("github", "GitHub URL", p.github, "https://github.com/…")}${f("linkedin", "LinkedIn URL", p.linkedin, "https://linkedin.com/in/…")}
<label class="block font-label-md" for="bio">Bio<textarea id="bio" rows="3" class="${inp} mt-1.5">${esc(p.bio)}</textarea></label></section>
<button class="w-full h-11 bg-primary-container hover:bg-primary text-on-primary font-label-md rounded-lg shadow-sm">Save profile</button>
<a href="#" data-logout class="text-center font-label-md text-error py-2">Log out</a></form>`;
    root.querySelector("[data-logout]").addEventListener("click", async (e) => { e.preventDefault(); await api("POST", "/api/auth/logout", {}, { noRedirect: true }).catch(() => {}); location.href = "login.html"; });
    document.getElementById("form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = Object.fromEntries(["full_name", "headline", "location", "github", "linkedin", "bio"].map((k) => [k, document.getElementById(k).value]));
      try { await api("PUT", "/api/users/profile", body); toast("Profile saved."); } catch (ex) { toast(ex.message, "error"); }
    });
  } catch (e) { if (e.status !== 401) root.innerHTML = errorBox(e.message); }
})();
