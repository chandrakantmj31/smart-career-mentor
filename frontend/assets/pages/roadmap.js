(async function () {
  const { api, esc, loading, errorBox, toast } = SCM;
  const root = document.getElementById("root");
  root.innerHTML = loading("Loading your roadmap…");
  const icon = { skill: "menu_book", project: "build", exercise: "edit_note", milestone: "flag" };
  function render(rm) {
    root.innerHTML = `<section class="px-space-md pt-space-md pb-space-sm"><h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface font-semibold tracking-tight">${esc(rm.career)} Roadmap</h1><p class="font-body-md text-on-surface-variant">About ${rm.total_weeks} weeks of focused work in four stages.</p>
<div class="mt-space-sm bg-surface-container-lowest rounded-xl p-space-md shadow-sm"><div class="flex justify-between font-label-md"><span>Overall progress</span><span id="pct" class="font-metric-inline text-primary">${rm.progress.pct}%</span></div><div class="w-full bg-surface-container rounded-full h-2 mt-2 overflow-hidden"><div id="pbar" class="bg-primary-container h-2 rounded-full transition-all duration-500" style="width:${rm.progress.pct}%"></div></div><p id="pcount" class="font-label-sm text-text-muted mt-1">${rm.progress.done} of ${rm.progress.total} tasks complete</p></div></section>
<section class="px-space-md flex flex-col gap-space-md">${rm.stages.map((s) => `<div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-md"><div class="flex items-start justify-between gap-2"><div><h2 class="font-headline-sm text-headline-sm font-semibold text-on-surface">${esc(s.title)}</h2><p class="font-body-sm text-text-muted">${esc(s.description)}</p></div><span class="font-label-sm text-text-muted shrink-0">~${s.est_weeks} wk</span></div><ul class="mt-space-sm flex flex-col gap-1">${s.tasks.map((t) => `<li class="flex items-start gap-2 p-2 rounded-lg hover:bg-surface-bg"><input type="checkbox" data-task="${t.id}" ${t.done ? "checked" : ""} aria-label="Mark complete: ${esc(t.title)}" class="mt-1 w-4 h-4 rounded border-border-subtle text-primary-container"><div class="min-w-0 flex-1"><p class="font-body-md ${t.done ? "line-through text-text-muted" : "text-on-surface"}" data-title="${t.id}"><span class="material-symbols-outlined text-[16px] align-text-bottom text-primary-container mr-1">${icon[t.type] || "task"}</span>${esc(t.title)}</p><p class="font-label-sm text-text-muted">~${t.est_weeks} wk${t.resource ? ` · <a class="text-primary-container underline" target="_blank" rel="noopener noreferrer" href="${esc(t.resource.url)}">${esc(t.resource.title)}</a>` : ""}</p></div></li>`).join("")}</ul></div>`).join("")}</section>
<div class="px-space-md py-space-md"><button id="regen" class="font-label-md text-primary-container underline">Regenerate roadmap (resets progress)</button></div>`;
    root.querySelectorAll("[data-task]").forEach((cb) => cb.addEventListener("change", async () => {
      const done = cb.checked;
      try {
        const { progress } = await api("PUT", "/api/roadmap/progress", { task_id: cb.dataset.task, done });
        document.getElementById("pct").textContent = progress.pct + "%"; document.getElementById("pbar").style.width = progress.pct + "%";
        document.getElementById("pcount").textContent = `${progress.done} of ${progress.total} tasks complete`;
        const ti = root.querySelector(`[data-title="${cb.dataset.task}"]`); ti.classList.toggle("line-through", done); ti.classList.toggle("text-text-muted", done); ti.classList.toggle("text-on-surface", !done);
      } catch (e) { cb.checked = !done; toast(e.message, "error"); }
    }));
    document.getElementById("regen").addEventListener("click", () => { if (confirm("Regenerate your roadmap? Your task progress will be reset.")) generate(rm.career_id); });
  }
  async function generate(careerId) {
    root.innerHTML = loading("Building your roadmap…");
    try { render((await api("POST", "/api/roadmap/generate", careerId ? { career_id: careerId } : {})).roadmap); }
    catch (e) { root.innerHTML = e.status === 404 ? SCM.empty("psychology_alt", "Assessment needed", "Complete the assessment first so your roadmap fits your current skills.", "assessment.html", "Start assessment") : errorBox(e.message); }
  }
  try {
    await SCM.requireAuth();
    const { roadmap } = await api("GET", "/api/roadmap");
    if (roadmap) return render(roadmap);
    const a = (await api("GET", "/api/assessment")).assessment;
    if (!a) return (root.innerHTML = SCM.empty("psychology_alt", "No roadmap yet", "Complete the assessment first so your roadmap fits your current skills.", "assessment.html", "Start assessment"));
    root.innerHTML = SCM.empty("moving", "Ready to build your roadmap", "We'll plan four stages (Beginner → Job Ready) toward your top-matched career.", null, "") + `<div class="px-space-md text-center"><button id="go" class="px-space-md h-11 rounded-lg bg-primary text-on-primary font-label-md hover:bg-primary-container">Generate roadmap</button></div>`;
    document.getElementById("go").addEventListener("click", () => generate());
  } catch (e) { if (e.status !== 401) root.innerHTML = errorBox(e.message); }
})();
