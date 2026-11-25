(async function () {
  const { api, esc, skillLabel, loading, errorBox, toast, bar } = SCM;
  const root = document.getElementById("root");
  root.innerHTML = loading("Analyzing your skills…");
  const PRI = { high: "bg-error-container text-on-error-container", medium: "bg-status-warning/15 text-status-warning", low: "bg-surface-container text-on-surface-variant", none: "bg-secondary-container text-on-secondary-container" };
  async function load(careerId) {
    try {
      const [g, careers] = await Promise.all([api("GET", "/api/skills/gap-analysis" + (careerId ? "?career_id=" + encodeURIComponent(careerId) : "")), api("GET", "/api/careers/available")]);
      root.innerHTML = `<section class="px-space-md pt-space-md"><h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface font-semibold tracking-tight">Skill Gap Analysis</h1>
<label class="block mt-space-sm font-label-md text-on-surface">Target career<select id="career" class="mt-1 w-full bg-surface-container-lowest rounded-lg border border-border-subtle px-3 py-2.5">${careers.careers.map((c) => `<option value="${esc(c.id)}" ${c.id === g.career_id ? "selected" : ""}>${esc(c.title)}</option>`).join("")}</select></label>
<div class="mt-space-sm bg-surface-container-lowest rounded-xl p-space-md shadow-sm"><div class="flex justify-between font-label-md"><span>Coverage of ${esc(g.career)}</span><span class="font-metric-inline text-primary">${g.completion_pct}%</span></div><div class="w-full bg-surface-container rounded-full h-2 mt-2 overflow-hidden"><div class="bg-primary-container h-2 rounded-full" style="width:${g.completion_pct}%"></div></div><p class="font-label-sm text-text-muted mt-1">You have ${g.existing_count} of ${g.total_required} required skills.</p></div></section>
<section class="px-space-md mt-space-md flex flex-col gap-space-xs">${g.skills.map((s) => `<div class="bg-surface-container-lowest rounded-xl p-space-md shadow-sm"><div class="flex items-center justify-between gap-2"><span class="font-label-md font-semibold text-on-surface">${esc(skillLabel(s.skill))}</span><span class="px-2 py-0.5 rounded-full font-label-sm text-[10px] ${PRI[s.priority]}">${s.priority === "none" ? "On target" : s.priority + " priority"}</span></div><div class="flex justify-between font-label-sm text-text-muted mt-1"><span>Current: ${s.current_label}</span><span>Required: ${s.required_label}</span></div><div class="mt-1">${bar(s.current_pct, s.required_pct)}</div>
<div class="flex items-center justify-between mt-2 gap-2">${s.resource ? `<a class="font-label-sm text-primary-container underline truncate" target="_blank" rel="noopener noreferrer" href="${esc(s.resource.url)}">${esc(s.resource.title)}</a>` : "<span></span>"}<select data-skill="${esc(s.skill)}" aria-label="Set your level for ${esc(skillLabel(s.skill))}" class="font-label-sm bg-surface-container rounded px-2 py-1">${["none", "beginner", "intermediate", "advanced"].map((l, i) => `<option value="${l}" ${i === s.current ? "selected" : ""} ${l === "none" ? "disabled" : ""}>${l === "none" ? "Not yet" : l}</option>`).join("")}</select></div></div>`).join("")}</section>
<section class="px-space-md mt-space-md"><div class="bg-surface-container-lowest rounded-xl p-space-md shadow-sm"><h2 class="font-headline-sm text-label-md font-semibold">Your improvement plan</h2>${g.improvement_plan.length ? `<ol class="list-decimal pl-5 mt-1 font-body-md text-on-surface-variant space-y-0.5">${g.improvement_plan.map((p) => `<li>${esc(p)}</li>`).join("")}</ol>` : '<p class="font-body-md text-on-surface-variant mt-1">You meet every requirement for this career.</p>'}</div></section>`;
      document.getElementById("career").addEventListener("change", (e) => load(e.target.value));
      root.querySelectorAll("[data-skill]").forEach((sel) => sel.addEventListener("change", async () => {
        try { await api("PUT", "/api/skills/progress", { skill: sel.dataset.skill, level: sel.value }); toast("Progress saved."); load(document.getElementById("career").value); }
        catch (e) { toast(e.message, "error"); }
      }));
    } catch (e) { if (e.status === 404) root.innerHTML = SCM.empty("psychology", "Assessment needed", "Add your skills first to see how they compare with your target career.", "assessment.html", "Start assessment"); else if (e.status !== 401) root.innerHTML = errorBox(e.message); }
  }
  await SCM.requireAuth(); load();
})();
