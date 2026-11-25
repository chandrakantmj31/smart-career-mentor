(async function () {
  const { api, esc, skillLabel, loading, errorBox, toast } = SCM;
  const root = document.getElementById("root");
  root.innerHTML = loading("Finding your best-fit careers…");
  try {
    await SCM.requireAuth();
    const d = await api("GET", "/api/careers/recommendations");
    if (d.needs_assessment) { root.innerHTML = SCM.empty("psychology_alt", "No recommendations yet", "Complete the career assessment and we'll score every career against your skills, interests and goals.", "assessment.html", "Start assessment"); return; }
    const recs = d.recommendations, top = recs[0];
    const parts = (r) => [["Skills", r.breakdown.skills, "55%"], ["Interests", r.breakdown.interests, "15%"], ["Role preference", r.breakdown.preferences, "15%"], ["Education", r.breakdown.education, "15%"]]
      .map(([n, v, w]) => `<div><div class="flex justify-between font-label-sm text-label-sm"><span class="text-on-surface-variant">${n} <span class="text-text-muted">(weight ${w})</span></span><span class="font-metric-inline text-on-surface">${v}%</span></div><div class="w-full h-1.5 rounded-full bg-surface-container overflow-hidden mt-1"><div class="h-full rounded-full bg-primary-container" style="width:${v}%"></div></div></div>`).join("");
    const chips = (r) => [...r.skills_possessed.map((s) => `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-secondary-container text-on-secondary-container font-label-sm"><span class="material-symbols-outlined text-[14px]">check_circle</span>${esc(skillLabel(s.skill))}</span>`),
      ...r.missing_skills.slice(0, 6).map((s) => `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container text-on-surface-variant font-label-sm"><span class="material-symbols-outlined text-[14px] text-status-warning">warning</span>${esc(skillLabel(s.skill))}</span>`)].join("");
    const card = (r, i) => `<article class="${i === 0 ? "border-l-4 border-primary-container" : ""} bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col gap-space-sm">
<div class="flex items-start justify-between gap-space-sm"><div class="min-w-0">${i === 0 ? '<span class="font-label-sm text-label-sm text-primary uppercase tracking-wider">Primary Recommendation</span>' : ""}<h2 class="font-headline-sm text-headline-sm text-on-surface font-semibold">${esc(r.career)}</h2><p class="font-body-sm text-on-surface-variant">${esc(r.tagline)}</p></div><div class="text-right shrink-0"><span class="font-metric-display text-headline-md text-primary-container font-semibold">${r.match}%</span><p class="font-label-sm text-text-muted">Match</p></div></div>
<p class="font-body-md text-on-surface-variant">${esc(r.explanation)}</p>
<details class="group"><summary class="cursor-pointer font-label-md text-primary-container flex items-center gap-1 select-none"><span class="material-symbols-outlined text-[18px] transition-transform group-open:rotate-90">chevron_right</span>How this match is calculated</summary><div class="mt-space-sm flex flex-col gap-space-sm">${parts(r)}</div></details>
<div><p class="font-label-sm text-text-muted uppercase tracking-wider mb-1">Skills (have · missing)</p><div class="flex flex-wrap gap-1.5">${chips(r)}</div></div>
<div><p class="font-label-sm text-text-muted uppercase tracking-wider mb-1">Recommended projects</p><ul class="list-disc pl-5 font-body-sm text-on-surface-variant space-y-0.5">${r.recommended_projects.map((p) => `<li>${esc(p)}</li>`).join("")}</ul></div>
${r.learning_path.length ? `<div><p class="font-label-sm text-text-muted uppercase tracking-wider mb-1">Suggested learning path</p><ol class="list-decimal pl-5 font-body-sm space-y-0.5">${r.learning_path.map((l) => `<li>${esc(skillLabel(l.skill))}${l.resource ? ` — <a class="text-primary-container underline" target="_blank" rel="noopener noreferrer" href="${esc(l.resource[1])}">${esc(l.resource[0])}</a>` : ""}</li>`).join("")}</ol></div>` : ""}
<div class="flex items-center justify-between pt-space-xs"><span class="font-label-sm text-text-muted">Typical fresher pay: ${esc(r.salary_note)}</span><button data-roadmap="${esc(r.career_id)}" class="px-space-md h-9 rounded-lg bg-primary text-on-primary font-label-md hover:bg-primary-container transition-colors flex items-center gap-1.5">Build roadmap <span class="material-symbols-outlined text-[16px]">arrow_forward</span></button></div></article>`;
    root.innerHTML = `<section class="px-space-md pt-space-md pb-space-sm"><span class="font-label-sm text-label-sm text-primary uppercase tracking-wider">Rule-based matching</span><h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface font-semibold tracking-tight">Personalized Career Paths</h1><p class="font-body-md text-on-surface-variant">Scored from your assessment, with every calculation shown. Top match: <b>${esc(top.career)}</b> (${top.match}%).</p></section>
<section class="px-space-md py-space-sm flex flex-col gap-space-md">${recs.map(card).join("")}</section>
<p class="px-space-md pb-space-md font-label-sm text-text-muted">${esc(d.method)}</p>
<div class="px-space-md pb-space-md"><a href="assessment.html" class="font-label-md text-primary-container underline">Update my assessment</a></div>`;
    root.querySelectorAll("[data-roadmap]").forEach((b) => b.addEventListener("click", async () => {
      b.disabled = true;
      try { await api("POST", "/api/roadmap/generate", { career_id: b.dataset.roadmap }); location.href = "roadmap.html"; }
      catch (e) { b.disabled = false; toast(e.message, "error"); }
    }));
  } catch (e) { if (e.status !== 401) root.innerHTML = errorBox(e.message); }
})();
